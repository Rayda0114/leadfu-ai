#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_etf_nav.py — ETF 淨值 / 折溢價 / 規模（官方源：TWSE 基本市況報導 all_etf.txt）

來源：https://mis.twse.com.tw/stock/data/all_etf.txt
  「ETF 發行單位變動及淨值揭露專區」的後端資料檔（投信/總代理人提供，TWSE 揭露）。
  每筆欄位：a=代號 b=全名 c=已發行受益權單位數 d=與前日差異 e=成交價
            f=投信預估淨值 g=折溢價幅度(%) h=前一營業日單位淨值 i=日期 j=時間

輸出 etf_nav_live.json：{code:{nav, premium, prevNav, units, aum, aumYi, price, asof}}
  - premium = 折溢價幅度(%)（官方提供）
  - aum（規模，元）= 受益單位數 × 淨值；aumYi = 規模（億元）

無需環境變數；由 run_all.py 每日盤後執行。
"""
import json
import datetime
import ssl
import urllib.request
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
OUT = DATA_DIR / "etf_nav_live.json"
SRC = "https://mis.twse.com.tw/stock/data/all_etf.txt"
REFERER = "https://mis.twse.com.tw/stock/various-areas/etf-price/indicator-disclosure-etf?lang=zhHant"
_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE


def get_text(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (LeadFu-AI)", "Accept": "*/*", "Referer": REFERER})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode("utf-8", "ignore")
    except Exception:
        with urllib.request.urlopen(req, timeout=30, context=_CTX) as r:
            return r.read().decode("utf-8", "ignore")


def fnum(x):
    try:
        return float(str(x).replace(",", "").replace("%", "").strip())
    except (ValueError, TypeError):
        return None


def main():
    try:
        raw = get_text(SRC)
        doc = json.loads(raw)
    except Exception as e:
        print(f"[error] 抓/解析 all_etf.txt 失敗：{e}")
        return

    # 結構：{"a1":[{"msgArray":[ {a,b,c,...}, ... ]}, ... ]}
    chunks = doc.get("a1") or []
    out = {}
    for ch in chunks:
        for r in (ch.get("msgArray") or []):
            code = (r.get("a") or "").strip()
            if not code:
                continue
            nav = fnum(r.get("f"))
            price = fnum(r.get("e"))
            prem = fnum(r.get("g"))
            prev = fnum(r.get("h"))
            units = fnum(r.get("c"))
            rec = {}
            if nav is not None:
                rec["nav"] = round(nav, 4)
            if prem is not None:
                rec["premium"] = round(prem, 2)      # 折溢價幅度 %
            if prev is not None:
                rec["prevNav"] = round(prev, 4)
            if price is not None:
                rec["price"] = round(price, 4)
            if units is not None:
                rec["units"] = units
                base = nav if nav else price
                if base:
                    aum = units * base
                    rec["aum"] = round(aum)            # 規模（元）
                    rec["aumYi"] = round(aum / 1e8, 1)  # 規模（億元）
            rec["asof"] = str(r.get("i", "")).strip()
            if rec:
                out[code] = rec

    OUT.write_text(json.dumps({"updatedAt": datetime.date.today().isoformat(),
                               "source": "TWSE 基本市況 all_etf.txt（投信揭露淨值/折溢價）",
                               "count": len(out), "data": out}, ensure_ascii=False), encoding="utf-8")
    print(f"✅ ETF 淨值/折溢價/規模：{len(out)} 檔 → etf_nav_live.json")


if __name__ == "__main__":
    main()
