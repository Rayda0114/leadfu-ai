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
import os
import re
import time
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

# 低於這個則數就視為抓取失敗，不覆寫既有新聞（見 main() 的 fail-closed 區塊）
MIN_NEWS = 5

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

# 搜尋關鍵字 → 對應 tag
QUERIES = [
    ("台股 上市",      "焦點"),
    ("IPO 申購",        "抽籤"),
    ("台股 興櫃",      "個股"),
    ("半導體 上市",    "個股"),
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


def notify_owner(text):
    """抓取失敗時通知站長 LINE（沿用站上既有 Messaging API 設定；沒設就安靜略過）"""
    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
    uid = os.environ.get("OWNER_LINE_USER_ID", "")
    if not token or not uid:
        print("[notify] 缺 LINE_CHANNEL_ACCESS_TOKEN / OWNER_LINE_USER_ID，略過通知")
        return
    try:
        body = json.dumps({"to": uid, "messages": [{"type": "text", "text": text[:900]}]}).encode("utf-8")
        req = Request("https://api.line.me/v2/bot/message/push", data=body,
                      headers={"Content-Type": "application/json",
                               "Authorization": f"Bearer {token}"})
        with urlopen(req, timeout=15) as r:
            print(f"[notify] 已通知站長 LINE（{r.status}）")
    except Exception as e:
        print(f"[notify] LINE 通知失敗：{e}")


def fetch_query(keyword, retries=3):
    """從 Google News RSS 抓某個關鍵字的新聞。

    ⚠ Google News 會「間歇性」對雲端機房 IP 回 503/429（GitHub Actions runner 常中，
    同一時間住宅 IP 打同一網址卻 200）。故對這類暫時性錯誤做退避重試，
    全部重試都失敗才拋出，交由 main() 的 fail-closed 判斷。
    """
    url = f"https://news.google.com/rss/search?q={quote(keyword)}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    last = None
    for attempt in range(retries):
        try:
            req = Request(url, headers={"User-Agent": UA, "Accept": "application/rss+xml"})
            with urlopen(req, timeout=20) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except (URLError, HTTPError) as e:
            last = e
            code = getattr(e, "code", None)
            transient = code in (429, 500, 502, 503, 504) or code is None
            if attempt < retries - 1 and transient:
                wait = 8 * (attempt + 1)          # 8s → 16s
                print(f"(第{attempt + 1}次 {code or e}，{wait}s 後重試)", end=" ", flush=True)
                time.sleep(wait)
                continue
            raise
    raise last


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

    out = DATA_DIR / "news_live.json"

    # ══ fail-closed：抓不到（或遠低於正常量）就「不要覆寫」既有新聞 ══
    # 背景：Google News RSS 間歇性擋雲端 IP（503）。舊版無條件寫檔，
    # 於是 0 則會把前一天好好的 29 則洗成空白、網站「頭條快報」整區消失
    # （2026-08-24、08-27 各發生一次）。寧可顯示昨天的新聞，也不要顯示空白。
    if len(all_news) < MIN_NEWS:
        prev = 0
        try:
            with open(out, encoding="utf-8") as f:
                prev = len(json.load(f).get("news", []))
        except Exception:
            pass
        msg = (f"只抓到 {len(all_news)} 則（門檻 {MIN_NEWS}），已保留既有 {prev} 則、"
               f"不覆寫。常見原因：Google News RSS 擋雲端 IP（503）。")
        print(f"\n⚠ {msg}")
        notify_owner(f"【領富 AI】盤前新聞抓取失敗\n{msg}\n網站仍顯示前一版新聞，不會空白。")
        # 非 0 退出：workflow 該步標記失敗（continue-on-error 不擋後續步驟），
        # 且因為沒寫檔，git diff 無變化 → 不會 commit 空新聞。
        sys.exit(1)

    payload = {
        "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source": "Google News RSS（聚合台灣財經媒體）",
        "newsCount": len(all_news),
        "news": all_news
    }

    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 已輸出: {out.relative_to(ROOT)}（{len(all_news)} 則）")


if __name__ == "__main__":
    main()
