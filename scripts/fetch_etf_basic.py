#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_etf_basic.py — ETF 基本資料（官方源：TWSE OpenAPI t187ap47_L「基金基本資料彙總表」）

來源：https://openavpi... → https://openapi.twse.com.tw/v1/opendata/t187ap47_L
含 257 檔上市 ETF：基金類型、標的/追蹤指數名稱、是否含國外成分、上市日期、發行單位數。

輸出 etf_basic_live.json：{code:{type, index, foreign(bool), listDate, mgr}}
  - type   = 基金類型（如「國內成分證券指數股票型基金」「主動式…」「債券…」）
  - index  = 標的指數/追蹤指數名稱（「不適用」者留空，多為主動式 ETF）
  - foreign= 是否包含國外成分股
無需環境變數；由 run_all.py 每日盤後執行。
"""
import json
import datetime
import ssl
import urllib.request
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
OUT = DATA_DIR / "etf_basic_live.json"
SRC = "https://openapi.twse.com.tw/v1/opendata/t187ap47_L"
_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE


def roc_date(s):
    s = str(s).strip()
    try:
        if len(s) == 7:
            return f"{int(s[:3]) + 1911}-{s[3:5]}-{s[5:7]}"
    except Exception:
        pass
    return ""


def main():
    req = urllib.request.Request(SRC, headers={"User-Agent": "Mozilla/5.0 (LeadFu-AI)", "Accept": "application/json"})
    try:
        rows = json.loads(urllib.request.urlopen(req, timeout=30).read())
    except Exception:
        try:
            rows = json.loads(urllib.request.urlopen(req, timeout=30, context=_CTX).read())
        except Exception as e:
            print(f"[error] 抓 t187ap47_L 失敗：{e}")
            return
    if not isinstance(rows, list):
        print("[error] t187ap47_L 格式非預期")
        return

    out = {}
    for r in rows:
        code = (r.get("基金代號") or "").strip()
        if not code:
            continue
        idx = (r.get("標的指數/追蹤指數名稱") or "").strip()
        if idx in ("不適用", "N/A", "-"):
            idx = ""
        out[code] = {
            "type": (r.get("基金類型") or "").strip(),
            "index": idx,
            "foreign": (r.get("是否包含國外成分股") or "").strip() == "是",
            "listDate": roc_date(r.get("上市日期")),
            "mgr": (r.get("基金經理人") or "").strip(),
        }

    OUT.write_text(json.dumps({"updatedAt": datetime.date.today().isoformat(),
                               "source": "TWSE OpenAPI t187ap47_L 基金基本資料彙總表",
                               "count": len(out), "data": out}, ensure_ascii=False), encoding="utf-8")
    print(f"✅ ETF 基本資料：{len(out)} 檔 → etf_basic_live.json（含追蹤指數/類型）")


if __name__ == "__main__":
    main()
