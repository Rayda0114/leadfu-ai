#!/usr/bin/env python3
"""
批次給 leadfuai.com 所有頁面補上完整 SEO meta tags + Open Graph + Twitter Card。
規則：
- 若頁面已有 <meta name="description"> → 不動，只補缺的
- 若沒有 → 用 PAGE_META 字典插入完整一組
- 插入位置：<title> 標籤之後

執行：python scripts/batch_seo_meta.py
"""
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
PAGES_DIR = ROOT / "pages"
SITE_URL = "https://leadfuai.com"
DEFAULT_OG_IMAGE = "https://leadfuai.com/icons/icon-512.png"

# 每頁的 SEO 內容定義
PAGE_META = {
    "stocks.html": {
        "title": "股價總覽 - 上市/上櫃/興櫃 全市場即時報價 - 領富 AI",
        "desc": "領富 AI 整合台股全市場 2,300+ 檔即時報價，跨上市、上櫃、興櫃一次看完。支援產業/市場/排序篩選。資料源 TWSE+TPEx+MOPS。",
    },
    "screener.html": {
        "title": "進階選股 - 多條件智慧篩選 - 領富 AI",
        "desc": "依本益比、殖利率、ROE、月營收年增、合理區間位置等 14 項條件智慧篩選台股。投資人選股最有效率的工具。",
    },
    "industries.html": {
        "title": "產業分類 - 35 大產業跨三市場 - 領富 AI",
        "desc": "領富 AI 整理 35 大產業類別個股分布，半導體、生技、AI 伺服器、PCB 等熱門題材一頁看完。跨上市/上櫃/興櫃。",
    },
    "institutional.html": {
        "title": "三大法人買賣超 - 外資投信自營商每日動向 - 領富 AI",
        "desc": "領富 AI 整理三大法人（外資、投信、自營商）每日買賣超排行。看大戶在買什麼、賣什麼。",
    },
    "margin.html": {
        "title": "融資融券 - 散戶融資餘額追蹤 - 領富 AI",
        "desc": "領富 AI 整理融資融券餘額變化，看散戶資金動向。融資餘額異常變化常是反指標。",
    },
    "sbl.html": {
        "title": "借券餘額 - 外資借券放空追蹤 - 領富 AI",
        "desc": "領富 AI 整理借券餘額變化。外資狂借券 = 準備大空襲？看誰被借券狂掃。",
    },
    "dividends.html": {
        "title": "高殖利率排行 - 穩定配息存股名單 - 領富 AI",
        "desc": "領富 AI 整理台股高殖利率股票排行，5%、6%、7% 以上殖利率名單。退休族存股最愛工具。",
    },
    "risk-radar.html": {
        "title": "防錯雷達 - 注意股/處置股/月營收暴跌警示 - 領富 AI",
        "desc": "領富 AI 整理注意股、處置股、月營收年減 50% 以上、借券暴增等異常警示，幫您避雷。看清楚再決定。",
    },
    "portfolio-health.html": {
        "title": "持股健診 - 自選股 AI 風險檢測 - 領富 AI",
        "desc": "領富 AI 自動檢查您的自選股集中度、注意股暴露、法人賣超風險。每日自動分析，給您完整健診報告。",
    },
    "weekly.html": {
        "title": "AI 產業週報 - 每週一自動生成 - 領富 AI",
        "desc": "領富 AI 每週一自動生成的產業週報。整合 35 大產業漲跌、熱門題材、法人動向、本週重點。",
    },
    "learn.html": {
        "title": "學習中心 - 退休族投資入門 - 領富 AI",
        "desc": "領富 AI 學習中心：本益比、殖利率、KD/MACD、布林通道、注意股、上市上櫃差異等退休族必懂概念。",
    },
    "news.html": {
        "title": "財經新聞 - 台股即時新聞 - 領富 AI",
        "desc": "領富 AI 整合 Google News 財經新聞 + TWSE/TPEx 公告，每日台股焦點一頁看完。",
    },
    "discussion.html": None,  # 已在 discussion 改造時補齊
    "ipo.html": {
        "title": "IPO 新股抽籤 - 台股新股行事曆 - 領富 AI",
        "desc": "領富 AI 整理台股 IPO 新股抽籤行事曆、承銷價、中籤率預估。資料源 TWSE OpenAPI。",
    },
    "announcements.html": {
        "title": "公司公告 - 重大訊息整理 - 領富 AI",
        "desc": "領富 AI 整合台股上市櫃公司每日重大訊息、注意股／處置股公告。MOPS 公開資訊觀測站資料。",
    },
    "vip.html": None,  # vip.html 已有 description
    "login.html": {
        "title": "會員登入 - 領富 AI",
        "desc": "領富 AI 會員登入。註冊免費，登入後可同步自選股、解鎖完整合理區間分析、設定 LINE 警示推播。",
    },
    "register.html": {
        "title": "免費註冊 - 領富 AI",
        "desc": "免費註冊領富 AI 會員。0 元就送：跨上市櫃 2,300+ 檔即時報價、AI 對話、合理區間、月營收、產業週報、自選股雲端同步。",
    },
    "about.html": {
        "title": "關於我們 - 領富 AI 公司簡介 - 領富 AI",
        "desc": "領富 AI（LeadFu）— 台灣全市場股票資訊整合平台。我們的使命：讓台股資訊變得透明、簡單、可信賴。不推薦個股、不代操、不收任何投資款項。",
    },
    "terms.html": None,
    "privacy.html": None,
    "fraud-alert.html": None,  # 已有完整 head 含 JSON-LD
    "contact.html": {
        "title": "聯絡我們 - 領富 AI 客服 LINE @041exgtv - 領富 AI",
        "desc": "領富 AI 唯一官方客服 LINE：@041exgtv。⚠ 我們沒有 APP，不主動加 LINE 群組，不保證獲利。冒用請報 165 反詐騙專線。",
    },
    "stock-detail.html": None,  # 已在 P1-A 處理
    "ai.html": {
        "title": "AI 對話 - 自然語言查詢台股 - 領富 AI",
        "desc": "領富 AI 對話：用講的、用問的、跨上市/上櫃/興櫃 2,300+ 檔即時資料 + 合理區間 + AI 分析。",
    },
    "tax.html": {
        "title": "證交稅專題 - 股票交易稅務指南 - 領富 AI",
        "desc": "領富 AI 整理台股證交稅、二代健保補充保費、股息扣繳、海外所得等稅務相關資訊。",
    },
    "tutorial.html": None,
    "watchlist.html": {
        "title": "我的自選股 - 雲端同步 - 領富 AI",
        "desc": "領富 AI 自選股：跨裝置雲端同步，免費註冊即可使用。AI 自動健診、警示推播、月營收追蹤。",
    },
    "member.html": None,
    "search.html": {
        "title": "搜尋結果 - 領富 AI",
        "desc": "領富 AI 全站搜尋：個股、產業、新聞、公告一次找。",
    },
    "news-detail.html": None,
    "thread-detail.html": None,
    "software.html": None,
    "app.html": None,
}


def build_seo_block(slug: str, meta: dict) -> str:
    """產生完整 SEO meta block"""
    url = f"{SITE_URL}/pages/{slug}"
    title = meta["title"]
    desc = meta["desc"].replace('"', "&quot;")
    return f"""<meta name="description" content="{desc}">
<link rel="canonical" href="{url}">

<!-- Open Graph -->
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:image" content="{DEFAULT_OG_IMAGE}">
<meta property="og:type" content="website">
<meta property="og:url" content="{url}">
<meta property="og:locale" content="zh_TW">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{desc}">
<meta name="twitter:image" content="{DEFAULT_OG_IMAGE}">
<meta name="theme-color" content="#1B4332">
<link rel="icon" type="image/svg+xml" href="../icons/icon.svg">"""


def process_file(filepath: Path, meta: dict) -> bool:
    """處理單一檔案，回傳是否有更新"""
    if not filepath.exists():
        print(f"  ⊘ 跳過：{filepath.name} 不存在")
        return False

    text = filepath.read_text(encoding="utf-8")

    # 已經有 og:title 就跳過（已 SEO 過）
    if 'property="og:title"' in text or "property='og:title'" in text:
        print(f"  ⊘ 跳過：{filepath.name} 已有 OG 標籤")
        return False

    # 更新 <title>（如果寫在 PAGE_META 裡且現有 title 是預設樣）
    new_title = meta.get("title", "")
    if new_title:
        old_title_match = re.search(r"<title>([^<]+)</title>", text)
        if old_title_match:
            text = text.replace(old_title_match.group(0), f"<title>{new_title}</title>", 1)

    seo_block = build_seo_block(filepath.name, meta)

    # 插入到 </title> 之後
    title_end = text.find("</title>")
    if title_end == -1:
        print(f"  ✗ 失敗：{filepath.name} 找不到 </title>")
        return False

    insert_at = title_end + len("</title>")
    # 找下一個換行做為插入點
    next_nl = text.find("\n", insert_at)
    if next_nl == -1:
        next_nl = insert_at

    # 若已有 description 就刪掉舊的
    text_after_title = text[next_nl:]
    text_after_title = re.sub(
        r'\n?<meta\s+name="description"[^>]*>',
        "",
        text_after_title,
        count=1
    )

    new_text = text[:next_nl] + "\n" + seo_block + text_after_title

    filepath.write_text(new_text, encoding="utf-8")
    print(f"  ✓ 更新：{filepath.name}")
    return True


def main():
    updated = 0
    skipped = 0
    for slug, meta in PAGE_META.items():
        if meta is None:
            continue
        filepath = PAGES_DIR / slug
        if process_file(filepath, meta):
            updated += 1
        else:
            skipped += 1
    print(f"\n完成：{updated} 個檔案更新，{skipped} 個跳過")


if __name__ == "__main__":
    main()
