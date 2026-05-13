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
import subprocess
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent
SCRIPTS = [
    "fetch_emerging.py",
    "fetch_companies.py",
    "fetch_revenue.py",
    "fetch_news.py",
    "fetch_announcements.py",
    "fetch_klines.py",
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
        try:
            code = subprocess.call(
                [sys.executable, str(script)],
                env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"}
            )
            if code != 0:
                failed.append(s)
                print(f"❌ {s} 失敗 (exit {code})")
        except Exception as e:
            failed.append(s)
            print(f"❌ {s} 例外: {e}")

    print(f"\n{'=' * 60}")
    if failed:
        print(f"⚠ 完成但有 {len(failed)} 個腳本失敗：{failed}")
        sys.exit(1)
    print(f"✅ 全部完成 ・ {datetime.now():%H:%M:%S}")


if __name__ == "__main__":
    main()
