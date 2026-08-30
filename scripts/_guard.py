"""資料抓取／計算腳本的共用守門。

為什麼需要這個
--------------
2026-08 出過兩次「安靜壞掉」：
  1. fetch_news.py 在 Google News RSS 回 503 時照樣把空陣列寫進 news_live.json，
     網站新聞區整片空白，沒有任何告警。
  2. 每日資料管線因為 rebase 衝突整份被丟棄，台股資料凍結 71 天，
     自然搜尋流量掉了約 80%，直到有人偶然發現。

共同的失敗模式是：**上游拿不到資料時，腳本仍然無條件覆寫輸出檔**。
舊資料至少是「舊但正確」，空資料是「錯」——所以寧可保留舊的、讓這一步失敗，
也不要覆寫。這就是 fail-closed。

用法
----
    from _guard import guard_count, guard_sources, notify_owner

    guard_count("fair_value_live.json", len(out_data), floor=1500,
                what="合理區間", out_path=OUT)

    guard_sources("attention_live.json", ok=ok_sources, total=len(sources),
                  what="注意股／處置股")

兩個函式在判定失敗時都會：印出原因 → 推 LINE 給站長 → sys.exit(1)。
因為沒有寫檔，git diff 無變化，workflow 也就不會 commit 出一份空資料。
"""

import json
import os
import sys
from pathlib import Path
from urllib.request import Request, urlopen

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def notify_owner(text):
    """推 LINE 給站長（沿用站上既有 Messaging API 設定；沒設環境變數就安靜略過）。"""
    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
    uid = os.environ.get("OWNER_LINE_USER_ID", "")
    if not token or not uid:
        print("[notify] 缺 LINE_CHANNEL_ACCESS_TOKEN / OWNER_LINE_USER_ID，略過通知")
        return
    try:
        body = json.dumps({"to": uid, "messages": [{"type": "text", "text": text[:900]}]}).encode("utf-8")
        req = Request("https://api.line.me/v2/bot/message/push", data=body,
                      headers={"Content-Type": "application/json",
                               "Authorization": f"Bearer {token}"})
        with urlopen(req, timeout=15) as r:
            print(f"[notify] 已通知站長 LINE（{r.status}）")
    except Exception as e:
        print(f"[notify] LINE 通知失敗：{e}")


def _prev_count(filename, keys=("data", "revenue", "news")):
    """讀既有輸出檔的筆數，用來跟這次的結果比。讀不到就回 0。"""
    try:
        d = json.loads((DATA_DIR / filename).read_text(encoding="utf-8"))
    except Exception:
        return 0
    if isinstance(d, dict):
        if isinstance(d.get("count"), int):
            return d["count"]
        for k in keys:
            v = d.get(k)
            if hasattr(v, "__len__"):
                return len(v)
    return 0


def guard_count(filename, got, floor, what, drop_ratio=0.6):
    """筆數型守門：適用於「正常情況下筆數應該很穩定」的檔案（合理區間、月營收…）。

    兩道檢查：
      1. 絕對地板：低於 floor 一定不對。
      2. 相對衰退：比上一版少掉超過 drop_ratio，代表上游只回了一部分。
         （只有在上一版本身夠大時才檢查，避免第一次執行或剛擴充時誤判。）

    ⚠ 不要拿這個去守「本來就可能是零」的資料（例如注意股當天可能真的沒有），
      那種請用 guard_sources。
    """
    prev = _prev_count(filename)
    reason = None
    if got < floor:
        reason = f"只算出 {got} 筆，低於安全門檻 {floor}"
    elif prev >= floor and got < prev * (1 - drop_ratio):
        reason = f"只算出 {got} 筆，比上一版的 {prev} 筆少了超過 {int(drop_ratio * 100)}%"
    if not reason:
        return
    msg = f"{what}：{reason}，已保留既有 {prev} 筆、不覆寫 {filename}。"
    print(f"\n⚠ {msg}")
    notify_owner(f"【領富 AI】資料異常，已停止覆寫\n\n{msg}\n\n"
                 f"網站仍顯示前一版資料，不會空白。請查上游來源是否改版或被擋。")
    sys.exit(1)


def guard_sources(filename, ok, total, what, min_ok=1):
    """來源型守門：適用於「結果可能合法為零」的檔案（注意股、處置股…）。

    這類資料不能用筆數判斷——今天真的沒有任何注意股，空的就是正確答案。
    能區分「抓成功但零筆」與「全部抓失敗」的，只有成功的來源數。
    """
    if ok >= min_ok:
        return
    prev = _prev_count(filename)
    msg = (f"{what}：{total} 個來源全部抓取失敗（成功 {ok} 個，至少需要 {min_ok} 個），"
           f"已保留既有 {prev} 筆、不覆寫 {filename}。")
    print(f"\n⚠ {msg}")
    notify_owner(f"【領富 AI】資料來源全數失敗，已停止覆寫\n\n{msg}\n\n"
                 f"網站仍顯示前一版資料。請查來源網站是否改版或擋爬。")
    sys.exit(1)
