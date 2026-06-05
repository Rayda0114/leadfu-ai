#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
calc_fin_trend.py — 毛利率 / 營益率「季變化」累積

財報（MOPS t187ap17 營益分析）是「單季」資料，要算「較上季變化」必須累積歷史。
每次執行把當季毛利率/營益率寫進 financials_qhistory.json {code:[{q,gm,op},...]}，
並在累積到 2 季以上時，算出 gm_change / op_change，輸出 financials_trend_live.json。

⚠ 目前只有 115Q1 一季，gm_change 要等下一季（115Q2，約 8 月）才算得出來；
   本腳本「現在開始累積基準」，下季財報一出就會有季變化可用。
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


def numf(x):
    return x if isinstance(x, (int, float)) and not isinstance(x, bool) else None


def main():
    fin = load("financials_live.json", "data") or {}
    hist = load("financials_qhistory.json") or {}
    if not isinstance(hist, dict):
        hist = {}
    if not fin:
        print("[warn] 無財報資料，略過")
        return

    trend = {}
    for code, v in fin.items():
        gm, op = v.get("gross_margin"), v.get("op_margin")
        q = f"{v.get('year')}Q{v.get('quarter')}"
        h = [e for e in hist.get(code, []) if isinstance(e, dict)]
        # 新的一季才追加（同季重複執行不重複記錄）
        if not h or h[-1].get("q") != q:
            h.append({"q": q, "gm": gm, "op": op})
            hist[code] = h[-6:]
        h = hist.get(code, [])
        if len(h) >= 2 and numf(h[-1].get("gm")) is not None and numf(h[-2].get("gm")) is not None:
            trend[code] = {
                "gm_change": round(h[-1]["gm"] - h[-2]["gm"], 2),
                "op_change": (round(h[-1]["op"] - h[-2]["op"], 2)
                              if numf(h[-1].get("op")) is not None and numf(h[-2].get("op")) is not None else None),
                "cur_q": h[-1]["q"], "prev_q": h[-2]["q"],
            }

    (DATA_DIR / "financials_qhistory.json").write_text(
        json.dumps(hist, ensure_ascii=False), encoding="utf-8")
    (DATA_DIR / "financials_trend_live.json").write_text(json.dumps({
        "updatedAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source": "毛利率/營益率季變化（需累積 2 季以上）",
        "count": len(trend),
        "data": trend,
    }, ensure_ascii=False), encoding="utf-8")
    print(f"✅ 財報季歷史 {len(hist)} 檔；可算季變化 {len(trend)} 檔（單季時為 0，下季起有值）")


if __name__ == "__main__":
    main()
