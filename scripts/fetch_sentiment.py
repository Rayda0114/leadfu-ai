"""
領富 AI · 個股輿情掃描（近 30 天）— last30days 概念的台股在地化
來源（多源熱度指數 v2）：
  1. PTT 股板（散戶討論，4 週趨勢）
  2. Google News RSS（媒體熱度，after:/before: 切週，免費無驗證；計數上限 100/週=飽和）
  3. X 快訊雷達 DB（大佬提及，summary 全文比對）
  4. YouTube Data API（財經影片聲量；金鑰在 ~/.hermes/youtube_api_key，絕不進 repo；
     quota：search=100 單位/次，每日 10,000 → 15 檔 ≈ 1,515 單位）
警示分級：任兩源同時暴增 = 🔴 紅色警示；單源暴增 = 🟠 橘色注意
輸出：data/sentiment_live.json
合規：只做熱度統計與標題樣本（附原文連結），不轉述喊單內容、非投資建議。
炒作警示規則：本週貼文數 ≥8 且為前三週平均的 ≥3 倍 → heat_spike（常見於炒作前期）
"""
import json, re, sys, time, urllib.request, urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
NOW = datetime.now()

def http_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Cookie": "over18=1"})
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return r.read().decode("utf-8", "ignore")
        except Exception:
            if attempt == 0: time.sleep(2)
    return ""

R_ENT = re.compile(
    r'<div class="r-ent">.*?<div class="nrec">(?:<span[^>]*>([^<]*)</span>)?</div>'
    r'.*?<div class="title">\s*(?:<a href="([^"]+)">([^<]+)</a>)?'
    r'.*?<div class="date">\s*([0-9 ]{1,2}/[0-9]{2})', re.S)

def nrec_val(s):
    if not s: return 0
    s = s.strip()
    if s == "爆": return 100
    if s.startswith("X"): return -10
    try: return int(s)
    except Exception: return 0

def parse_date(md):
    try:
        m, d = md.strip().split("/")
        dt = datetime(NOW.year, int(m), int(d))
        if dt > NOW + timedelta(days=2):  # 跨年（去年12月）
            dt = datetime(NOW.year - 1, int(m), int(d))
        return dt
    except Exception:
        return None

def scan_ptt(query, max_pages=6):
    """搜 PTT 股板，回近 35 天貼文 [(date, push, title, url)]"""
    out = []
    for page in range(1, max_pages + 1):
        url = f"https://www.ptt.cc/bbs/Stock/search?page={page}&q={urllib.parse.quote(query)}"
        html = http_get(url)
        if not html or 'class="r-ent"' not in html: break
        oldest_on_page = None
        for m in R_ENT.finditer(html):
            push, href, title, md = nrec_val(m.group(1)), m.group(2), m.group(3), m.group(4)
            dt = parse_date(md)
            if not dt or not title: continue
            oldest_on_page = dt if (oldest_on_page is None or dt < oldest_on_page) else oldest_on_page
            if (NOW - dt).days <= 35:
                out.append({"d": dt.strftime("%Y-%m-%d"), "push": push,
                            "title": title.strip(), "url": ("https://www.ptt.cc" + href) if href else ""})
        if oldest_on_page and (NOW - oldest_on_page).days > 35: break
        time.sleep(0.8)
    return out


def gnews_weekly(name):
    """Google News RSS：近 4 週每週新聞則數（舊→新）。上限 100/週（飽和=高熱度）。"""
    counts = []
    for lo in (21, 14, 7, 0):   # 舊 → 新
        a = (NOW - timedelta(days=lo + 7)).strftime("%Y-%m-%d")
        b = (NOW - timedelta(days=lo)).strftime("%Y-%m-%d")
        q = f'"{name}" after:{a} before:{b}' if lo else f'"{name}" after:{a}'
        url = ("https://news.google.com/rss/search?q=" + urllib.parse.quote(q)
               + "&hl=zh-TW&gl=TW&ceid=TW:zh-Hant")
        xml = http_get(url)
        counts.append(len(re.findall(r"<pubDate>", xml)))
        time.sleep(0.6)
    return counts

def x_mentions_30d(name):
    """X 快訊雷達 DB：近 30 天摘要提及次數（讀 ~/.hermes/x_supabase_key，失敗回 None）。"""
    try:
        import os
        key = os.environ.get("SUPABASE_SERVICE_KEY", "").strip() or (Path.home() / ".hermes" / "x_supabase_key").read_text().strip()
        since = (NOW - timedelta(days=30)).strftime("%Y-%m-%dT00:00:00")
        url = ("https://lhwxpnyzplylajxunlua.supabase.co/rest/v1/x_alerts?select=url"
               + "&summary_zh=ilike." + urllib.parse.quote(f"%{name}%")
               + "&created_at=gte." + since)
        req = urllib.request.Request(url, headers={"apikey": key, "Authorization": "Bearer " + key,
                                                   "Prefer": "count=exact", "Range": "0-0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            cr = r.headers.get("Content-Range", "")
            return int(cr.split("/")[-1]) if "/" in cr else None
    except Exception:
        return None


def yt_weekly(name):
    """YouTube：近 28 天提及影片的週分布 + 觀看數（單次 search 上限 50 部=飽和）。失敗回 None。"""
    import os
    key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    if not key:
        try:
            key = (Path.home() / ".hermes" / "youtube_api_key").read_text().strip()
        except Exception:
            return None
    after = (NOW - timedelta(days=28)).strftime("%Y-%m-%dT00:00:00Z")
    url = ("https://www.googleapis.com/youtube/v3/search?part=snippet&type=video&order=date&maxResults=50"
           + "&regionCode=TW&relevanceLanguage=zh-Hant&publishedAfter=" + after
           + "&q=" + urllib.parse.quote(name) + "&key=" + key)
    try:
        data = json.loads(http_get(url) or "{}")
    except Exception:
        return None
    items = data.get("items") or []
    if "error" in data:
        print("  [YT] API 錯誤:", str(data["error"].get("message", ""))[:80])
        return None
    weeks = [0, 0, 0, 0]   # w0=本週
    vids = []
    for it in items:
        s = it.get("snippet") or {}
        try:
            dt = datetime.strptime(s["publishedAt"][:10], "%Y-%m-%d")
        except Exception:
            continue
        b = min((NOW - dt).days // 7, 3)
        weeks[b] += 1
        vid = (it.get("id") or {}).get("videoId")
        if vid:
            vids.append({"id": vid, "t": s.get("title", ""), "ch": s.get("channelTitle", "")})
    views = {}
    if vids:
        ids = ",".join(v["id"] for v in vids[:50])
        try:
            st = json.loads(http_get("https://www.googleapis.com/youtube/v3/videos?part=statistics&id="
                                     + ids + "&key=" + key) or "{}")
            for it in (st.get("items") or []):
                views[it["id"]] = int((it.get("statistics") or {}).get("viewCount", 0))
        except Exception:
            pass
    for v in vids:
        v["views"] = views.get(v["id"], 0)
    top = sorted(vids, key=lambda x: -x["views"])[:2]
    return {"trend": weeks[::-1], "week": weeks[0], "saturated": len(items) >= 50,
            "views_30d": sum(views.values()),
            "top": [{"t": v["t"], "ch": v["ch"], "views": v["views"],
                     "url": "https://www.youtube.com/watch?v=" + v["id"]} for v in top]}

def week_bucket(dstr):
    days = (NOW - datetime.strptime(dstr, "%Y-%m-%d")).days
    return min(days // 7, 4)  # 0=本週 1,2,3=前三週 4=更舊

def load(name):
    p = DATA / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

def main():
    stocks = (load("stocks_live.json") or {}).get("stocks", [])
    by_code = {str(s["code"]): s for s in stocks}
    # 掃描清單（正式版）：成交量前 50（非 ETF，上市+上櫃）＋ 全體會員自選股
    vol_top = [str(s["code"]) for s in sorted(stocks, key=lambda x: -(x.get("volume") or 0))
               if s.get("category") != "ETF" and s.get("status") in ("上市", "上櫃")][:50]
    member = []
    try:
        import os
        key = os.environ.get("SUPABASE_SERVICE_KEY", "").strip() or (Path.home() / ".hermes" / "x_supabase_key").read_text().strip()
        req = urllib.request.Request(
            "https://lhwxpnyzplylajxunlua.supabase.co/rest/v1/profiles?select=watchlist&watchlist=not.is.null",
            headers={"apikey": key, "Authorization": "Bearer " + key})
        for r in json.loads(urllib.request.urlopen(req, timeout=15).read()):
            member += [str(c) for c in (r.get("watchlist") or [])]
        print(f"[清單] 會員自選 {len(set(member))} 檔")
    except Exception as e:
        print("[清單] 會員自選讀取失敗（略過）:", str(e)[:60])
    codes = list(dict.fromkeys(vol_top + member))
    # YT quota 保護：search=100 單位/次、日上限 10,000 → 最多掃 90 檔
    if len(codes) > 90:
        print(f"[清單] {len(codes)} 檔超過 YT 配額上限，截至 90 檔")
        codes = codes[:90]

    result = {}
    for i, code in enumerate(codes, 1):
        st = by_code.get(code)
        if not st: continue
        name = st.get("name", "")
        posts = scan_ptt(name)
        weeks = [0, 0, 0, 0]      # 貼文數 w0=本週
        pushes = [0, 0, 0, 0]
        for p_ in posts:
            b = week_bucket(p_["d"])
            if b < 4:
                weeks[b] += 1
                pushes[b] += max(p_["push"], 0)
        baseline = sum(weeks[1:4]) / 3.0
        ratio = round(weeks[0] / baseline, 1) if baseline > 0 else (99.0 if weeks[0] >= 5 else 0.0)
        spike = weeks[0] >= 8 and (baseline == 0 or weeks[0] >= baseline * 3)
        hot_titles = sorted([p_ for p_ in posts if week_bucket(p_["d"]) == 0],
                            key=lambda x: -x["push"])[:3]
        # 源 2：Google News 週趨勢（舊→新）
        gn = gnews_weekly(name)
        gn_base = sum(gn[:3]) / 3.0
        gn_ratio = round(gn[3] / gn_base, 1) if gn_base > 0 else (99.0 if gn[3] >= 10 else 0.0)
        gn_saturated = min(gn) >= 95          # 大型股四週都頂到 100，比率失真
        gn_spike = (not gn_saturated) and gn[3] >= 15 and (gn_base == 0 or gn[3] >= gn_base * 2.5)
        # 源 3：X 大佬提及
        xm = x_mentions_30d(name)
        # 源 4：YouTube 影片聲量
        yt = yt_weekly(name)
        yt_base = (sum(yt["trend"][:3]) / 3.0) if yt else 0
        yt_ratio = (round(yt["week"] / yt_base, 1) if yt_base > 0 else (99.0 if yt and yt["week"] >= 5 else 0.0)) if yt else 0
        yt_spike = bool(yt) and not yt["saturated"] and yt["week"] >= 5 and (yt_base == 0 or yt["week"] >= yt_base * 2.5)
        # 警示分級：任兩源同時暴增 = 🔴；單源 = 🟠
        n_spk = int(spike) + int(gn_spike) + int(yt_spike)
        dual = n_spk >= 2
        single = n_spk == 1
        result[code] = {
            "name": name, "ptt_week": weeks[0], "ptt_baseline": round(baseline, 1),
            "ptt_ratio": ratio, "ptt_trend": weeks[::-1],   # 舊→新
            "ptt_push_week": pushes[0],
            "gn_trend": gn, "gn_week": gn[3], "gn_base": round(gn_base, 1),
            "gn_ratio": gn_ratio, "gn_saturated": gn_saturated,
            "x_mentions_30d": xm,
            "yt_trend": yt["trend"] if yt else None, "yt_week": yt["week"] if yt else None,
            "yt_ratio": yt_ratio, "yt_saturated": bool(yt and yt["saturated"]),
            "yt_views_30d": yt["views_30d"] if yt else None,
            "yt_top": yt["top"] if yt else [],
            "ptt_spike": spike, "gn_spike": gn_spike, "yt_spike": yt_spike,
            "heat_spike": dual, "heat_watch": single,
            "hot_titles": [{"t": h["title"], "push": h["push"], "url": h["url"]} for h in hot_titles],
        }
        tag = " 🔴 雙源警示" if dual else (" 🟠 單源注意" if single else "")
        yts = f"YT {yt['week']} 部(x{yt_ratio}{'·飽和' if yt and yt['saturated'] else ''})" if yt else "YT -"
        print(f"[{i}/{len(codes)}] {code} {name}: PTT {weeks[0]} 篇(x{ratio}) · 新聞 {gn[3]} 則(x{gn_ratio}{'·飽和' if gn_saturated else ''}) · {yts} · X {xm if xm is not None else '-'} 次{tag}")
    ptt_ok = bool(http_get("https://www.ptt.cc/bbs/Stock/index.html"))
    out = {"updatedAt": NOW.strftime("%Y-%m-%d %H:%M"), "ptt_ok": ptt_ok,
           "source": "PTT Stock 板 + Google News + YouTube + X 快訊雷達（四源熱度統計）；僅輿情整理、非投資建議",
           "window_days": 30, "count": len(result), "data": result}
    (DATA / "sentiment_live.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n✅ sentiment_live.json：{len(result)} 檔")

if __name__ == "__main__":
    main()
