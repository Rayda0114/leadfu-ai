#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_conference.py — 法人說明會（法說會）行事曆累積器

法說會無單一官方未來總表；公司以「重大訊息」公告受邀/舉辦法說會。
本腳本每日從已抓到的重大訊息抽出法說會，累積成 conference_live.json（行事曆會逐日長大）。

來源：
  1. data/announcements_live.json（fetch_announcements.py 產，含上市+上櫃重大訊息）
  2. TWSE OpenAPI t187ap04_L（上市重大訊息，補充）
抽取規則：標題/主旨含「法人說明會」或「法說會」。
解析法說會日期：標題若含「民國 yyy 年 m 月 d 日」或「yyyy/mm/dd」則擷取。
輸出 conference_live.json：{updatedAt, count, data:[{code,name,title,annDate,confDate,market}]}
累積、去重(code+annDate+title)，僅保留近 120 天。
"""
import json
import re
import datetime
import ssl
import urllib.request
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
OUT = DATA_DIR / "conference_live.json"
KEEP_DAYS = 120
_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (LeadFu-AI)", "Accept": "application/json"})
    try:
        return json.loads(urllib.request.urlopen(req, timeout=25).read())
    except Exception:
        return json.loads(urllib.request.urlopen(req, timeout=25, context=_CTX).read())


def parse_conf_date(title):
    """從標題抽法說會日期 → YYYY-MM-DD（抓不到回空）。"""
    # 民國年：1yy 年 m 月 d 日 / yy 年 m 月 d 日（115年=2026）
    m = re.search(r"(\d{2,3})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日", title)
    if m:
        y = int(m.group(1))
        y = y + 1911 if y < 200 else y
        try:
            return f"{y:04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        except Exception:
            pass
    # 西元 yyyy/mm/dd 或 yyyy-mm-dd
    m = re.search(r"(20\d{2})[/-](\d{1,2})[/-](\d{1,2})", title)
    if m:
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    return ""


def is_conf(text):
    return ("法人說明會" in text) or ("法說會" in text)


def main():
    today = datetime.date.today()
    items = []

    # 1) 既有 announcements_live
    try:
        a = json.loads((DATA_DIR / "announcements_live.json").read_text(encoding="utf-8"))
        arr = a.get("announcements") or a.get("data") or []
        for x in arr:
            title = x.get("title") or ""
            if is_conf(title):
                items.append({"code": x.get("code", ""), "name": x.get("name", ""), "title": title,
                              "annDate": x.get("date", ""), "confDate": parse_conf_date(title),
                              "market": x.get("market", "")})
    except Exception as e:
        print(f"[warn] announcements: {e}")

    # 2) TWSE t187ap04_L 補充（上市）
    try:
        for r in get_json("https://openapi.twse.com.tw/v1/opendata/t187ap04_L"):
            title = (r.get("主旨 ") or r.get("主旨") or "").strip()
            if is_conf(title):
                d = r.get("發言日期") or ""
                ann = f"{int(d[:3])+1911}-{d[3:5]}-{d[5:7]}" if len(d) == 7 and d.isdigit() else ""
                items.append({"code": r.get("公司代號", ""), "name": r.get("公司名稱", ""), "title": title,
                              "annDate": ann, "confDate": parse_conf_date(title), "market": "twse"})
    except Exception as e:
        print(f"[warn] t187ap04_L: {e}")

    # 3) 併入舊累積
    prev = []
    if OUT.exists():
        try:
            prev = json.loads(OUT.read_text(encoding="utf-8")).get("data", [])
        except Exception:
            prev = []

    seen, merged = set(), []
    for it in items + prev:
        key = (it.get("code", ""), it.get("annDate", ""), (it.get("title", "") or "")[:24])
        if key in seen:
            continue
        seen.add(key)
        merged.append(it)

    # 4) 僅留近 KEEP_DAYS（依公告日；無日期者保留）
    cutoff = (today - datetime.timedelta(days=KEEP_DAYS)).isoformat()
    merged = [m for m in merged if (not m.get("annDate")) or m["annDate"] >= cutoff]
    # 排序：法說會日期(或公告日)新→舊
    merged.sort(key=lambda m: (m.get("confDate") or m.get("annDate") or ""), reverse=True)

    OUT.write_text(json.dumps({"updatedAt": today.isoformat(), "source": "公司重大訊息（法人說明會公告）累積",
                               "count": len(merged), "data": merged}, ensure_ascii=False), encoding="utf-8")
    print(f"✅ 法說會行事曆：本次抽 {len(items)} 筆，累積 {len(merged)} 場 → conference_live.json")


if __name__ == "__main__":
    main()
