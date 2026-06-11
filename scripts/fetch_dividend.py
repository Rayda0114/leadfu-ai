#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_dividend.py — 股息現金流資料（退休族規劃用）

來源（皆 TWSE 上市；上櫃 TPEx 之後可再接）：
  1) 除權除息預告 TWT48U：除息日 + 現金股利/股（近期將除息者）
  2) 股利分派 t187ap45_L：現金股利分解（盈餘/法定公積/資本公積）+ 本期淨利
     → 判斷「一次性高配息／配老本」（配息主要來自公積、或淨損仍配息）

產出：data/dividend_live.json
  { code: {cash, ex_date, ex_month, type, oneoff, oneoff_reason, div_year} }

⚠ 填息紀錄需多年歷史除息日 + 股價回補，本檔未做（同回測的歷史資料限制）。
非投資建議。
"""
import json
import re
import ssl
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
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


def roc_to_month(s):
    m = re.match(r"(\d+)年(\d+)月(\d+)日", str(s or ""))
    if not m:
        return "", None
    y = int(m.group(1)) + 1911
    mo = int(m.group(2))
    return f"{y}-{mo:02d}-{int(m.group(3)):02d}", mo


def main():
    print(f"[{datetime.now():%H:%M:%S}] 抓取股息現金流資料")
    out = {}

    # 1) 除權除息預告：除息日 + 現金股利
    try:
        t = get_json("https://www.twse.com.tw/exchangeReport/TWT48U?response=json")
        rows = t.get("data", []) if isinstance(t, dict) else []
        n = 0
        for r in rows:
            if len(r) < 8:
                continue
            code = str(r[1]).strip()
            if not code:
                continue
            d = out.setdefault(code, {})
            iso, mo = roc_to_month(r[0])
            if iso:
                d["ex_date"], d["ex_month"] = iso, mo
            d["type"] = str(r[3]).strip()
            cash = fnum(r[7])
            if cash and cash > 0:
                d["cash"] = round(cash, 4)
                n += 1
        print(f"  除權息預告 TWT48U：{len(rows)} 筆，{n} 檔有現金股利")
    except Exception as e:
        print(f"  TWT48U 失敗：{e}")

    # 2) 股利分派：分解 + 淨利 → 一次性偵測（取每檔最新一筆）
    try:
        ap = get_json("https://openapi.twse.com.tw/v1/opendata/t187ap45_L")
        latest = {}
        for x in ap:
            code = str(x.get("公司代號", "")).strip()
            if not code:
                continue
            key = (str(x.get("股利年度", "")), str(x.get("期別", "")), str(x.get("出表日期", "")))
            if code not in latest or key > latest[code][0]:
                latest[code] = (key, x)
        oneoff_n = 0
        for code, (_, x) in latest.items():
            earn = fnum(x.get("股東配發-盈餘分配之現金股利(元/股)")) or 0
            legal = fnum(x.get("股東配發-法定盈餘公積發放之現金(元/股)")) or 0
            capital = fnum(x.get("股東配發-資本公積發放之現金(元/股)")) or 0
            ni = fnum(x.get("本期淨利(淨損)(元)"))
            total = earn + legal + capital
            d = out.setdefault(code, {})
            if total > 0 and not d.get("cash"):
                d["cash"] = round(total, 4)
            d["div_year"] = x.get("股利年度")
            reserve_pct = (legal + capital) / total if total > 0 else 0
            if ni is not None and ni < 0 and total > 0:
                d["oneoff"], d["oneoff_reason"] = True, "本期淨損仍配息（配老本／公積）"
                oneoff_n += 1
            elif total > 0 and reserve_pct >= 0.3:
                d["oneoff"], d["oneoff_reason"] = True, f"約 {round(reserve_pct*100)}% 配息來自公積、非當年獲利"
                oneoff_n += 1
        print(f"  股利分派 t187ap45：{len(latest)} 檔，標記一次性／配老本 {oneoff_n} 檔")
    except Exception as e:
        print(f"  t187ap45 失敗：{e}")

    payload = {
        "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source": "TWSE 除權息預告 TWT48U + 股利分派 t187ap45（上市）",
        "count": len(out),
        "data": out,
    }
    (DATA_DIR / "dividend_live.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    # 📚 配息歷史累積（dividend_history.json）：為「含息真實報酬」鋪路 — 每筆 (code, ex_date) 永久留存
    hist_path = DATA_DIR / "dividend_history.json"
    hist = {}
    if hist_path.exists():
        try: hist = json.loads(hist_path.read_text(encoding="utf-8")).get("data", {})
        except Exception: hist = {}
    added = 0
    for code, v in out.items():
        if not v.get("ex_date"): continue
        rows = hist.setdefault(code, [])
        if not any(r.get("ex_date") == v["ex_date"] for r in rows):
            rows.append({"ex_date": v["ex_date"], "cash": v.get("cash"), "type": v.get("type"), "div_year": v.get("div_year")})
            rows.sort(key=lambda r: r["ex_date"])
            added += 1
    hist_path.write_text(json.dumps({"updatedAt": payload["updatedAt"], "note": "配息歷史累積（每筆除息事件永久留存，含息報酬用）",
                                     "data": hist}, ensure_ascii=False), encoding="utf-8")
    print(f"📚 配息歷史累積 +{added} 筆")
    have_ex = sum(1 for v in out.values() if v.get("ex_month"))
    print(f"✅ 股息資料 {len(out)} 檔（有除息日 {have_ex}）→ dividend_live.json")


if __name__ == "__main__":
    main()
