#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_etf_dividend.py — ETF 配息累積器（為 ETF 專區的殖利率鋪路）

TWSE 沒有「ETF 年度殖利率」的單一 API；配息金額散在除權息預告 TWT48U_ALL（含 ETF 的
CashDividend）。本腳本每日抓 TWT48U_ALL → 收集 ETF（代號 00 開頭）每次除息的配息金額，
累積到 etf_div_history.json（逐檔、去重）。累積一段時間後即有「近一年各次配息」，
可算出真實年度殖利率（近 12 個月配息合計 ÷ 股價）。

冪等：同一檔同一除息日只記一次。輸出 etf_div_live.json 供前端用（最新配息 + 近一年合計）。
無需環境變數；由 run_all.py 每日盤後執行。
"""
import json
import datetime
import ssl
import urllib.request
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
HIST = DATA_DIR / "etf_div_history.json"
OUT = DATA_DIR / "etf_div_live.json"
SRC = "https://openapi.twse.com.tw/v1/exchangeReport/TWT48U_ALL"
_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (LeadFu-AI)", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return json.loads(r.read().decode("utf-8", "ignore"))
    except Exception:
        with urllib.request.urlopen(req, timeout=40, context=_CTX) as r:
            return json.loads(r.read().decode("utf-8", "ignore"))


def fnum(x):
    try:
        return float(str(x).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


def roc_date(s):
    # "1150617" → 2026-06-17
    s = str(s).strip()
    try:
        if len(s) == 7:
            return f"{int(s[:3]) + 1911:04d}-{s[3:5]}-{s[5:7]}"
    except Exception:
        pass
    return s


def main():
    try:
        rows = get_json(SRC)
    except Exception as e:
        print(f"[error] 抓 TWT48U_ALL 失敗：{e}")
        return
    if not isinstance(rows, list):
        print("[error] TWT48U_ALL 格式非預期")
        return

    # 載入歷史
    hist = {}
    if HIST.exists():
        try:
            hist = json.loads(HIST.read_text(encoding="utf-8")).get("data", {}) or {}
        except Exception:
            hist = {}

    # 收集本次 ETF 除息（代號 00 開頭、息、有現金股利）
    new = 0
    for r in rows:
        code = (r.get("Code") or "").strip()
        if not code.startswith("00"):
            continue
        cash = fnum(r.get("CashDividend"))
        if not cash or cash <= 0:
            continue
        d = roc_date(r.get("Date"))
        name = (r.get("Name") or "").strip()
        rec = hist.setdefault(code, {"name": name, "dists": []})
        rec["name"] = name or rec.get("name", "")
        if not any(x.get("d") == d for x in rec["dists"]):
            rec["dists"].append({"d": d, "cash": round(cash, 4)})
            rec["dists"].sort(key=lambda x: x.get("d", ""))
            rec["dists"] = rec["dists"][-24:]   # 留最近 24 次
            new += 1

    HIST.write_text(json.dumps({"updatedAt": datetime.date.today().isoformat(), "data": hist},
                               ensure_ascii=False), encoding="utf-8")

    # 衍生：每檔近一年配息合計 + 最新一次（供前端算殖利率 = 近一年合計 / 股價）
    today = datetime.date.today()
    one_year_ago = (today - datetime.timedelta(days=365)).isoformat()
    live = {}
    for code, rec in hist.items():
        dists = rec.get("dists", [])
        if not dists:
            continue
        ttm = round(sum(x["cash"] for x in dists if x.get("d", "") >= one_year_ago), 4)
        last = dists[-1]
        live[code] = {
            "name": rec.get("name", ""),
            "lastCash": last["cash"],
            "lastExDate": last["d"],
            "ttmCash": ttm,            # 近一年配息合計（資料累積中，初期可能偏低）
            "distCount": len(dists),
        }
    OUT.write_text(json.dumps({"updatedAt": today.isoformat(), "count": len(live), "data": live},
                              ensure_ascii=False), encoding="utf-8")
    print(f"✅ ETF 配息：本次新增 {new} 筆除息事件；累積 {len(hist)} 檔、輸出 {len(live)} 檔（etf_div_live.json）")


if __name__ == "__main__":
    main()
