"""
領富 AI · 上櫃股票資料抓取（TPEx 櫃買中心主板）
資料來源：櫃買中心 OpenAPI（免費、公開）
端點：https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes

用法：python scripts/fetch_listed_tpex.py
產出：data/_listed_tpex.json （中間檔，由 merge_stocks.py 合併進 stocks_live.json）

注意：這跟 fetch_emerging.py 是不同端點
  - 上櫃（OTC mainboard）：tpex_mainboard_daily_close_quotes
  - 興櫃（Emerging）：tpex_esb_latest_statistics
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

TPEX_URL = "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes"
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

# 上櫃常見產業（跟興櫃/上市共用大致一樣）
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
    "88": "貿易百貨",
}


def fetch_tpex_json():
    req = Request(TPEX_URL, headers={
        "User-Agent": "LeadFu-AI/1.0 (+https://leadfuai.com)",
        "Accept": "application/json"
    })
    with urlopen(req, timeout=45) as resp:
        return json.loads(resp.read().decode("utf-8"))


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
        code = (r.get("SecuritiesCompanyCode") or "").strip()
        name = (r.get("CompanyName") or "").strip()
        if not code or not name:
            skipped += 1
            continue
        # 跳過權證、ETN 等
        if len(code) != 4 or not code.isdigit():
            skipped += 1
            continue

        close = safe_float(r.get("Close"))
        change = safe_float(r.get("Change"))
        # 上櫃 TradingShares 是股數，TradingVolume 是金額
        volume_shares = safe_int(r.get("TradingShares"))

        if close <= 0:
            skipped += 1
            continue

        stocks.append({
            "code": code,
            "name": name,
            "price": round(close, 2),
            "change": round(change, 2),
            "volume": volume_shares // 1000,
            "category": guess_industry(code),
            "status": "上櫃",
            "market": "otc"
        })
    return stocks, skipped


def main():
    print(f"[{datetime.now():%H:%M:%S}] 抓取 TPEx 上櫃 OpenAPI: {TPEX_URL}")
    try:
        raw = fetch_tpex_json()
    except (URLError, HTTPError) as e:
        print(f"❌ 連線失敗: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"原始筆數: {len(raw)}")
    stocks, skipped = transform(raw)
    print(f"轉換後有效個股: {len(stocks)}（略過 {skipped} 筆權證/ETN/無報價）")
    stocks.sort(key=lambda s: s["volume"], reverse=True)

    payload = {
        "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source": "TPEx 櫃買中心 OpenAPI",
        "market": "otc",
        "count": len(stocks),
        "stocks": stocks
    }

    out = DATA_DIR / "_listed_tpex.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"✅ 已輸出: {out.relative_to(ROOT)}")

    print("\n--- 成交量前 5 檔（上櫃） ---")
    for s in stocks[:5]:
        sign = "▲" if s["change"] > 0 else ("▼" if s["change"] < 0 else "－")
        print(f"  {s['code']} {s['name']}  {s['price']}  {sign} {s['change']:+.2f}  量 {s['volume']:,} 張  [{s['category']}]")


if __name__ == "__main__":
    main()
