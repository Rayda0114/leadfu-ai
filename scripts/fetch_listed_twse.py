"""
領富 AI · 上市股票資料抓取（TWSE 證交所）
資料來源：證交所 OpenAPI（公開、免費、無金鑰）
端點：https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL

用法：python scripts/fetch_listed_twse.py
產出：data/_listed_twse.json （中間檔，由 merge_stocks.py 合併進 stocks_live.json）

排程：盤後 14:30 後執行（TWSE 大約 13:50-14:00 更新當日資料）
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

TWSE_URL = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"

# TWSE 政府 API 的 SSL 憑證鏈 Python CA 抓不到（Windows 上 certifi 套件版本問題常見）
# 因為是公開政府資料，無認證、無敏感性，這裡退而求其次用不驗證的 SSL context
_INSECURE_CTX = ssl.create_default_context()
_INSECURE_CTX.check_hostname = False
_INSECURE_CTX.verify_mode = ssl.CERT_NONE
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

# 上市常見產業（從 TWSE 代號前綴推測）
INDUSTRY_HINTS = {
    "11": "水泥", "12": "食品", "13": "塑膠", "14": "紡織",
    "15": "電機機械", "16": "電器電纜", "17": "化學", "18": "玻璃陶瓷",
    "19": "造紙", "20": "鋼鐵", "21": "橡膠", "22": "汽車",
    "23": "電子", "24": "半導體", "25": "金融保險", "26": "建材營造",
    "27": "航運", "28": "觀光餐旅", "29": "百貨貿易",
    "30": "電子", "31": "電子", "32": "半導體", "33": "電腦周邊",
    "34": "光電", "35": "通訊網路", "36": "電子零組件",
    "37": "電子通路", "38": "資訊服務",
    "44": "生技醫療", "46": "PCB", "48": "半導體", "49": "電腦周邊",
    "60": "金融", "61": "證券", "62": "金融控股",
    "88": "貿易百貨", "91": "其他",
}


def fetch_twse_json():
    req = Request(TWSE_URL, headers={
        "User-Agent": "LeadFu-AI/1.0 (+https://leadfuai.com)",
        "Accept": "application/json"
    })
    # 先試正常 SSL，失敗就用不驗證 context 退而求其次
    try:
        with urlopen(req, timeout=45) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (URLError, ssl.SSLError) as e:
        if "CERTIFICATE" in str(e) or isinstance(e.__cause__, ssl.SSLError):
            print("⚠ SSL 驗證失敗，改用 unverified context（公開資料 OK）")
            with urlopen(req, timeout=45, context=_INSECURE_CTX) as resp:
                return json.loads(resp.read().decode("utf-8"))
        raise


def safe_float(x, default=0.0):
    try:
        if x is None or x in ("", "--", "-"):
            return default
        s = str(x).replace(",", "")
        return float(s)
    except (ValueError, TypeError):
        return default


def safe_int(x, default=0):
    try:
        if x is None or x in ("", "--", "-"):
            return default
        s = str(x).replace(",", "")
        return int(float(s))
    except (ValueError, TypeError):
        return default


def guess_industry(code):
    if not code or len(code) < 4:
        return "其他"
    return INDUSTRY_HINTS.get(code[:2], "其他")


def transform(raw_list):
    stocks = []
    skipped = 0
    for r in raw_list:
        code = (r.get("Code") or "").strip()
        name = (r.get("Name") or "").strip()
        if not code or not name:
            skipped += 1
            continue
        # 跳過權證、ETF、特別股等非普通股（代號通常 5-6 碼以上）
        if len(code) != 4 or not code.isdigit():
            skipped += 1
            continue

        close = safe_float(r.get("ClosingPrice"))
        change = safe_float(r.get("Change"))
        volume_shares = safe_int(r.get("TradeVolume"))

        if close <= 0:
            # 沒收盤價就跳過
            skipped += 1
            continue

        stocks.append({
            "code": code,
            "name": name,
            "price": round(close, 2),
            "change": round(change, 2),
            "volume": volume_shares // 1000,   # 股 → 張
            "category": guess_industry(code),
            "status": "上市",
            "market": "listed"
        })
    return stocks, skipped


def main():
    print(f"[{datetime.now():%H:%M:%S}] 抓取 TWSE OpenAPI: {TWSE_URL}")
    try:
        raw = fetch_twse_json()
    except (URLError, HTTPError) as e:
        print(f"❌ 連線失敗: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"原始筆數: {len(raw)}")
    stocks, skipped = transform(raw)
    print(f"轉換後有效個股: {len(stocks)}（略過 {skipped} 筆權證/ETF/無報價）")
    stocks.sort(key=lambda s: s["volume"], reverse=True)

    payload = {
        "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source": "TWSE 證交所 OpenAPI",
        "market": "listed",
        "count": len(stocks),
        "stocks": stocks
    }

    out = DATA_DIR / "_listed_twse.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"✅ 已輸出: {out.relative_to(ROOT)}")

    print("\n--- 成交量前 5 檔（上市） ---")
    for s in stocks[:5]:
        sign = "▲" if s["change"] > 0 else ("▼" if s["change"] < 0 else "－")
        print(f"  {s['code']} {s['name']}  {s['price']}  {sign} {s['change']:+.2f}  量 {s['volume']:,} 張  [{s['category']}]")


if __name__ == "__main__":
    main()
