#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
refresh_prices_mis.py — 用 TWSE 即時報價(MIS)把 stocks_live.json 的收盤價更新成「今日」。

為什麼需要：官方日收盤檔(STOCK_DAY_ALL)出得很慢——收盤後數小時仍回前一交易日，
pipeline 15:00 直接抓會落後一天。MIS 在 13:30 收盤就有今日資料。

做法：讀已合併的 stocks_live.json → 對上市/上櫃逐批(≤40)透過自家 worker /api/quote 代理
(Cloudflare IP 較不會被 MIS 擋)抓即時 → 覆蓋 price/change/volume；抓不到的維持原值。
非核心：失敗不擋部署（run_all 的 CRITICAL 不含本檔）。
"""
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "stocks_live.json"
PROXY = "https://leadfuai.com/api/quote?ex_ch="
BATCH = 40
UA = "LeadFu-AI/1.0 (+https://leadfuai.com)"


def fetch_batch(exchs):
    url = PROXY + urllib.parse.quote("|".join(exchs))
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def main():
    try:
        d = json.loads(DATA.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[error] 讀 stocks_live.json 失敗: {e}")
        return
    stocks = d.get("stocks") or []
    by_code = {s.get("code"): s for s in stocks}
    targets = [s for s in stocks if s.get("market") in ("listed", "otc") and s.get("code")]
    print(f"[info] 上市/上櫃 {len(targets)} 檔，分 {(-(-len(targets)//BATCH))} 批用即時報價更新")

    updated = 0
    for i in range(0, len(targets), BATCH):
        chunk = targets[i:i + BATCH]
        exchs = [("otc_" if s["market"] == "otc" else "tse_") + s["code"] + ".tw" for s in chunk]
        data = None
        for attempt in range(2):
            try:
                data = fetch_batch(exchs)
                break
            except Exception as e:
                if attempt == 0:
                    time.sleep(1.5)
                else:
                    print(f"[warn] 第 {i // BATCH + 1} 批失敗: {e}")
        if not data or not data.get("msgArray"):
            continue
        for q in data["msgArray"]:
            s = by_code.get(q.get("c"))
            if not s:
                continue
            z = _f(q.get("z"))
            if z <= 0:
                z = _f(q.get("pz"))   # 無當盤成交用上一筆成交
            y = _f(q.get("y"))        # 昨收
            if z > 0 and y > 0:
                s["price"] = z
                s["change"] = round(z - y, 2)
                v = _f(q.get("v"))    # 累積成交量(張)
                if v >= 0:
                    s["volume"] = int(v)
                updated += 1
        time.sleep(0.5)

    tw = time.gmtime(time.time() + 8 * 3600)
    d["updatedAt"] = time.strftime("%Y-%m-%d %H:%M", tw) + " · TWSE 即時(MIS)當日收盤"
    DATA.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    print(f"[done] 即時收盤價覆蓋 {updated}/{len(targets)} 檔；updatedAt={d['updatedAt']}")


if __name__ == "__main__":
    main()
