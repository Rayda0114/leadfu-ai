"""
領富 AI · K 線歷史回補腳本（一次性）
從 TWSE / TPEx 個股月成交資訊抓回近 60 個交易日的 OHLCV，
合併進 data/klines.json，讓技術指標立即可用。

策略：
  - 抓「本月」+「上月」兩個月，足以涵蓋 30+ 個交易日
  - 每 0.6 秒一次請求（保守，避免被擋）
  - 每 50 檔存檔一次（中斷不會丟資料）
  - 已有 25 天以上資料的個股直接跳過

用法：
  python scripts/backfill_klines.py            # 預設只跑上市（最多人看）
  python scripts/backfill_klines.py --tpex     # 加跑上櫃
  python scripts/backfill_klines.py --resume   # 只補空缺、跳過已完成

抓完後跑 calc_indicators.py 即可立即得到 KD/MACD/布林等技術指標。
"""

import json
import ssl
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
KLINES_FILE = DATA_DIR / "klines.json"
STOCKS_FILE = DATA_DIR / "stocks_live.json"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36"

_INSECURE_CTX = ssl.create_default_context()
_INSECURE_CTX.check_hostname = False
_INSECURE_CTX.verify_mode = ssl.CERT_NONE

SLEEP = 0.6           # 每檔請求間隔（秒）
SAVE_EVERY = 50       # 每 N 檔存檔一次
MIN_DAYS_SKIP = 25    # 已有 ≥ N 天歷史就跳過
TARGET_DAYS = 30      # 目標：每檔留最近 30 天


def roc_to_iso(roc):
    """115/05/15 -> 2026-05-15"""
    roc = (roc or "").strip()
    if "/" not in roc:
        return ""
    parts = roc.split("/")
    if len(parts) != 3:
        return ""
    try:
        year = int(parts[0]) + 1911
        return f"{year}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"
    except ValueError:
        return ""


def safe_float(x):
    if x in (None, "", "-", "--"):
        return None
    try:
        return float(str(x).replace(",", "").replace("X", "").strip())
    except ValueError:
        return None


def safe_int(x):
    if x in (None, "", "-", "--"):
        return 0
    try:
        return int(str(x).replace(",", "").strip())
    except ValueError:
        return 0


def fetch_twse(code, date_yyyymm01):
    """TWSE 個股月日成交資訊"""
    url = f"https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY?date={date_yyyymm01}&stockNo={code}&response=json"
    req = Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8"))
    except (URLError, ssl.SSLError):
        with urlopen(req, timeout=20, context=_INSECURE_CTX) as r:
            return json.loads(r.read().decode("utf-8"))


def fetch_tpex(code, date_yyyy_mm_dd):
    """TPEx 個股月日成交資訊"""
    url = f"https://www.tpex.org.tw/www/zh-tw/afterTrading/tradingStock?code={code}&date={date_yyyy_mm_dd}&response=json"
    req = Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8"))
    except (URLError, ssl.SSLError):
        with urlopen(req, timeout=20, context=_INSECURE_CTX) as r:
            return json.loads(r.read().decode("utf-8"))


def parse_twse(raw):
    """TWSE fields: 日期, 成交股數, 成交金額, 開盤價, 最高價, 最低價, 收盤價, 漲跌價差, 成交筆數, 註記"""
    bars = []
    for row in raw.get("data", []):
        if len(row) < 7:
            continue
        d = roc_to_iso(row[0])
        if not d:
            continue
        o = safe_float(row[3])
        h = safe_float(row[4])
        l = safe_float(row[5])
        c = safe_float(row[6])
        v = safe_int(row[1]) // 1000  # 股 → 張
        if c is None or c <= 0:
            continue
        bars.append({"date": d, "open": o, "high": h, "low": l, "close": c, "volume": v})
    return bars


def parse_tpex(raw):
    """TPEx tables[0] fields: 日期, 成交張數, 成交仟元, 開盤, 最高, 最低, 收盤, 漲跌, 筆數"""
    if not raw.get("tables"):
        return []
    t = raw["tables"][0]
    bars = []
    for row in t.get("data", []):
        if len(row) < 7:
            continue
        d = roc_to_iso(row[0])
        if not d:
            continue
        o = safe_float(row[3])
        h = safe_float(row[4])
        l = safe_float(row[5])
        c = safe_float(row[6])
        v = safe_int(row[1])  # 已是張
        if c is None or c <= 0:
            continue
        bars.append({"date": d, "open": o, "high": h, "low": l, "close": c, "volume": v})
    return bars


def two_months():
    """回傳本月與上月（給 TWSE 用 YYYYMM01，給 TPEx 用 YYYY/MM/DD 當月最後一天）"""
    now = datetime.now()
    this_first = now.replace(day=1)
    last_last = this_first - timedelta(days=1)
    last_first = last_last.replace(day=1)

    twse_dates = [this_first.strftime("%Y%m%d"), last_first.strftime("%Y%m%d")]
    tpex_dates = [now.strftime("%Y/%m/%d"), last_last.strftime("%Y/%m/%d")]
    return twse_dates, tpex_dates


def merge_bars(existing, new_bars):
    """合併同 code 的 K 線，按日期去重、排序，最多保留 TARGET_DAYS"""
    by_date = {b["date"]: b for b in existing}
    for b in new_bars:
        by_date[b["date"]] = b   # 新資料覆蓋舊
    merged = sorted(by_date.values(), key=lambda b: b["date"])
    return merged[-TARGET_DAYS:]


def main():
    do_tpex = "--tpex" in sys.argv
    resume = "--resume" in sys.argv

    print("=" * 60)
    print(f"K 線歷史回補 ・ {datetime.now():%Y-%m-%d %H:%M:%S}")
    print(f"模式：上市 + {('上櫃' if do_tpex else '(skip 上櫃)')} {'｜跳過已完成' if resume else ''}")
    print("=" * 60)

    if not STOCKS_FILE.exists():
        print(f"❌ {STOCKS_FILE} 不存在")
        sys.exit(1)
    with open(STOCKS_FILE, "r", encoding="utf-8") as f:
        stocks_data = json.load(f)
    all_stocks = stocks_data.get("stocks", [])
    listed = [s for s in all_stocks if s.get("market") == "listed" and s.get("code", "").isdigit()]
    otc = [s for s in all_stocks if s.get("market") == "otc" and s.get("code", "").isdigit()]

    targets = listed[:]
    if do_tpex:
        targets += otc
    print(f"目標：上市 {len(listed)} + 上櫃 {len(otc) if do_tpex else 0} = {len(targets)} 檔")

    # 載入既有 klines
    if KLINES_FILE.exists():
        with open(KLINES_FILE, "r", encoding="utf-8") as f:
            store = json.load(f)
    else:
        store = {"updatedAt": "", "klines": {}}
    klines = store.get("klines", {})
    print(f"目前 klines.json：{len(klines)} 檔個股")

    twse_dates, tpex_dates = two_months()

    processed = 0
    skipped = 0
    failed = 0
    enriched = 0
    for i, s in enumerate(targets, 1):
        code = s["code"]
        market = s.get("market")

        existing = klines.get(code, [])
        if resume and len(existing) >= MIN_DAYS_SKIP:
            skipped += 1
            continue

        try:
            new_bars = []
            if market == "listed":
                for d in twse_dates:
                    raw = fetch_twse(code, d)
                    new_bars += parse_twse(raw)
                    time.sleep(SLEEP)
            elif market == "otc":
                for d in tpex_dates:
                    raw = fetch_tpex(code, d)
                    new_bars += parse_tpex(raw)
                    time.sleep(SLEEP)
            if new_bars:
                klines[code] = merge_bars(existing, new_bars)
                enriched += 1
            else:
                # 沒抓到任何資料
                failed += 1
        except Exception as e:
            failed += 1
            print(f"  ⚠ {code} {s.get('name', '')}: {e}")
            time.sleep(SLEEP)

        processed += 1
        if processed % 20 == 0:
            print(f"  進度 {processed}/{len(targets)} (補入 {enriched}, 失敗 {failed}, 跳過 {skipped})")

        if processed % SAVE_EVERY == 0:
            store["klines"] = klines
            store["updatedAt"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            store["stockCount"] = len(klines)
            store["maxDays"] = TARGET_DAYS
            with open(KLINES_FILE, "w", encoding="utf-8") as f:
                json.dump(store, f, ensure_ascii=False, indent=2)
            print(f"  💾 已存檔（{len(klines)} 檔）")

    # 最終存檔
    store["klines"] = klines
    store["updatedAt"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    store["stockCount"] = len(klines)
    store["maxDays"] = TARGET_DAYS
    with open(KLINES_FILE, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2)

    print()
    print("=" * 60)
    print(f"✅ 完成：補入 {enriched} 檔、跳過 {skipped} 檔、失敗 {failed} 檔")
    print(f"   klines.json 共 {len(klines)} 檔")
    print(f"   平均深度 {sum(len(v) for v in klines.values()) / max(len(klines),1):.1f} 天")
    print("=" * 60)
    print("\n下一步：python scripts/calc_indicators.py")


if __name__ == "__main__":
    main()
