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
    ("/pages/check.html",              "daily",   0.9),
    ("/pages/samples.html",            "weekly",  0.7),
    ("/pages/value-stocks.html",       "daily",   0.85),
    ("/pages/etf.html",                "daily",   0.9),
    ("/pages/etf-compare.html",        "daily",   0.85),
    ("/pages/conference.html",         "daily",   0.7),
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
    ("/pages/market-risk.html",        "daily",   0.85),
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
    ("/pages/learn/kd-indicator.html",              "monthly", 0.85),
    ("/pages/learn/macd-indicator.html",            "monthly", 0.85),
    ("/pages/learn/bollinger-bands.html",           "monthly", 0.8),
    ("/pages/learn/margin-trading.html",            "monthly", 0.8),
    ("/pages/learn/warning-stocks.html",            "monthly", 0.85),
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
        f"    <loc>{BASE_URL}{path.replace('.html', '')}</loc>",  # 無 .html 為正規網址（對齊 canonical）
    ]
    if lastmod:
        parts.append(f"    <lastmod>{lastmod}</lastmod>")
    parts += [
        f"    <changefreq>{changefreq}</changefreq>",
        f"    <priority>{priority}</priority>",
        "  </url>",
    ]
    return "\n".join(parts)


def write_urlset(filename, url_list):
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    xml += "\n".join(url_list)
    xml += "\n</urlset>\n"
    (ROOT / filename).write_text(xml, encoding="utf-8")


def main():
    today = datetime.now().strftime("%Y-%m-%d")
    page_urls, stock_urls, content_urls = [], [], []

    # 1. 首頁 + 工具/靜態頁（學習文章歸「內容」子 sitemap）
    for path, freq, prio in STATIC_PAGES:
        entry = url_entry(path, freq, prio, today)
        if path.startswith("/pages/learn"):
            content_urls.append(entry)
        else:
            page_urls.append(entry)

    # 2. 個股詳情頁
    stocks_data = load_json(DATA_DIR / "stocks_live.json")
    if stocks_data and stocks_data.get("stocks"):
        for s in stocks_data["stocks"]:
            code = s.get("code")
            if code:
                stock_urls.append(url_entry(
                    f"/pages/stock-detail.html?code={code}", "daily", 0.6, today
                ))

    # 3. 新聞詳情頁 → 內容
    news_data = load_json(DATA_DIR / "news_live.json")
    if news_data and news_data.get("news"):
        for n in news_data["news"]:
            nid = n.get("id")
            date = n.get("date") or today
            if nid:
                content_urls.append(url_entry(
                    f"/pages/news-detail.html?id={nid}", "monthly", 0.5, date
                ))

    # 寫出 3 個子 sitemap
    write_urlset("sitemap-pages.xml", page_urls)       # 首頁 + 工具頁
    write_urlset("sitemap-stocks.xml", stock_urls)     # 個股頁（2,500+）
    write_urlset("sitemap-content.xml", content_urls)  # 教學文章 + 新聞

    # 4. sitemap.xml 改為「索引檔」，指向 3 個子 sitemap（robots / GSC 已指向它）
    refs = []
    for fn in ("sitemap-pages.xml", "sitemap-stocks.xml", "sitemap-content.xml"):
        refs.append(
            f"  <sitemap>\n    <loc>{BASE_URL}/{fn}</loc>\n"
            f"    <lastmod>{today}</lastmod>\n  </sitemap>"
        )
    idx = '<?xml version="1.0" encoding="UTF-8"?>\n'
    idx += '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    idx += "\n".join(refs)
    idx += "\n</sitemapindex>\n"
    SITEMAP.write_text(idx, encoding="utf-8")

    print(
        f"✅ sitemap 索引 + 3 子檔已更新："
        f"首頁/工具 {len(page_urls)}、個股 {len(stock_urls)}、內容 {len(content_urls)}"
    )


if __name__ == "__main__":
    main()
