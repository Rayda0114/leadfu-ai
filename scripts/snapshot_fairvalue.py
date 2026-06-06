#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
snapshot_fairvalue.py — 每日把各股「合理區間 low/high + 收盤價」append 到 fv_history.json，
為 VIP 旗艦「歷史合理區間走勢圖」累積資料。

- rolling：每檔只保留最近 CAP 天（避免檔案無限長大）。
- 冪等：同一天重跑只更新當天那筆，不會重複。
- 越早開始跑、歷史越長；圖的價格線可由 klines（日資料）疊上，區間帶用這裡的 low/high。

無需環境變數；由 run_all.py 每日盤後執行。
"""
import json
import sys
import datetime
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SRC = DATA_DIR / "fair_value_live.json"
OUT = DATA_DIR / "fv_history.json"
CAP = 30          # 每檔最多保留幾個「週點」（約半年）
FORCE = "--force" in sys.argv


def _num(x):
    return x if isinstance(x, (int, float)) and not isinstance(x, bool) else None


def main():
    try:
        fv = json.loads(SRC.read_text(encoding="utf-8")).get("data", {}) or {}
    except Exception as e:
        print(f"[error] 讀 fair_value_live.json 失敗：{e}")
        return
    today_d = datetime.date.today()
    today = today_d.isoformat()

    hist, last_upd = {}, ""
    if OUT.exists():
        try:
            j = json.loads(OUT.read_text(encoding="utf-8"))
            hist = j.get("data", {}) or {}
            last_upd = j.get("updatedAt", "")
        except Exception:
            hist = {}

    # 每週記一筆即可（合理區間帶變化慢，控制檔案大小）；上次 <6 天就跳過。--force 可強制。
    if not FORCE and last_upd:
        try:
            if (today_d - datetime.date.fromisoformat(last_upd)).days < 6:
                print(f"[skip] fv_history {last_upd} 已記錄（<6 天），本次跳過。--force 可強制。")
                return
        except Exception:
            pass

    n = 0
    for code, x in fv.items():
        low, high, price = _num(x.get("low")), _num(x.get("high")), _num(x.get("price"))
        if low is None or high is None:
            continue
        rec = {"d": today, "l": round(low, 2), "h": round(high, 2)}
        if price is not None:
            rec["p"] = round(price, 2)
        arr = [e for e in hist.get(code, []) if e.get("d") != today]   # 同日去重（重跑覆蓋）
        arr.append(rec)
        hist[code] = arr[-CAP:]
        n += 1

    OUT.write_text(json.dumps({"updatedAt": today, "cap": CAP, "count": n, "data": hist},
                              ensure_ascii=False), encoding="utf-8")
    days = max((len(v) for v in hist.values()), default=0)
    print(f"✅ fv_history：{n} 檔今日({today})合理區間已記錄；目前最長歷史 {days} 天（每檔上限 {CAP} 天）")


if __name__ == "__main__":
    main()
