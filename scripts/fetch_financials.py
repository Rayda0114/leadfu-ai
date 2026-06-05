#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_financials.py — 抓 MOPS「營益分析」(t187ap17) → data/financials_live.json

提供每家上市/上櫃公司「最新一季」的獲利能力指標（給財報健檢、判斷卡、同業比較用）：
  gross_margin   毛利率(%)
  op_margin      營業利益率(%)（本業獲利能力）
  pretax_margin  稅前純益率(%)
  net_margin     稅後純益率(%)
  revenue_m      營業收入（百萬元）
  year/quarter   年度（民國）/季別

來源（MOPS OpenData CSV，全市場）：
  上市 https://mopsfin.twse.com.tw/opendata/t187ap17_L.csv
  上櫃 https://mopsfin.twse.com.tw/opendata/t187ap17_O.csv
  （興櫃無此表）
純 stdlib。欄位用「索引」解析（表頭名稱很長、含括號斜線，用位置最穩）。
"""
import csv
import io
import json
import ssl
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
UA = "Mozilla/5.0 LeadFuAI/1.0"
_CTX = ssl.create_default_context()

SOURCES = {
    "listed": "https://mopsfin.twse.com.tw/opendata/t187ap17_L.csv",
    "otc":    "https://mopsfin.twse.com.tw/opendata/t187ap17_O.csv",
}
# t187ap17 欄位順序：出表日期,年度,季別,公司代號,公司名稱,營業收入(百萬),毛利率,營業利益率,稅前純益率,稅後純益率
IDX = {"year": 1, "quarter": 2, "code": 3, "revenue_m": 5,
       "gross_margin": 6, "op_margin": 7, "pretax_margin": 8, "net_margin": 9}


def fnum(x):
    try:
        return round(float(str(x).replace(",", "").strip()), 2)
    except Exception:
        return None


def fetch_csv(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=45, context=_CTX) as r:
        raw = r.read().decode("utf-8-sig")   # 去 BOM
    return list(csv.reader(io.StringIO(raw)))


def main():
    data = {}
    period = None
    for market, url in SOURCES.items():
        try:
            rows = fetch_csv(url)
        except Exception as e:
            print(f"[warn] {market} 抓取失敗: {e}")
            continue
        n = 0
        for r in rows[1:]:                    # 跳表頭
            if len(r) <= IDX["net_margin"]:
                continue
            code = r[IDX["code"]].strip()
            if not code or not code.isdigit():
                continue
            year, q = r[IDX["year"]].strip(), r[IDX["quarter"]].strip()
            data[code] = {
                "year": year,
                "quarter": q,
                "revenue_m": fnum(r[IDX["revenue_m"]]),
                "gross_margin": fnum(r[IDX["gross_margin"]]),
                "op_margin": fnum(r[IDX["op_margin"]]),
                "pretax_margin": fnum(r[IDX["pretax_margin"]]),
                "net_margin": fnum(r[IDX["net_margin"]]),
                "market": market,
            }
            n += 1
            if not period and year and q:
                period = f"{year}Q{q}"
        print(f"[info] {market}: {n} 檔")

    now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M")
    out = {
        "updatedAt": now,
        "source": "MOPS 營益分析 t187ap17（TWSE OpenData，上市+上櫃）",
        "period": period,
        "count": len(data),
        "data": data,
    }
    (DATA_DIR / "financials_live.json").write_text(
        json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"[done] financials_live.json：{len(data)} 檔，最新期別 {period}")


if __name__ == "__main__":
    main()
