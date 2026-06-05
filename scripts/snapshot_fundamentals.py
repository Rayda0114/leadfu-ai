#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
snapshot_fundamentals.py — 每週存一份「當時的基本面快照」

用途：為「未來真正的策略回測」鋪路。真回測需要「過去某時點的基本面」(PE/殖利率/
營收/法人/合理區間位置)，但我們的各資料檔只存「今天」。本腳本每週把當時的關鍵
基本面壓縮存進 data/fund_history/<date>.json，累積數月後即可做 point-in-time 回測。

每週一份即可(基本面變動慢)，避免 repo 過度膨脹。run_all 每天跑、自動判斷該不該寫。
"""
import json
import sys
import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
HIST_DIR = DATA_DIR / "fund_history"
HIST_DIR.mkdir(exist_ok=True)
TODAY = datetime.date.today()


def load(name, key=None):
    try:
        d = json.loads((DATA_DIR / name).read_text(encoding="utf-8"))
        return d.get(key, {}) if key else d
    except Exception:
        return {}


def num(x):
    return x if isinstance(x, (int, float)) and not isinstance(x, bool) else None


def main():
    # 每週一份：近 6 天內已有快照就跳過
    existing = sorted(HIST_DIR.glob("*.json"))
    for f in existing:
        try:
            d = datetime.date.fromisoformat(f.stem)
            if (TODAY - d).days < 6:
                print(f"[skip] 近 6 天已有快照 {f.name}，本週不重複")
                return
        except ValueError:
            continue

    stocks = load("stocks_live.json", "stocks") or []
    val = load("valuation_live.json", "data") or {}
    rev = load("revenue_live.json", "revenue") or {}
    fin = load("financials_live.json", "data") or {}
    inst = load("institutional_live.json", "data") or {}
    fv = load("fair_value_live.json", "data") or {}
    if not stocks:
        print("[error] 無 stocks，略過")
        return

    snap = {}
    for s in stocks:
        c = s.get("code")
        if not c:
            continue
        v, r, f2, i2, fv2 = val.get(c, {}), rev.get(c, {}), fin.get(c, {}), inst.get(c, {}), fv.get(c, {})
        rec = {}
        if s.get("price"): rec["p"] = s["price"]
        if num(v.get("pe_ratio")): rec["pe"] = v["pe_ratio"]
        if num(v.get("yield_pct")) is not None: rec["yld"] = v["yield_pct"]
        if num(r.get("yoy")) is not None: rec["yoy"] = r["yoy"]
        if num(f2.get("gross_margin")) is not None: rec["gm"] = f2["gross_margin"]
        if num(f2.get("op_margin")) is not None: rec["om"] = f2["op_margin"]
        if num(i2.get("foreign_net_lots")) is not None: rec["fnl"] = i2["foreign_net_lots"]
        if num(fv2.get("position")) is not None: rec["fvp"] = round(fv2["position"], 3)
        if rec:
            snap[c] = rec

    out = HIST_DIR / f"{TODAY.isoformat()}.json"
    out.write_text(json.dumps({"date": TODAY.isoformat(), "count": len(snap), "data": snap}, ensure_ascii=False), encoding="utf-8")
    print(f"✅ 基本面快照 {len(snap)} 檔 → fund_history/{out.name}（共 {len(existing)+1} 份歷史）")


if __name__ == "__main__":
    main()
