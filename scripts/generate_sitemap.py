"""
領富 AI · sitemap.xml 自動產生器
- 列出所有靜態頁面
- 列出所有興櫃個股的 stock-detail 頁（深度連結，Google 會逐一索引）
- 列出所有真實新聞詳情頁
- lastmod 用今天日期

由 GitHub Actions 每日跑（在 run_all 之後）→ commit 進 repo → Netlify 自動部署
"""

import json
import sys
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
SITEMAP = ROOT / "sitemap.xml"

# 改網域時只需動這裡
BASE_URL = "https://leadfuai.com"

STATIC_PAGES = [
    ("/",                              "daily",   1.0),
    ("/pages/ai.html",                 "daily",   0.95),
    ("/pages/stocks.html",             "daily",   0.9),
    ("/pages/screener.html",           "daily",   0.9),
    ("/pages/news.html",               "daily",   0.9),
    ("/pages/industries.html",         "daily",   0.8),
    ("/pages/ipo.html",                "weekly",  0.8),
    ("/pages/announcements.html",      "daily",   0.7),
    ("/pages/discussion.html",         "weekly",  0.7),
    ("/pages/tutorial.html",           "monthly", 0.7),
    ("/pages/tax.html",                "monthly", 0.6),
    ("/pages/watchlist.html",          "weekly",  0.6),
    ("/pages/vip.html",                "monthly", 0.6),
    ("/pages/app.html",                "monthly", 0.5),
    ("/pages/software.html",           "monthly", 0.5),
    ("/pages/about.html",              "monthly", 0.5),
    ("/pages/contact.html",            "monthly", 0.5),
    ("/pages/register.html",           "yearly",  0.4),
    ("/pages/login.html",              "yearly",  0.3),
    ("/pages/terms.html",              "yearly",  0.3),
    ("/pages/privacy.html",            "yearly",  0.3),
    ("/pages/fraud-alert.html",        "monthly", 0.5),
    ("/pages/risk-radar.html",         "daily",   0.85),
    ("/pages/institutional.html",      "daily",   0.85),
    ("/pages/portfolio-health.html",   "weekly",  0.7),
    ("/pages/dividends.html",          "daily",   0.85),
    ("/pages/margin.html",             "daily",   0.85),
    ("/pages/sbl.html",                "daily",   0.8),
    ("/pages/weekly.html",             "weekly",  0.9),
    ("/pages/learn.html",              "weekly",  0.9),
    ("/pages/learn/yoy.html",                       "monthly", 0.8),
    ("/pages/learn/pe-ratio.html",                  "monthly", 0.85),
    ("/pages/learn/dividend-yield.html",            "monthly", 0.85),
    ("/pages/learn/institutional-investors.html",   "monthly", 0.8),
    ("/pages/learn/securities-lending.html",        "monthly", 0.75),
]


def load_json(path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def url_entry(path, changefreq, priority, lastmod=None):
    parts = [
        "  <url>",
        f"    <loc>{BASE_URL}{path}</loc>",
    ]
    if lastmod:
        parts.append(f"    <lastmod>{lastmod}</lastmod>")
    parts += [
        f"    <changefreq>{changefreq}</changefreq>",
        f"    <priority>{priority}</priority>",
        "  </url>",
    ]
    return "\n".join(parts)


def main():
    today = datetime.now().strftime("%Y-%m-%d")
    urls = []

    # 1. 靜態頁面
    for path, freq, prio in STATIC_PAGES:
        urls.append(url_entry(path, freq, prio, today))
    print(f"靜態頁面: {len(STATIC_PAGES)}")

    # 2. 個股詳情頁
    stocks_data = load_json(DATA_DIR / "stocks_live.json")
    stock_count = 0
    if stocks_data and stocks_data.get("stocks"):
        for s in stocks_data["stocks"]:
            code = s.get("code")
            if code:
                urls.append(url_entry(
                    f"/pages/stock-detail.html?code={code}",
                    "daily", 0.6, today
                ))
                stock_count += 1
    print(f"個股詳情頁: {stock_count}")

    # 3. 新聞詳情頁
    news_data = load_json(DATA_DIR / "news_live.json")
    news_count = 0
    if news_data and news_data.get("news"):
        for n in news_data["news"]:
            nid = n.get("id")
            date = n.get("date") or today
            if nid:
                urls.append(url_entry(
                    f"/pages/news-detail.html?id={nid}",
                    "monthly", 0.5, date
                ))
                news_count += 1
    print(f"新聞詳情頁: {news_count}")

    # 組裝
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    xml += "\n".join(urls)
    xml += "\n</urlset>\n"

    SITEMAP.write_text(xml, encoding="utf-8")

    total = len(STATIC_PAGES) + stock_count + news_count
    print(f"\n✅ sitemap.xml 已更新（共 {total} 個 URL）")


if __name__ == "__main__":
    main()
