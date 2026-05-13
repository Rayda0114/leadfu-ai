"""
領富 AI · 興櫃股票資料抓取腳本
資料來源：櫃買中心 TPEx OpenAPI（公開資料，免費）
端點：https://www.tpex.org.tw/openapi/v1/tpex_esb_latest_statistics

用法：
    python scripts/fetch_emerging.py
產出：
    data/stocks_live.json （網站前端讀取）
    data/_raw_tpex_<DATE>.json （原始備份）

排程：
    手動每日跑一次（盤後 14:00 之後）
    之後可接 GitHub Actions 自動化
"""

import json
import sys
import os
from datetime import datetime

# Windows console 預設 cp950，強制 UTF-8 才能印中文與 emoji
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

TPEX_URL = "https://www.tpex.org.tw/openapi/v1/tpex_esb_latest_statistics"
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

# 簡易產業分類（依代號開頭/常見產業對應）
# 之後可從 mops 或自建表擴充
INDUSTRY_HINTS = {
    "11": "水泥",       "12": "食品",       "13": "塑膠",      "14": "紡織",
    "15": "電機機械",   "16": "電器電纜",   "17": "化學",      "18": "玻璃陶瓷",
    "19": "造紙",       "20": "鋼鐵",       "21": "橡膠",      "22": "汽車",
    "23": "電子",       "24": "半導體",     "25": "金融保險",  "26": "建材營造",
    "27": "航運",       "28": "觀光餐旅",   "29": "百貨貿易",  "30": "電子",
    "31": "電子",       "32": "半導體",     "33": "電腦周邊",  "34": "光電",
    "35": "通訊網路",   "36": "電子零組件", "37": "電子通路",  "38": "資訊服務",
    "44": "生技醫療",   "46": "PCB",        "48": "半導體",    "49": "電腦周邊",
    "60": "金融",       "61": "證券",       "62": "金融控股",  "64": "金融",
    "65": "金融",       "66": "金融保險",   "67": "證券",      "68": "證券",
    "88": "貿易百貨",
}


def fetch_tpex_json():
    """從 TPEx OpenAPI 抓興櫃股票即時統計"""
    req = Request(
        TPEX_URL,
        headers={
            "User-Agent": "LeadFu-AI/1.0 (+https://friendly-mousse-33de3d.netlify.app)",
            "Accept": "application/json"
        }
    )
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def safe_float(x, default=0.0):
    try:
        if x is None or x == "":
            return default
        return float(x)
    except (ValueError, TypeError):
        return default


def safe_int(x, default=0):
    try:
        if x is None or x == "":
            return default
        return int(float(x))
    except (ValueError, TypeError):
        return default


def guess_industry(code):
    """從代號猜產業（粗略）"""
    if not code or len(code) < 4:
        return "其他"
    prefix2 = code[:2]
    return INDUSTRY_HINTS.get(prefix2, "其他")


def transform(raw_list):
    """把 TPEx 原始格式轉成領富 AI 網站需要的格式"""
    stocks = []
    skipped = 0

    for r in raw_list:
        code = (r.get("SecuritiesCompanyCode") or "").strip()
        name = (r.get("CompanyName") or "").strip()
        if not code or not name:
            skipped += 1
            continue

        price = safe_float(r.get("LatestPrice"))
        prev  = safe_float(r.get("PreviousAveragePrice"))

        # 沒有當日成交價，退而用昨日均價
        if price <= 0:
            price = prev
        if price <= 0:
            skipped += 1
            continue

        change = round(price - prev, 2) if prev > 0 else 0.0
        volume_shares = safe_int(r.get("TransactionVolume"))
        volume_lots   = volume_shares // 1000  # 股 → 張

        stocks.append({
            "code": code,
            "name": name,
            "price": round(price, 2),
            "change": change,
            "volume": volume_lots,
            "category": guess_industry(code),
            "status": "興櫃"
        })

    return stocks, skipped


def build_payload(stocks, source_date):
    """組裝最終 JSON，相容於前端原本的 STOCK_DATA 結構"""
    return {
        "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source": "TPEx 櫃買中心 OpenAPI",
        "sourceDate": source_date,
        "stockCount": len(stocks),
        "stocks": stocks,
        # 以下欄位前端會跟內嵌備份資料合併（main.js 處理）
        # 留空表示「請用 fallback 內嵌的」
        "news": [],
        "hotTopics": [],
        "details": {},
        "ipoCalendar": [],
        "announcements": []
    }


def main():
    print(f"[{datetime.now():%H:%M:%S}] 抓取 TPEx OpenAPI: {TPEX_URL}")
    try:
        raw = fetch_tpex_json()
    except (URLError, HTTPError) as e:
        print(f"❌ 連線失敗: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"原始筆數: {len(raw)}")

    source_date = ""
    if raw:
        # TPEx 用民國年: 1150513 → 2026-05-13
        roc = (raw[0].get("Date") or "").strip()
        if len(roc) == 7:
            year = int(roc[:3]) + 1911
            source_date = f"{year}-{roc[3:5]}-{roc[5:7]}"

    stocks, skipped = transform(raw)
    print(f"轉換後有效個股: {len(stocks)}  (略過 {skipped} 筆無報價/不完整資料)")
    print(f"資料日期: {source_date}")

    # 排序：依成交量大→小，盤面更熱的排前面
    stocks.sort(key=lambda s: s["volume"], reverse=True)

    payload = build_payload(stocks, source_date)

    # 原始備份
    raw_backup = DATA_DIR / f"_raw_tpex_{source_date or 'unknown'}.json"
    with open(raw_backup, "w", encoding="utf-8") as f:
        json.dump(raw, f, ensure_ascii=False, indent=2)
    print(f"📦 原始備份: {raw_backup.relative_to(ROOT)}")

    # 主要產出
    out = DATA_DIR / "stocks_live.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"✅ 已輸出: {out.relative_to(ROOT)}")

    # 顯示前 5 檔讓使用者確認
    print("\n--- 成交量前 5 檔 ---")
    for s in stocks[:5]:
        sign = "▲" if s["change"] > 0 else ("▼" if s["change"] < 0 else "－")
        print(f"  {s['code']} {s['name']}  價 {s['price']}  {sign} {s['change']:+.2f}  量 {s['volume']} 張  [{s['category']}]")


if __name__ == "__main__":
    main()
