#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_attention.py — 領富 AI · 注意股 / 處置股 名單

來源（全市場）：
  TWSE 上市：
    announcement/notice      當日公布注意股
    announcement/notetrans   近期多次達注意標準（累計）
    announcement/punish      處置有價證券
  TPEx 上櫃：
    tpex_esb_warning_information   注意股（欄位「注意交易資訊」）
    tpex_esb_disposal_information  處置股

產出：data/attention_live.json
  { updatedAt, source, count, data: { code: {type:"注意"/"處置", reason, date, market} } }

用途：進階選股「注意股排除」、個股頁風險、持股健診警示。
注意：處置(較嚴重) 覆蓋 注意；含權證/ETF 代碼亦保留，與股票清單交集後自然只留個股。
"""
import json
import ssl
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from urllib.error import URLError, HTTPError

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
BASE_TPEX = "https://www.tpex.org.tw/openapi/v1"
BASE_TWSE = "https://openapi.twse.com.tw/v1"
UA = "LeadFu-AI/1.0 (+https://leadfuai.com)"
_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE


def fetch_url(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except (URLError, ssl.SSLError):
        with urllib.request.urlopen(req, timeout=30, context=_CTX) as r:
            return json.loads(r.read().decode("utf-8"))


def roc_to_iso(s):
    s = str(s or "").strip()
    if len(s) != 7:
        return ""
    try:
        return f"{int(s[:3]) + 1911}-{s[3:5]}-{s[5:7]}"
    except ValueError:
        return ""


def add(data, code, typ, reason, date, market):
    code = (code or "").strip()
    if not code:
        return
    # 處置 比 注意 嚴重；已標記處置者不被注意覆蓋
    if code in data and data[code]["type"] == "處置" and typ == "注意":
        return
    data[code] = {"type": typ, "reason": (reason or "").strip()[:60], "date": date, "market": market}


def main():
    print(f"[{datetime.now():%H:%M:%S}] 抓取注意股 / 處置股名單")
    data = {}
    sources = [
        (f"{BASE_TWSE}/announcement/notice",     "TWSE 注意(當日)",   "注意", "listed", "Code", "TradingInfoForAttention", "Date"),
        (f"{BASE_TWSE}/announcement/notetrans",  "TWSE 注意(累計)",   "注意", "listed", "Code", "RecentlyMetAttentionSecuritiesCriteria", None),
        (f"{BASE_TWSE}/announcement/punish",     "TWSE 處置",         "處置", "listed", "Code", "ReasonsOfDisposition", "Date"),
        (f"{BASE_TPEX}/tpex_esb_warning_information",  "TPEx 注意",   "注意", "otc",    "證券代號", "注意交易資訊", "公告日期"),
        (f"{BASE_TPEX}/tpex_esb_disposal_information", "TPEx 處置",   "處置", "otc",    "證券代號", "處置原因",   "公布日期"),
    ]
    for url, label, typ, market, code_k, reason_k, date_k in sources:
        try:
            raw = fetch_url(url)
            before = len(data)
            for r in (raw or []):
                add(data, r.get(code_k), typ, r.get(reason_k), roc_to_iso(r.get(date_k)) if date_k else "", market)
            print(f"  {label}: 原始 {len(raw)} → 累計 +{len(data) - before}")
        except (URLError, HTTPError, ValueError, ssl.SSLError) as e:
            print(f"  {label}: ❌ {e}")

    att = sum(1 for v in data.values() if v["type"] == "注意")
    dis = len(data) - att
    payload = {
        "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source": "TWSE + TPEx 注意股 / 處置股",
        "count": len(data),
        "data": data,
    }
    out = DATA_DIR / "attention_live.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ 注意 {att}、處置 {dis}、合計 {len(data)} → {out.name}")
    for c, v in list(data.items())[:8]:
        print(f"  {c} [{v['type']}] {v['reason'][:34]}")


if __name__ == "__main__":
    main()
