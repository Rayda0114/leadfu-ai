"""
領富 AI · 個股輿情掃描（近 30 天）— last30days 概念的台股在地化
來源：PTT 股板（討論熱度，主引擎）+ X 快訊雷達摘要（大佬提及）+ 站內新聞
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

def week_bucket(dstr):
    days = (NOW - datetime.strptime(dstr, "%Y-%m-%d")).days
    return min(days // 7, 4)  # 0=本週 1,2,3=前三週 4=更舊

def load(name):
    p = DATA / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

def main():
    stocks = (load("stocks_live.json") or {}).get("stocks", [])
    by_code = {str(s["code"]): s for s in stocks}
    # 掃描清單：成交量前 12（非 ETF）+ 示範自選 + 高波動示例
    vol_top = [str(s["code"]) for s in sorted(stocks, key=lambda x: -(x.get("volume") or 0))
               if s.get("category") != "ETF" and s.get("status") == "上市"][:12]
    extra = ["2883", "2303", "2409", "2324", "4953", "2344", "2330", "5246"]
    codes = list(dict.fromkeys(vol_top + extra))
    news = (load("news_live.json") or {}).get("news", []) or []

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
        news_hits = sum(1 for n in news if name and name in str(n.get("title", "")))
        result[code] = {
            "name": name, "ptt_week": weeks[0], "ptt_baseline": round(baseline, 1),
            "ptt_ratio": ratio, "ptt_trend": weeks[::-1],   # 舊→新
            "ptt_push_week": pushes[0], "heat_spike": spike,
            "hot_titles": [{"t": h["title"], "push": h["push"], "url": h["url"]} for h in hot_titles],
            "news_30d": news_hits,
        }
        print(f"[{i}/{len(codes)}] {code} {name}: 本週 {weeks[0]} 篇（基期 {baseline:.1f}/週, x{ratio}）"
              + (" ⚠️ 熱度異常" if spike else ""))
    out = {"updatedAt": NOW.strftime("%Y-%m-%d %H:%M"),
           "source": "PTT Stock 板（熱度統計）+ 站內新聞；僅輿情整理、非投資建議",
           "window_days": 30, "count": len(result), "data": result}
    (DATA / "sentiment_live.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n✅ sentiment_live.json：{len(result)} 檔")

if __name__ == "__main__":
    main()
