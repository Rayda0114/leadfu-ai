"""
領富 AI · 美股精選 100 即時快照抓取
讀 data/us_stocks_meta.json 的 100 個 ticker，用 yfinance 抓：
  price / change / change_pct / pe_ratio / yield_pct / market_cap / 52w_high / 52w_low
輸出 data/us_stocks_live.json（前端 us-market.html join meta 後渲染）

執行：
  本機：.venv/bin/python scripts/fetch_us_snapshot.py
  CI：先 pip install yfinance，再 python scripts/fetch_us_snapshot.py
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    import yfinance as yf
except ImportError:
    print("❌ 缺 yfinance，請先：pip install yfinance", file=sys.stderr)
    sys.exit(1)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
META_PATH = DATA_DIR / "us_stocks_meta.json"
OUT_PATH = DATA_DIR / "us_stocks_live.json"


def safe(val, cast=None):
    """yfinance 偶爾回 'Infinity' / None / 字串，全部清理成 number 或 None"""
    if val is None:
        return None
    if isinstance(val, float) and (val != val or val in (float("inf"), float("-inf"))):
        return None
    if cast:
        try:
            return cast(val)
        except (TypeError, ValueError):
            return None
    return val


def fetch_one(ticker, retries=2):
    """抓單一 ticker，失敗回 None"""
    last_err = None
    for attempt in range(retries + 1):
        try:
            t = yf.Ticker(ticker)
            info = t.info
            if not info or len(info) < 3:
                raise ValueError("empty info dict")

            price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
            change = info.get("regularMarketChange")
            change_pct = info.get("regularMarketChangePercent")

            return {
                "ticker": ticker,
                "price": safe(price, float),
                "change": safe(change, float),
                "change_pct": safe(change_pct, float),
                "pe_ratio": safe(info.get("trailingPE"), float),
                "yield_pct": safe(info.get("dividendYield"), float),
                "market_cap": safe(info.get("marketCap"), int),
                "w52_high": safe(info.get("fiftyTwoWeekHigh"), float),
                "w52_low": safe(info.get("fiftyTwoWeekLow"), float),
                "sector": info.get("sector"),
                "yf_industry": info.get("industry"),
            }
        except Exception as e:
            last_err = e
            if attempt < retries:
                time.sleep(1 + attempt * 2)
            continue
    return None, str(last_err)


def main():
    print("=" * 64)
    print(f"領富 AI · 美股精選 100 即時快照 ・ {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 64)

    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    tickers = list(meta["data"].keys())
    print(f"目標：{len(tickers)} 檔 / yfinance {yf.__version__}\n")

    results = {}
    errors = []

    for i, ticker in enumerate(tickers, 1):
        print(f"  [{i:>3}/{len(tickers)}] {ticker:<6}", end=" ... ", flush=True)
        out = fetch_one(ticker)
        if isinstance(out, tuple):
            result, err = out
            print(f"❌ {err[:60]}")
            errors.append({"ticker": ticker, "error": err[:200]})
        elif out:
            results[ticker] = out
            price_str = f"${out['price']}" if out["price"] else "—"
            chg = out.get("change_pct")
            chg_str = f" ({chg:+.2f}%)" if chg is not None else ""
            print(f"OK {price_str}{chg_str}")
        else:
            print("❌ 未知失敗")
            errors.append({"ticker": ticker, "error": "unknown"})
        # 不要太快，避免 Yahoo rate limit
        time.sleep(0.15)

    payload = {
        "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source": "Yahoo Finance via yfinance",
        "yfinance_version": yf.__version__,
        "count": len(results),
        "expected": len(tickers),
        "errors": errors,
        "data": results,
    }

    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{'='*64}")
    print(f"✅ {len(results)}/{len(tickers)} 檔成功 → {OUT_PATH.relative_to(ROOT)}")
    if errors:
        print(f"⚠️ {len(errors)} 檔失敗：{[e['ticker'] for e in errors]}")

    # 列前 5 大成功檔 quick sanity check
    valid = [r for r in results.values() if r.get("price")]
    if valid:
        valid.sort(key=lambda r: r.get("market_cap") or 0, reverse=True)
        print(f"\n--- 市值前 5 ---")
        for r in valid[:5]:
            mcap_b = (r.get("market_cap") or 0) / 1e9
            print(f"  {r['ticker']:<6} ${r['price']:>10.2f}  市值 ${mcap_b:>7.1f}B  PE {r.get('pe_ratio') or '—'}  yield {r.get('yield_pct') or '—'}")


if __name__ == "__main__":
    main()
