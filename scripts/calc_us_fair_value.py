"""
領富 AI · 美股版合理區間計算器 v1（LeadFu US Fair Value Range™ v1）
讀 data/us_stocks_meta.json + data/us_stocks_live.json，
用「52 週區間位置 + sector PE 帶」算出每檔的 label / position / confidence。

v1 信號（簡化版，用現有資料 < 1 秒跑完）：
  A. 52 週區間位置 = (price - w52_low) / (w52_high - w52_low)
  B. Sector PE 帶（業界知識常識值）— 區分科技/金融/能源/民生等
  C. 兩者綜合：52w 位置為主軸 → PE 偏低 push 一級「便宜」、PE 偏高 push 一級「貴」

v2 (未來) 會加：
  - 5y 歷史 P/E 分位（要 yfinance 抓財報歷史，較慢）
  - 200d MA 偏離度
  - ETF 殖利率 5y 分位

輸出 data/us_fair_value_live.json，schema 跟台股 fair_value_live.json 對齊
"""

import json
import sys
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
META = DATA_DIR / "us_stocks_meta.json"
LIVE = DATA_DIR / "us_stocks_live.json"
OUT = DATA_DIR / "us_fair_value_live.json"


# Sector PE 預期範圍（業界常識值，2026 年市況）
# 不同 sector 的「合理 PE」差異很大：科技股本來就 PE 高、金融能源 PE 低
SECTOR_PE_BANDS = {
    "Technology":            (15, 35),   # 七巨頭、半導體
    "Communication Services":(15, 30),   # Meta/GOOG/NFLX
    "Consumer Cyclical":     (15, 30),   # AMZN/TSLA/HD
    "Consumer Defensive":    (15, 25),   # PG/KO/WMT
    "Healthcare":            (15, 30),   # JNJ/LLY/UNH
    "Financial Services":    (8, 18),    # JPM/V/MA
    "Energy":                (8, 20),    # XOM/CVX
    "Industrials":           (12, 25),
    "Utilities":             (10, 22),
    "Real Estate":           (15, 30),   # REIT 含 O/VNQ
    "Basic Materials":       (10, 25),
}
DEFAULT_PE_BAND = (12, 28)   # 沒 sector 用這個

# label levels（跟台股 calc_fair_value.py 對齊）
LABELS = [
    "低於合理區間",   # idx 0  position < 0
    "合理區間下緣",   # idx 1  0-15%
    "合理偏低",       # idx 2  15-35%
    "合理區間中",     # idx 3  35-55%
    "合理偏高",       # idx 4  55-75%
    "合理區間上緣",   # idx 5  75-100%
    "高於合理區間",   # idx 6  > 100%
]


def calc_pe_shift(pe, sector):
    """PE 對 label 的 shift 量。cheap -2、低 -1、normal 0、高 +1、貴 +2"""
    if pe is None or pe <= 0 or pe > 500:   # PE 過高（虧損或剛轉盈）排除
        return 0, None
    band = SECTOR_PE_BANDS.get(sector or "", DEFAULT_PE_BAND)
    low, high = band
    if pe < low * 0.7:
        return -2, "cheap"
    if pe < low:
        return -1, "low"
    if pe <= high:
        return 0, "normal"
    if pe <= high * 1.5:
        return 1, "high"
    return 2, "expensive"


def calc_position_index(pos):
    """52w 位置 → label index"""
    if pos is None:
        return None
    if pos < 0:      return 0
    if pos < 0.15:   return 1
    if pos < 0.35:   return 2
    if pos < 0.55:   return 3
    if pos < 0.75:   return 4
    if pos <= 1.0:   return 5
    return 6


def is_etf_like(category):
    """ETF / 加密 / 退休防禦 用較寬鬆的 PE 判斷"""
    return "ETF" in (category or "") or "加密" in (category or "") or "退休" in (category or "")


def calc_one(ticker, meta_entry, live_entry):
    """單檔合理區間計算"""
    if not live_entry:
        return None
    price = live_entry.get("price")
    w52_low = live_entry.get("w52_low")
    w52_high = live_entry.get("w52_high")
    pe = live_entry.get("pe_ratio")
    yield_pct = live_entry.get("yield_pct")
    sector = live_entry.get("sector")
    category = meta_entry.get("category", "")

    if price is None or price <= 0 or w52_low is None or w52_high is None or w52_high <= w52_low:
        return None

    # A. 52 週位置
    pos = (price - w52_low) / (w52_high - w52_low)
    pos_idx = calc_position_index(pos)

    # B. PE 偏離（ETF 跳過 PE 修正、因 ETF 的 PE 是底層加權、意義不同）
    if is_etf_like(category):
        pe_shift, pe_zone = 0, "etf"
    else:
        pe_shift, pe_zone = calc_pe_shift(pe, sector)

    # 綜合：52w 位置為主軸 + PE 修正
    final_idx = max(0, min(6, pos_idx + pe_shift))
    label = LABELS[final_idx]

    # confidence：資料完整度
    confidence = 2
    if w52_low and w52_high:    confidence += 1   # 有 52w
    if pe and pe > 0:            confidence += 1   # 有 PE
    if yield_pct is not None:    confidence += 0.5   # 有 yield
    if sector and sector != "None": confidence += 0.5   # 有 sector
    confidence = round(min(5.0, confidence), 1)

    # 一句話 summary
    pos_pct = f"{pos*100:.0f}%"
    pe_str = f"PE {pe:.1f}" if pe and pe > 0 else "PE 無"
    if is_etf_like(category):
        if yield_pct and yield_pct >= 5:
            summary = f"配息 ETF（殖利率 {yield_pct:.1f}%）；52 週區間位於 {pos_pct} 位置"
        elif yield_pct and yield_pct >= 2:
            summary = f"平衡 ETF（殖利率 {yield_pct:.1f}%）；52 週區間位於 {pos_pct} 位置"
        else:
            summary = f"成長型 ETF（殖利率 {yield_pct or 0:.1f}%）；52 週區間位於 {pos_pct} 位置"
    else:
        zone_desc = {
            "cheap": "估值偏低",
            "low": "估值略低",
            "normal": "估值合理",
            "high": "估值偏高",
            "expensive": "估值偏貴",
            None: "PE 無資料",
        }.get(pe_zone, "估值不明")
        summary = f"{pe_str}（{zone_desc}）；52 週區間位於 {pos_pct} 位置"

    return {
        "ticker": ticker,
        "name_zh": meta_entry.get("name_zh"),
        "category": category,
        "price": round(price, 2),
        "low": round(w52_low, 2),
        "high": round(w52_high, 2),
        "position": round(pos, 3),
        "label": label,
        "confidence": confidence,
        "pe_ratio": round(pe, 1) if pe else None,
        "yield_pct": round(yield_pct, 2) if yield_pct else None,
        "summary": summary,
    }


def main():
    print("=" * 64)
    print(f"領富 AI · 美股合理區間計算 v1 ・ {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 64)

    meta = json.loads(META.read_text(encoding="utf-8"))
    live = json.loads(LIVE.read_text(encoding="utf-8"))
    meta_data = meta.get("data", {})
    live_data = live.get("data", {})
    print(f"資料：{len(meta_data)} meta / {len(live_data)} live\n")

    out = {}
    label_counts = {}
    skipped = []

    for ticker, m in meta_data.items():
        l = live_data.get(ticker)
        result = calc_one(ticker, m, l)
        if result:
            out[ticker] = result
            label_counts[result["label"]] = label_counts.get(result["label"], 0) + 1
        else:
            skipped.append(ticker)

    print(f"計算結果：{len(out)} 檔成功 / {len(skipped)} skipped\n")
    if skipped:
        print(f"  skipped (資料不全): {skipped}\n")

    print("位置分布：")
    for label in LABELS:
        cnt = label_counts.get(label, 0)
        bar = "█" * cnt
        print(f"  {label:<14} {cnt:>3}  {bar}")

    payload = {
        "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source": "LeadFu US Fair Value Range™ v1（52 週區間位置 + sector PE 帶 + yield）",
        "algorithm_version": "v1",
        "count": len(out),
        "data": out,
    }

    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ 已輸出：{OUT.relative_to(ROOT)}")

    # 範例展示
    print(f"\n--- 範例 ---")
    for t in ["AAPL", "NVDA", "TSLA", "SCHD", "JEPI", "VOO", "BRK-B", "IBIT"]:
        if t in out:
            r = out[t]
            print(f"  {t:<6} {r['label']:<8} ({r['position']*100:>5.1f}%)  {r['summary']}  conf {r['confidence']}⭐")


if __name__ == "__main__":
    main()
