"""
領富 AI · 三市場股票資料合併
讀取 _emerging.json + _listed_twse.json + _listed_tpex.json
輸出唯一 stocks_live.json（網站前端讀取）

每檔個股保留 market 欄位：
  - "listed"   = 上市 (TWSE)
  - "otc"      = 上櫃 (TPEx mainboard)
  - "emerging" = 興櫃 (TPEx ESB)

排序：依 (market 優先級, volume desc)，讓上市熱門股優先曝光
"""

import json
import sys
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

# 市場優先級（同成交量時，誰排前面）
MARKET_PRIORITY = {"listed": 0, "otc": 1, "emerging": 2}


def load_intermediate(name):
    """讀取單一市場的中間檔。沒有/壞掉返回 [] 不影響其他市場"""
    p = DATA_DIR / name
    if not p.exists():
        print(f"⚠ 找不到 {name}（該市場資料先跳過）")
        return [], None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        stocks = data.get("stocks", [])
        source = data.get("source", "")
        return stocks, source
    except Exception as e:
        print(f"⚠ 讀取 {name} 失敗: {e}")
        return [], None


def main():
    print("=" * 60)
    print(f"合併三市場股票資料 ・ {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 60)

    emerging, src_emerging = load_intermediate("_emerging.json")
    listed_twse, src_twse = load_intermediate("_listed_twse.json")
    listed_tpex, src_tpex = load_intermediate("_listed_tpex.json")

    # 讀公司基本資料拿真實產業名（覆蓋 fetcher 用代號前綴粗略推測的 category）
    companies = {}
    companies_path = DATA_DIR / "companies_live.json"
    if companies_path.exists():
        try:
            cdata = json.loads(companies_path.read_text(encoding="utf-8"))
            companies = cdata.get("companies", {}) or {}
            print(f"\n載入 companies_live.json: {len(companies)} 家公司可用產業資料")
        except Exception as e:
            print(f"\n⚠ 讀取 companies_live.json 失敗: {e}（產業欄位將沿用 fetcher 粗估）")
    else:
        print(f"\n⚠ 找不到 companies_live.json（產業欄位將沿用 fetcher 粗估）")

    enriched_count = 0
    def enrich(stocks):
        nonlocal enriched_count
        for s in stocks:
            co = companies.get(s.get("code"))
            if co:
                real = co.get("industryName") or ""
                if real:
                    s["category"] = real
                    enriched_count += 1
        return stocks

    listed_twse = enrich(listed_twse)
    listed_tpex = enrich(listed_tpex)
    emerging    = enrich(emerging)
    print(f"以真實產業覆蓋: {enriched_count} 檔")

    print(f"\n上市 (TWSE):  {len(listed_twse):>5} 檔")
    print(f"上櫃 (TPEx):  {len(listed_tpex):>5} 檔")
    print(f"興櫃 (ESB):   {len(emerging):>5} 檔")

    # 合併，按市場優先級 + 成交量排序
    all_stocks = listed_twse + listed_tpex + emerging

    # 去重（理論上不會重複，但保險起見以 code 為 key）
    seen = {}
    for s in all_stocks:
        code = s.get("code")
        if not code:
            continue
        if code in seen:
            # 已存在：保留優先級高的市場
            existing = seen[code]
            if MARKET_PRIORITY.get(s.get("market"), 9) < MARKET_PRIORITY.get(existing.get("market"), 9):
                seen[code] = s
        else:
            seen[code] = s

    merged = list(seen.values())
    merged.sort(key=lambda s: (
        MARKET_PRIORITY.get(s.get("market"), 9),
        -s.get("volume", 0)
    ))

    print(f"\n合併後總數: {len(merged):>5} 檔（去重後）")

    # 統計
    by_market = {}
    for s in merged:
        m = s.get("market", "unknown")
        by_market[m] = by_market.get(m, 0) + 1
    print(f"  分佈: {by_market}")

    sources = [s for s in (src_twse, src_tpex, src_emerging) if s]
    payload = {
        "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source": " + ".join(sources) if sources else "TWSE / TPEx OpenAPI",
        "sourceDate": datetime.now().strftime("%Y-%m-%d"),
        "stockCount": len(merged),
        "marketBreakdown": by_market,
        "stocks": merged,
        # 沿用前端期待的空欄位
        "news": [],
        "hotTopics": [],
        "details": {},
        "ipoCalendar": [],
        "announcements": []
    }

    out = DATA_DIR / "stocks_live.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 已輸出: {out.relative_to(ROOT)}（{len(merged)} 檔）")


if __name__ == "__main__":
    main()
