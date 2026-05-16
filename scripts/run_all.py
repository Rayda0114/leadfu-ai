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
    # 4. 其他補充資料
    "fetch_revenue.py",
    "fetch_news.py",
    "fetch_announcements.py",
    "fetch_institutional.py",   # 三大法人買賣超（上市，TWSE T86）
    "fetch_klines.py",
    "generate_sitemap.py",
]


def main():
    print("=" * 60)
    print(f"領富 AI 全資料抓取 ・ {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 60)

    failed = []
    for s in SCRIPTS:
        script = ROOT / s
        print(f"\n{'━' * 50}")
        print(f"▶ 執行 {s}")
        print(f"{'━' * 50}")

        success = False
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                code = subprocess.call(
                    [sys.executable, str(script)],
                    env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"}
                )
                if code == 0:
                    success = True
                    break
                if attempt < MAX_ATTEMPTS:
                    wait = RETRY_BACKOFF * attempt
                    print(f"⚠ {s} 第 {attempt} 次失敗 (exit {code})，等 {wait} 秒後重試...")
                    time.sleep(wait)
                else:
                    print(f"❌ {s} 三次嘗試都失敗，放棄")
            except Exception as e:
                if attempt < MAX_ATTEMPTS:
                    print(f"⚠ {s} 第 {attempt} 次例外: {e}，等 {RETRY_BACKOFF * attempt} 秒後重試...")
                    time.sleep(RETRY_BACKOFF * attempt)
                else:
                    print(f"❌ {s} 三次嘗試都例外: {e}")

        if not success:
            failed.append(s)

    print(f"\n{'=' * 60}")
    if failed:
        print(f"⚠ 完成但有 {len(failed)} 個腳本失敗：{failed}")
        sys.exit(1)
    print(f"✅ 全部完成 ・ {datetime.now():%H:%M:%S}")


if __name__ == "__main__":
    main()
