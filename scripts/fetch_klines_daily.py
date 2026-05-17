"""
領富 AI · 每日 K 線增量更新（全市場）
每天跑一次，把當日 OHLCV 追加進 klines.json 的每檔個股。

策略：
  - 上市：TWSE STOCK_DAY_ALL 一次 1,359 檔
  - 上櫃：TPEx dailyQuotes 一次 ~880 主板 + ETFs
  - 興櫃：用既有 _raw_tpex_*.json（最新一份）
  - 每檔保留最近 30 天，超出修剪
  - 已記錄同日資料 → 覆蓋（盤中跑兩次也安全）

取代舊版 fetch_klines.py（原本只更新 348 檔興櫃）。
跑完後接 calc_indicators.py 即得最新技術指標。
"""

import json
import ssl
import sys
from datetime import datetime
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
TARGET_DAYS = 30

_INSECURE_CTX = ssl.create_default_context()
_INSECURE_CTX.check_hostname = False
_INSECURE_CTX.verify_mode = ssl.CERT_NONE


def fetch_json(url):
    req = Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except (URLError, ssl.SSLError):
        with urlopen(req, timeout=30, context=_INSECURE_CTX) as r:
            return json.loads(r.read().decode("utf-8"))


def yyyymmdd_to_iso(s):
    """20260515 → 2026-05-15"""
    s = (s or "").strip()
    if len(s) == 8 and s.isdigit():
        return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
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


def fetch_twse_listed():
    """TWSE STOCK_DAY_ALL — 一次拿全上市單日 OHLCV
    Fields: 證券代號, 證券名稱, 成交股數, 成交金額, 開盤價, 最高價, 最低價, 收盤價, 漲跌價差, 成交筆數
    """
    url = "https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY_ALL?response=json"
    raw = fetch_json(url)
    if raw.get("stat") != "OK":
        return "", []
    date_iso = yyyymmdd_to_iso(raw.get("date", ""))
    bars = []
    for row in raw.get("data", []):
        if len(row) < 8:
            continue
        code = (row[0] or "").strip()
        if not code:
            continue
        o = safe_float(row[4])
        h = safe_float(row[5])
        l = safe_float(row[6])
        c = safe_float(row[7])
        v = safe_int(row[2]) // 1000   # 股 → 張
        if c is None or c <= 0:
            continue
        bars.append({
            "code": code, "date": date_iso,
            "open": o, "high": h, "low": l, "close": c, "volume": v
        })
    return date_iso, bars


def fetch_tpex_otc():
    """TPEx dailyQuotes — 一次拿全上櫃單日 OHLCV
    Fields: 代號, 名稱, 收盤, 漲跌, 開盤, 最高, 最低, 均價, 成交股數, 成交金額, 成交筆數, ...
    """
    url = "https://www.tpex.org.tw/www/zh-tw/afterTrading/dailyQuotes?response=json"
    raw = fetch_json(url)
    date_iso = yyyymmdd_to_iso(raw.get("date", ""))
    bars = []
    if not raw.get("tables"):
        return date_iso, bars
    table = raw["tables"][0]   # 上櫃股票行情
    for row in table.get("data", []):
        if len(row) < 9:
            continue
        code = (row[0] or "").strip()
        if not code:
            continue
        o = safe_float(row[4])
        h = safe_float(row[5])
        l = safe_float(row[6])
        c = safe_float(row[2])   # 注意：TPEx 順序是 收盤/漲跌/開盤/最高/最低
        v = safe_int(row[8]) // 1000  # 股 → 張
        if c is None or c <= 0:
            continue
        bars.append({
            "code": code, "date": date_iso,
            "open": o, "high": h, "low": l, "close": c, "volume": v
        })
    return date_iso, bars


def fetch_emerging():
    """興櫃：讀最新一份 _raw_tpex_*.json"""
    raws = sorted(DATA_DIR.glob("_raw_tpex_*.json"), reverse=True)
    if not raws:
        return "", []
    latest = raws[0]
    with open(latest, "r", encoding="utf-8") as f:
        raw = json.load(f)
    if not raw or not isinstance(raw, list):
        return "", []
    # 從第一筆解析資料日期（ROC → ISO）
    date_iso = ""
    roc = (raw[0].get("Date") or "").strip()
    if len(roc) == 7:
        try:
            year = int(roc[:3]) + 1911
            date_iso = f"{year}-{roc[3:5]}-{roc[5:7]}"
        except ValueError:
            pass
    bars = []
    for r in raw:
        code = (r.get("SecuritiesCompanyCode") or "").strip()
        if not code:
            continue
        try:
            c = float(r.get("LatestPrice") or 0)
            h = float(r.get("Highest") or c)
            l = float(r.get("Lowest") or c)
            prev = float(r.get("PreviousAveragePrice") or c)
            v = int(float(r.get("TransactionVolume") or 0)) // 1000
            o = prev if prev > 0 else c
        except (ValueError, TypeError):
            continue
        if c <= 0:
            continue
        bars.append({
            "code": code, "date": date_iso,
            "open": round(o, 2), "high": round(h, 2),
            "low":  round(l, 2), "close": round(c, 2), "volume": v
        })
    return date_iso, bars


def merge_into_klines(klines, all_bars):
    """把 [{code, date, ohlcv...}] 合併進 klines dict，保留最近 TARGET_DAYS"""
    added = 0
    updated = 0
    new_codes = 0
    for b in all_bars:
        code = b["code"]
        entry = {
            "date": b["date"], "open": b["open"], "high": b["high"],
            "low":  b["low"],  "close": b["close"], "volume": b["volume"]
        }
        if code not in klines:
            klines[code] = []
            new_codes += 1
        existing = klines[code]
        if existing and existing[-1].get("date") == entry["date"]:
            existing[-1] = entry
            updated += 1
        else:
            existing.append(entry)
            added += 1
        # 修剪
        if len(existing) > TARGET_DAYS:
            klines[code] = existing[-TARGET_DAYS:]
    return added, updated, new_codes


def load_universe():
    """從 stocks_live.json 讀取我們追蹤的個股集合（過濾掉權證、槓桿 ETF）"""
    if not STOCKS_FILE.exists():
        return None
    with open(STOCKS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {s["code"] for s in data.get("stocks", []) if s.get("code")}


def main():
    print("=" * 60)
    print(f"每日 K 線增量更新 ・ {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 60)

    # 個股 universe（過濾權證等雜訊）
    universe = load_universe()
    if universe:
        print(f"追蹤 universe：{len(universe)} 檔（其餘權證/槓桿 ETF 自動忽略）")

    # 載入既有
    if KLINES_FILE.exists():
        with open(KLINES_FILE, "r", encoding="utf-8") as f:
            store = json.load(f)
        klines = store.get("klines", {})
    else:
        store = {}
        klines = {}
    print(f"目前 klines.json：{len(klines)} 檔")

    def keep(bars):
        if not universe:
            return bars
        return [b for b in bars if b["code"] in universe]

    all_bars = []
    market_stats = []

    # 1. 上市
    try:
        d_listed, bars = fetch_twse_listed()
        bars = keep(bars)
        print(f"\n▶ 上市 TWSE：{len(bars)} 檔 ({d_listed})")
        all_bars.extend(bars)
        market_stats.append(("上市", d_listed, len(bars)))
    except Exception as e:
        print(f"\n❌ 上市抓取失敗：{e}")

    # 2. 上櫃
    try:
        d_otc, bars = fetch_tpex_otc()
        bars = keep(bars)
        print(f"▶ 上櫃 TPEx：{len(bars)} 檔 ({d_otc})")
        all_bars.extend(bars)
        market_stats.append(("上櫃", d_otc, len(bars)))
    except Exception as e:
        print(f"❌ 上櫃抓取失敗：{e}")

    # 3. 興櫃
    try:
        d_emg, bars = fetch_emerging()
        bars = keep(bars)
        print(f"▶ 興櫃 _raw_tpex：{len(bars)} 檔 ({d_emg})")
        all_bars.extend(bars)
        market_stats.append(("興櫃", d_emg, len(bars)))
    except Exception as e:
        print(f"❌ 興櫃讀取失敗：{e}")

    if not all_bars:
        print("\n❌ 三市場都沒拿到資料，跳過")
        sys.exit(1)

    added, updated, new_codes = merge_into_klines(klines, all_bars)
    print(f"\n合併結果：新增 {added} 根 / 覆蓋 {updated} 根 / 新個股 {new_codes} 檔")

    out = {
        "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "maxDays": TARGET_DAYS,
        "stockCount": len(klines),
        "markets": [{"market": m, "date": d, "count": c} for m, d, c in market_stats],
        "klines": klines
    }
    with open(KLINES_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"✅ 已輸出：{KLINES_FILE.relative_to(ROOT)}")
    print(f"   共 {len(klines)} 檔個股，平均深度 {sum(len(v) for v in klines.values()) / max(len(klines), 1):.1f} 天")


if __name__ == "__main__":
    main()
