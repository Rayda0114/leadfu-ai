#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
calc_inst_streak.py — 外資連買 / 連賣天數（每日累積）

讀 institutional_live.json 的外資買賣超(foreign_net_lots)，跟自身「上次輸出」比對，
累積「連買 N 日 / 連賣 N 日」。只涵蓋上市（TWSE T86 三大法人日報）。

輸出：data/inst_streak_live.json
  { code: { dir:"buy"/"sell", days:N, foreign:今日張數 } }（days≥1）

注意：連買/連賣天數需「每個交易日」執行累積；首次執行所有 days=1，之後每天 +1。
方向反轉（買→賣或賣→買）即重置為 1。非投資建議。
"""
import json
import sys
import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load(name, key=None):
    try:
        d = json.loads((DATA_DIR / name).read_text(encoding="utf-8"))
        return d.get(key, {}) if key else d
    except Exception:
        return {}


def main():
    inst = load("institutional_live.json", "data") or {}
    prev = load("inst_streak_live.json", "data") or {}
    if not inst:
        print("[warn] 無法人資料，略過")
        return

    out = {}
    for code, v in inst.items():
        fn = v.get("foreign_net_lots")
        if not isinstance(fn, (int, float)) or isinstance(fn, bool):
            continue
        d = "buy" if fn > 0 else ("sell" if fn < 0 else None)
        if d is None:
            continue
        p = prev.get(code) or {}
        days = (p.get("days", 0) + 1) if p.get("dir") == d else 1
        out[code] = {"dir": d, "days": days, "foreign": int(fn)}

    payload = {
        "updatedAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source": "外資連買/連賣天數（每日累積，上市 TWSE T86）",
        "count": len(out),
        "data": out,
    }
    (DATA_DIR / "inst_streak_live.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    buy3 = sum(1 for v in out.values() if v["dir"] == "buy" and v["days"] >= 3)
    sell3 = sum(1 for v in out.values() if v["dir"] == "sell" and v["days"] >= 3)
    print(f"✅ 法人連買/連賣 {len(out)} 檔；連買≥3日 {buy3}、連賣≥3日 {sell3}（首次執行皆 days=1，需逐日累積）")


if __name__ == "__main__":
    main()
