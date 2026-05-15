"""
領富 AI · 財經新聞抓取
資料來源：Google News RSS（聚合 UDN、自由、工商、經濟日報等主要媒體）
策略：以多組關鍵字搜尋，標題+摘要+原始連結，使用者點下去回原媒體網站

用法：
    python scripts/fetch_news.py
產出：
    data/news_live.json
"""

import json
import sys
import re
import html
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import quote
from urllib.error import URLError, HTTPError
import xml.etree.ElementTree as ET

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

# 搜尋關鍵字 → 對應 tag
QUERIES = [
    ("興櫃 股票",      "焦點"),
    ("IPO 申購",        "抽籤"),
    ("未上市 股票",    "個股"),
    ("半導體 興櫃",    "個股"),
    ("生技 興櫃",      "個股"),
    ("台股 公告",      "公告"),
]

UA = "Mozilla/5.0 (compatible; LeadFu-AI/1.0; +https://leadfuai.com)"


def strip_html(s):
    """簡易去 HTML 標籤 + 解 entity"""
    if not s:
        return ""
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def parse_pub_date(s):
    """Google News 用 RFC822 格式: Mon, 13 May 2026 06:30:00 GMT"""
    if not s:
        return "", ""
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(s)
        return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M")
    except Exception:
        return "", ""


def fetch_query(keyword):
    """從 Google News RSS 抓某個關鍵字的新聞"""
    url = f"https://news.google.com/rss/search?q={quote(keyword)}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    req = Request(url, headers={"User-Agent": UA, "Accept": "application/rss+xml"})
    with urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", errors="replace")


def parse_rss(xml_text, tag, max_items=8):
    """解析 RSS 為新聞列表"""
    items = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        print(f"  ⚠ XML 解析失敗: {e}")
        return items

    for it in root.iter("item"):
        if len(items) >= max_items:
            break
        title  = strip_html(it.findtext("title", ""))
        link   = (it.findtext("link", "") or "").strip()
        pub    = it.findtext("pubDate", "")
        desc   = strip_html(it.findtext("description", ""))

        # Google News description 通常包含媒體名，例如 "經濟日報" 或 "工商時報"
        source = ""
        m = re.search(r"((?:聯合|經濟|工商|自由|中央社|中時|蘋果|鉅亨|商業周刊)\w*)", desc)
        if m:
            source = m.group(1)

        date, t = parse_pub_date(pub)
        # 摘要：截短到 80 字
        summary = (desc[:80] + "...") if len(desc) > 80 else desc

        if title and link:
            items.append({
                "title": title,
                "link": link,
                "date": date,
                "time": t,
                "tag": tag,
                "source": source,
                "summary": summary
            })
    return items


def dedupe(news_list):
    """依標題前 18 字去重（避免不同關鍵字抓到同則新聞）"""
    seen = set()
    out = []
    for n in news_list:
        key = n["title"][:18]
        if key in seen:
            continue
        seen.add(key)
        out.append(n)
    return out


def main():
    print(f"[{datetime.now():%H:%M:%S}] 抓 Google News RSS")
    all_news = []

    for keyword, tag in QUERIES:
        print(f"  查詢 [{tag}] {keyword}", end=" ")
        try:
            xml = fetch_query(keyword)
            items = parse_rss(xml, tag, max_items=5)
            print(f"→ {len(items)} 則")
            all_news.extend(items)
        except (URLError, HTTPError) as e:
            print(f"❌ {e}")

    all_news = dedupe(all_news)
    # 按日期＋時間倒序
    all_news.sort(key=lambda n: (n["date"], n["time"]), reverse=True)
    # 最多保留 30 則
    all_news = all_news[:30]

    # 補上 id（網站內部用）
    for i, n in enumerate(all_news, 1):
        n["id"] = i

    # 顯示前 5 則
    print(f"\n去重後 {len(all_news)} 則新聞：")
    for n in all_news[:5]:
        src = f" [{n['source']}]" if n['source'] else ""
        print(f"  [{n['tag']}] {n['date']} {n['time']}{src} {n['title'][:50]}")

    payload = {
        "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source": "Google News RSS（聚合台灣財經媒體）",
        "newsCount": len(all_news),
        "news": all_news
    }

    out = DATA_DIR / "news_live.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 已輸出: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
