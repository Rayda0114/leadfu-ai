#!/usr/bin/env python3
"""確認每日管線真的執行了，而不是「安靜地什麼都沒做」。

為什麼需要這一關
----------------
2026-09-01 的 commit b23a52c 本意只是把 gen_stock_insight.py 加進 run_all.py
的清單，卻連同檔尾 60 行的 main() 一起刪掉。結果是：

  - run_all.py 執行後印出 0 行、exit 0
  - workflow 每一步都「成功」，綠燈
  - data/ 沒有任何檔案被更新 → git diff 幾乎空的 → 沒人察覺
  - 全站台股資料凍結在 2026-08-31，連續 6 個交易日

同樣的事 2026-06 已經發生過一次（凍結 71 天、自然搜尋掉約 80%）。
兩次的共通點都不是「腳本失敗」——失敗是會叫的——而是**根本沒跑**。
沒跑不會叫，所以要有人專門檢查「有沒有跑」。

檢查兩件事
----------
1. 執行紀錄裡的「▶ 執行 xxx.py」行數，要等於 run_all.SCRIPTS 的長度。
   這一項對連假免疫（放假照樣要跑完清單），是主要防線。
2. stocks_live.json 的日期不能落後太多。門檻放寬到 8 天，是為了避開
   春節那種長假；它擋不住短期凍結，只是第二層網。

任一項不過就推 LINE 給站長並 exit 1，讓 workflow 亮紅燈。
"""

import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _guard import notify_owner   # noqa: E402
import run_all                    # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
STALE_DAYS = 8


def main(log_path):
    problems = []

    log = Path(log_path).read_text(encoding="utf-8", errors="replace") if Path(log_path).exists() else ""
    ran = len(re.findall(r"▶ 執行 \S+\.py", log))
    want = len(run_all.SCRIPTS)
    if ran < want:
        problems.append(f"清單有 {want} 支腳本，實際只跑了 {ran} 支"
                        + ("（完全沒跑，run_all.py 可能壞了）" if ran == 0 else ""))

    try:
        import json
        d = json.loads((ROOT / "data" / "stocks_live.json").read_text(encoding="utf-8"))
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(d.get("updatedAt", "")))
        if not m:
            problems.append(f"stocks_live.json 的 updatedAt 讀不出日期：{d.get('updatedAt')!r}")
        else:
            age = (date.today() - date(*map(int, m.groups()))).days
            if age > STALE_DAYS:
                problems.append(f"股價資料停在 {m.group(0)}，已經 {age} 天沒更新")
    except Exception as e:
        problems.append(f"stocks_live.json 讀取失敗：{e}")

    if not problems:
        print(f"✅ 管線自檢通過：{ran}/{want} 支腳本執行完畢")
        return 0

    msg = "；".join(problems)
    print(f"\n❌ 管線自檢失敗：{msg}")
    notify_owner("【領富 AI】每日資料管線沒有正常執行\n\n" + msg
                 + "\n\n請看 GitHub Actions「每日資料更新」的紀錄。"
                   "網站顯示的是舊資料，不會空白，但已經停止更新。")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/run_all.log"))
