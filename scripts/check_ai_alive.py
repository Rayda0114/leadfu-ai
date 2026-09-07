#!/usr/bin/env python3
"""金絲雀：每天確認 /api/ask 真的答得出話。

為什麼需要這個
--------------
/api/ask 是全站唯一的 AI 出口——網站聊天（達叔）、LINE 客服、新聞 AI 標註、
每日個股常青內容，全部走它。它掛掉的時候，這四件事同時停擺。

而它掛掉的原因一年內重複了兩次，兩次都一樣：**Nvidia NIM 把模型下架**。
  2026-07-27  qwen 全家下架 → 410 → 8/14 才被發現
  2026-09-07  openai/gpt-oss-120b 下架 → 410（Gemini 備援同時撞 429）
下架不會有預告，程式碼也不會壞——壞的是遠端的模型清單。

備援救不了這種事：Gemini 免費額度是 1500 req/day，主力一掛就會在幾小時內
被打爆，接著兩邊一起 429/410。所以真正需要的是「早點知道」。

判定
----
連問 3 次，**每一次**都要答得出來才算通過。

為什麼是「每次都要過」而不是「有一次過就好」：主力掛掉時 Gemini 備援還在，
但免費額度是按分鐘限流的，所以會變成「偶爾答得出來、多數回 502」。實測
2026-09-07 就是這樣——單發一次探測會矇混過關，連發三次才看得出來已經壞了。
使用者體感也是這個：十次有七次拿不到回應，那就是壞了。

失敗就推 LINE 給站長並 exit 1，讓 workflow 亮紅燈。

⚠ 這支不需要任何金鑰——它打的是自己的公開端點，跟真實使用者走同一條路。
   刻意如此：測 worker 實際部署的設定，而不是測本機的環境變數。
"""

import json
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _guard import notify_owner   # noqa: E402

URL = "https://leadfuai.com/api/ask"
QUESTION = "用一句話說明本益比是什麼意思。"
MIN_LEN = 12
ATTEMPTS = 3


def probe():
    body = json.dumps({"question": QUESTION, "mode": "article",
                       "max_tokens": 300, "stream": False}).encode("utf-8")
    req = urllib.request.Request(URL, data=body, method="POST", headers={
        "Content-Type": "application/json", "User-Agent": "LeadFuAICanary/1.0"})
    with urllib.request.urlopen(req, timeout=120,
                                context=ssl.create_default_context()) as r:
        d = json.loads(r.read().decode("utf-8"))
    return (d.get("answer") or d.get("text") or "").strip()


def main():
    fails = []
    for i in range(1, ATTEMPTS + 1):
        last = ""
        try:
            ans = probe()
            if len(ans) >= MIN_LEN:
                print(f"  第 {i}/{ATTEMPTS} 次 OK（{len(ans)} 字）：{ans[:50]}")
                if i < ATTEMPTS:
                    time.sleep(3)
                continue
            last = f"回應太短（{len(ans)} 字）：{ans[:80]!r}"
        except urllib.error.HTTPError as e:
            # 502 的 body 裡有上游真正的錯誤碼（410=模型被下架、429=額度用盡），
            # 那是判斷「該換模型還是該等額度」的關鍵資訊，一定要帶進通知裡。
            try:
                detail = e.read().decode("utf-8", "replace")[:300]
            except Exception:
                detail = ""
            last = f"HTTP {e.code}：{detail}"
        except Exception as e:
            last = f"{type(e).__name__}：{str(e)[:150]}"
        fails.append(last)
        print(f"  第 {i}/{ATTEMPTS} 次失敗：{last[:160]}")
        if i < ATTEMPTS:
            time.sleep(6 * i)

    if not fails:
        print(f"\n✅ AI 金絲雀通過：{ATTEMPTS}/{ATTEMPTS} 次都答得出來")
        return 0

    summary = f"{ATTEMPTS} 次探測失敗了 {len(fails)} 次。最後一次：{fails[-1]}"
    print(f"\n❌ AI 金絲雀失敗：{summary}")
    notify_owner("【領富 AI】網站 AI 回應不穩或全掛\n\n"
                 f"{summary[:400]}\n\n"
                 "影響：網站 AI 對話、LINE 客服、新聞 AI 標註、每日個股內容全部停擺。\n"
                 "若錯誤碼是 410，代表 Nvidia NIM 又把模型下架了，"
                 "要改 worker.js 的 DEFAULT_MODEL；429 則是額度用盡。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
