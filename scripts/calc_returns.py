#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
calc_returns.py — 回測簡單版用：各股近 1/3/6 個月報酬 + 最大回撤（上市）

直接抓 TWSE STOCK_DAY 近 6 個月日收盤，算每檔 r1m/r3m/r6m 與 6 個月最大回撤；
另抓 FMTQIK 加權指數同期報酬（給「vs 大盤」）。輸出 data/returns_live.json（小檔）。

回測「簡單版」= 用這份報酬，把「目前符合某策略的股票」過去表現彙整（勝率/平均/回撤/vs大盤）。
⚠ 非歷史選股回測（有倖存者偏誤）；真回測需歷史基本面（見 snapshot_fundamentals.py 累積中）。

可重複執行：已在 returns_live.json 的代碼會跳過（中斷可續跑）。節流 0.6s。
"""
import json
import ssl
import sys
import time
import datetime
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
OUT = DATA_DIR / "returns_live.json"
SLEEP = 0.6
_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (LeadFu-AI)", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8", "ignore"))
    except (urllib.error.URLError, ssl.SSLError):
        with urllib.request.urlopen(req, timeout=30, context=_CTX) as r:
            return json.loads(r.read().decode("utf-8", "ignore"))


def fnum(x):
    try:
        return float(str(x).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


def roc_date(s):
    # "115/06/05" → date
    try:
        p = str(s).strip().split("/")
        return datetime.date(int(p[0]) + 1911, int(p[1]), int(p[2]))
    except Exception:
        return None


def months_back(n=6):
    out, cur = [], datetime.date.today().replace(day=1)
    for _ in range(n):
        out.append(cur.strftime("%Y%m%d"))
        cur = (cur - datetime.timedelta(days=1)).replace(day=1)
    return out


def metrics(series):
    """series: [(date, close)] 升冪。回傳 r1m/r3m/r6m(%) + mdd(%)。"""
    series = sorted([(d, c) for d, c in series if d and c and c > 0])
    if len(series) < 5:
        return None
    last_d, last_c = series[-1]
    def ret(days):
        cut = last_d - datetime.timedelta(days=days)
        prior = [c for d, c in series if d <= cut]
        base = prior[-1] if prior else series[0][1]
        return round((last_c - base) / base * 100, 2) if base else None
    peak = series[0][1]; mdd = 0.0
    for _, c in series:
        peak = max(peak, c)
        mdd = max(mdd, (peak - c) / peak * 100)
    return {"r1m": ret(30), "r3m": ret(90), "r6m": ret(180), "mdd": round(mdd, 2)}


def stock_series(code, months):
    s = []
    for ym in months:
        raw = get_json(f"https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY?date={ym}&stockNo={code}&response=json")
        for row in (raw.get("data") or []):
            d, c = roc_date(row[0]), fnum(row[6])  # [0]日期 [6]收盤價
            if d and c: s.append((d, c))
        time.sleep(SLEEP)
    return s


def index_series(months):
    s = []
    for ym in months:
        raw = get_json(f"https://www.twse.com.tw/rwd/zh/afterTrading/FMTQIK?date={ym}&response=json")
        for row in (raw.get("data") or []):
            d, c = roc_date(row[0]), fnum(row[4])  # [4]發行量加權股價指數
            if d and c: s.append((d, c))
        time.sleep(SLEEP)
    return s


def main():
    months = months_back(6)
    stocks = json.loads((DATA_DIR / "stocks_live.json").read_text(encoding="utf-8")).get("stocks", [])
    listed = [s for s in stocks if s.get("market") == "listed" and str(s.get("code", "")).isdigit()]

    prev = {}
    if OUT.exists():
        try: prev = json.loads(OUT.read_text(encoding="utf-8")).get("data", {})
        except Exception: prev = {}

    # 指數（每次重算）
    try:
        idx = metrics(index_series(months)) or {}
    except Exception as e:
        print(f"[warn] 指數抓取失敗: {e}"); idx = {}
    print(f"[info] 加權指數報酬 {idx}；上市 {len(listed)} 檔，已完成 {len(prev)} 檔")

    data = dict(prev)
    done = 0
    for i, s in enumerate(listed, 1):
        code = s["code"]
        if code in data:
            continue
        try:
            m = metrics(stock_series(code, months))
            if m: data[code] = m
        except Exception:
            pass
        done += 1
        if done % 40 == 0:
            OUT.write_text(json.dumps({"updatedAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                                       "index": idx, "count": len(data), "data": data}, ensure_ascii=False), encoding="utf-8")
            print(f"  進度 {i}/{len(listed)}（已存 {len(data)} 檔）")
    OUT.write_text(json.dumps({"updatedAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                               "index": idx, "count": len(data), "data": data}, ensure_ascii=False), encoding="utf-8")
    print(f"✅ 報酬資料 {len(data)} 檔 → returns_live.json（指數 r6m={idx.get('r6m')}）")


if __name__ == "__main__":
    main()
