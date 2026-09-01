"""
領富 AI · 全資料抓取主控
依序執行所有 fetcher，互不影響：

    1. fetch_emerging.py      → data/stocks_live.json
    2. fetch_news.py          → data/news_live.json
    3. fetch_announcements.py → data/announcements_live.json
    4. fetch_klines.py        → data/klines.json  (需先有 stocks_live)

用法：
    python scripts/run_all.py
"""

import sys
import time
import subprocess
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# TPEx API 偶發抽風，自動重試 3 次
MAX_ATTEMPTS = 3
RETRY_BACKOFF = 8   # 秒

ROOT = Path(__file__).resolve().parent
SCRIPTS = [
    # 1. 公司基本資料先抓（含產業代碼→中文名對照），給 merge_stocks 用
    "fetch_companies.py",
    # 2. 三市場各自抓報價 → 中間檔
    "fetch_listed_twse.py",   # 上市 ~1,000 檔
    "fetch_listed_tpex.py",   # 上櫃 ~800 檔
    "fetch_emerging.py",      # 興櫃 ~350 檔
    # 3. 合併並用 companies 真實產業覆蓋 category
    "merge_stocks.py",
    # 3.5 用即時報價(MIS)把收盤價更新成「今日」——官方日檔(STOCK_DAY_ALL)出太慢，否則整站落後一天
    "refresh_prices_mis.py",
    # 4. 其他補充資料
    "fetch_revenue.py",
    "fetch_news.py",
    "fetch_announcements.py",
    "fetch_conference.py",      # 法人說明會行事曆累積（從重大訊息抽法說會）
    "fetch_attention.py",       # 注意股/處置股名單（TWSE+TPEx）→ 進階選股「注意股排除」
    "fetch_institutional.py",   # 三大法人買賣超（上市，TWSE T86）
    "calc_inst_streak.py",      # 外資連買/連賣天數（每日累積，需逐日執行）
    "fetch_valuation.py",       # 本益比/殖利率/股價淨值比（上市，TWSE BWIBBU_d）
    "fetch_dividend.py",        # 股息現金流：除息日/現金股利/一次性偵測（上市）
    "fetch_financials.py",      # 營益分析：毛利率/營業利益率/純益率（上市+上櫃，MOPS t187ap17）
    "calc_fin_trend.py",        # 毛利率/營益率季變化（累積，下季起有值）
    "fetch_margin.py",          # 融資融券（上市，TWSE MI_MARGN）
    "fetch_margin_tpex.py",     # 融資融券（上櫃，TPEx balance）
    "fetch_sbl.py",             # 借券（外資空單，TWSE TWT93U）
    "fetch_tdcc.py",            # 千張大戶持股比率（TDCC 集保股權分散表，每週更新、腳本自帶同日期跳過）
    "fetch_insider.py",         # 大股東名單（MOPS t187ap02）
    "fetch_klines_daily.py",    # K 線：每日全市場 +1 根（取代舊 fetch_klines.py 只更新興櫃）
    "calc_indicators.py",       # 技術指標 KD/MACD/布林/RSI/MA（從 klines 計算）
    "calc_fair_value.py",       # 💎 領富 AI 合理區間（LeadFu Fair Value Range™）— 旗艦功能
    "calc_risk_score.py",       # ⚠ 個股風險分數 0-100（防錯雷達；需上面各資料齊全）+ 警示歷史累積
    "snapshot_fundamentals.py", # 每週存基本面快照（為未來真回測鋪路）
    "calc_returns.py",          # 各股近 1/3/6 月報酬 + 回撤（回測簡單版）；腳本自身週頻 gate，僅 7 天才重算
    "snapshot_fairvalue.py",    # 每日存合理區間 low/high → fv_history.json（VIP 歷史合理區間走勢圖累積用）
    "fetch_etf_dividend.py",    # ETF 配息累積
    "fetch_etf_nav.py",         # ETF 淨值/折溢價/規模（TWSE 基本市況 all_etf.txt 官方源）
    "fetch_etf_basic.py",       # ETF 基本資料：追蹤指數/類型/上市日（TWSE OpenAPI t187ap47_L）
    "fetch_etf_holdings.py",    # ETF 成分股（各投信 PCF API，v1：元大）
    "calc_etf_health.py",       # 高股息 ETF 健檢（殖利率 vs 總報酬、溢價、規模 → 徽章）
    "fetch_taifex.py",        # 大盤風險溫度計（台指期日夜盤+P/C+結算日 → 明日波動風險）
    "fetch_ipo.py",             # 新股 IPO 行事曆（TWSE 上市申請）
    "generate_industry_pages.py",  # 🏭 產業頁 pages/industries/*.html + 更新 industries.html 連結（需 stocks + risk）
    "generate_sitemap.py",
    # 每日常青內容：拿上面抓好的資料生成個股深度說明（放最後，要等素材齊）
    "gen_stock_insight.py",
]