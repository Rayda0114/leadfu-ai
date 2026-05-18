"""
領富 AI · 合理區間計算器（LeadFu Fair Value Range™）
專有演算法，整合 6 個訊號加權計算每檔個股的合理價格區間。

【內部使用 — 不公開演算法細節】

訊號組成（總權重 100%）：
  A. 同業 P/E 分位數 × TTM EPS    （基本面估值）   30%
  B. 布林通道 ± 2σ                  （統計區間）     20%
  C. 60 日（30 日資料）高低區間     （支撐壓力）     15%
  D. 月營收 YoY 修正                （成長溢價）     15%
  E. 三大法人方向                    （籌碼修正）     10%
  F. KD/MACD 動能                    （短期偏離）     10%

對外只露結果：fair_low、fair_high、position、confidence
對外文案統一為「領富 AI 合理區間（LeadFu Fair Value Range）」
"""

import json
import statistics
import sys
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUT = DATA_DIR / "fair_value_live.json"


def load_json(name):
    p = DATA_DIR / f"{name}.json"
    if not p.exists():
        return None
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def calc_industry_pe_percentile(stocks, valuation):
    """每個產業分別計算 P/E 25th / 75th percentile，給 Signal A 用"""
    by_industry = {}
    for s in stocks:
        cat = s.get("category", "其他")
        code = s["code"]
        v = valuation.get(code, {})
        pe = v.get("pe_ratio")
        if pe and pe > 0 and pe < 200:   # 排除負值與超極端
            by_industry.setdefault(cat, []).append(pe)

    result = {}
    for cat, pes in by_industry.items():
        if len(pes) < 5:   # 樣本太少跳過
            continue
        pes_sorted = sorted(pes)
        n = len(pes_sorted)
        result[cat] = {
            "p25": pes_sorted[int(n * 0.25)],
            "p50": pes_sorted[int(n * 0.50)],
            "p75": pes_sorted[int(n * 0.75)],
            "count": n
        }
    return result


def signal_a_industry_pe(stock, valuation_entry, industry_stats):
    """Signal A: 加權混合「同業 P/E 中位」與「個股自身 P/E」
    保留成長股應有的溢價，但向同業中位數靠攏。
    回傳 (low, high) 或 None
    """
    if not valuation_entry:
        return None
    pe = valuation_entry.get("pe_ratio")
    if not pe or pe <= 0 or pe > 100:
        return None
    cat = stock.get("category")
    stats = industry_stats.get(cat)
    if not stats:
        return None

    price = stock.get("price", 0)
    if price <= 0:
        return None
    eps = price / pe

    # 30% 同業 P/E 中位數 + 70% 個股自身 P/E
    # 這樣台積電（pe=30、同業中位=22）→ target = 0.3*22 + 0.7*30 = 26.8
    # 保留它的成長股溢價，但稍微往同業靠攏
    target_pe = 0.30 * stats["p50"] + 0.70 * pe

    # 區間 = target ± 18%
    low_pe = target_pe * 0.82
    high_pe = target_pe * 1.18

    return (low_pe * eps, high_pe * eps)


def signal_b_bollinger(indicator_entry):
    """Signal B: 布林通道 上/下軌"""
    if not indicator_entry:
        return None
    lo = indicator_entry.get("bb_lower")
    hi = indicator_entry.get("bb_upper")
    if not lo or not hi or lo <= 0 or hi <= lo:
        return None
    return (lo, hi)


def signal_c_klines_range(klines_for_stock):
    """Signal C: 過去 30 日（或更短）的最低/最高"""
    if not klines_for_stock or len(klines_for_stock) < 5:
        return None
    # 取最近 30 天（或全部）
    bars = sorted(klines_for_stock, key=lambda b: b.get("date", ""))[-30:]
    lows = [b["low"] for b in bars if b.get("low", 0) > 0]
    highs = [b["high"] for b in bars if b.get("high", 0) > 0]
    if not lows or not highs:
        return None
    return (min(lows), max(highs))


def signal_d_yoy_adjustment(revenue_entry):
    """Signal D: 月營收 YoY 對上限做乘數調整
    回傳 high_multiplier (1.0 = 不變)
    """
    if not revenue_entry:
        return 1.0
    yoy = revenue_entry.get("yoy")
    if yoy is None:
        return 1.0
    if yoy >= 50:
        return 1.12
    if yoy >= 30:
        return 1.08
    if yoy >= 15:
        return 1.04
    if yoy <= -30:
        return 0.88
    if yoy <= -15:
        return 0.92
    if yoy <= -5:
        return 0.97
    return 1.0


def signal_e_institutional_shift(inst_entry):
    """Signal E: 三大法人方向（最近一日）
    回傳 (low_shift, high_shift) 乘數
    """
    if not inst_entry:
        return (1.0, 1.0)
    foreign = inst_entry.get("foreign_net_lots", 0) or 0
    trust = inst_entry.get("trust_net_lots", 0) or 0
    total = inst_entry.get("total_net_lots", 0) or 0
    # 法人偏多
    if foreign > 1000 and trust > 0:
        return (1.02, 1.02)
    if total > 500:
        return (1.01, 1.01)
    # 法人偏空
    if foreign < -1000 and trust < 0:
        return (0.98, 0.98)
    if total < -500:
        return (0.99, 0.99)
    return (1.0, 1.0)


def signal_f_momentum(indicator_entry):
    """Signal F: KD/MACD 動能修正"""
    if not indicator_entry:
        return (1.0, 1.0)
    k = indicator_entry.get("k")
    d = indicator_entry.get("d")
    sig = indicator_entry.get("signal", "")

    low_mult, high_mult = 1.0, 1.0

    # 高檔多頭：上限略往上
    if k and d and k > 75 and k > d:
        high_mult *= 1.015
    # 低檔空頭：下限略往下
    if k and d and k < 25 and k < d:
        low_mult *= 0.985
    # 黃金交叉訊號加分
    if "黃金交叉" in sig:
        high_mult *= 1.01
    # 死亡交叉訊號減分
    if "死亡交叉" in sig:
        low_mult *= 0.99
    return (low_mult, high_mult)


def calc_position(price, low, high):
    """計算現價在區間哪個位置（0.0 ~ 1.0），可能 < 0 或 > 1"""
    if high <= low or price <= 0:
        return None
    return (price - low) / (high - low)


def position_label(pos):
    """位置文字標籤"""
    if pos is None:
        return "資料不足"
    if pos < 0:
        return "低於合理區間"
    if pos < 0.15:
        return "合理區間下緣"
    if pos < 0.35:
        return "合理偏低"
    if pos < 0.55:
        return "合理區間中"
    if pos < 0.75:
        return "合理偏高"
    if pos <= 1.0:
        return "合理區間上緣"
    return "高於合理區間"


def confidence_stars(signals_used):
    """信心度評分（1-5 顆星）"""
    score = 1.0   # 起步
    if "industry_pe" in signals_used:
        score += 2.0
    if "bollinger" in signals_used:
        score += 1.0
    if "klines_range" in signals_used:
        score += 0.5
    if "yoy_adj" in signals_used:
        score += 0.3
    if "institutional" in signals_used:
        score += 0.2
    return round(min(5.0, score), 1)


def calc_fair_value_for_stock(stock, ctx):
    """計算單檔個股的合理區間。回傳 dict 或 None"""
    code = stock["code"]
    price = stock.get("price", 0)
    if price <= 0:
        return None

    v_entry = ctx["valuation"].get(code, {})
    ind_entry = ctx["indicators"].get(code, {})
    rev_entry = ctx["revenue"].get(code, {})
    inst_entry = ctx["inst"].get(code, {})
    klines = ctx["klines"].get(code, [])
    industry_stats = ctx["industry_stats"]

    signals_used = []
    pairs = []   # [(low, high, weight)]

    # A. 同業 P/E
    a = signal_a_industry_pe(stock, v_entry, industry_stats)
    if a:
        pairs.append((a[0], a[1], 0.30))
        signals_used.append("industry_pe")

    # B. 布林
    b = signal_b_bollinger(ind_entry)
    if b:
        pairs.append((b[0], b[1], 0.20))
        signals_used.append("bollinger")

    # C. 30 日區間
    c = signal_c_klines_range(klines)
    if c:
        pairs.append((c[0], c[1], 0.15))
        signals_used.append("klines_range")

    # 至少要有一個基礎訊號
    if not pairs:
        return None

    # 加權平均
    total_weight = sum(p[2] for p in pairs)
    low_base = sum(p[0] * p[2] for p in pairs) / total_weight
    high_base = sum(p[1] * p[2] for p in pairs) / total_weight

    # D. YoY 乘數修正（影響上限）
    d_mult = signal_d_yoy_adjustment(rev_entry)
    if d_mult != 1.0:
        signals_used.append("yoy_adj")

    # E. 三大法人
    e_low_m, e_high_m = signal_e_institutional_shift(inst_entry)
    if (e_low_m, e_high_m) != (1.0, 1.0):
        signals_used.append("institutional")

    # F. 動能
    f_low_m, f_high_m = signal_f_momentum(ind_entry)
    if (f_low_m, f_high_m) != (1.0, 1.0):
        signals_used.append("momentum")

    low = low_base * e_low_m * f_low_m
    high = high_base * d_mult * e_high_m * f_high_m

    # Sanity: low < high, 兩者 > 0
    if low >= high or low <= 0:
        return None

    # 計算位置
    pos = calc_position(price, low, high)
    label = position_label(pos)
    confidence = confidence_stars(signals_used)

    return {
        "code": code,
        "name": stock.get("name"),
        "price": round(price, 2),
        "low": round(low, 2),
        "high": round(high, 2),
        "position": round(pos, 3) if pos is not None else None,
        "label": label,
        "confidence": confidence,
        # 注意：signals_used 內部保留，但不放進前端 JSON（保密）
    }


def main():
    print("=" * 60)
    print(f"領富 AI 合理區間計算 ・ {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 60)

    # 載入所有資料源
    stocks_data = load_json("stocks_live") or {}
    valuation = (load_json("valuation_live") or {}).get("data", {})
    indicators = (load_json("indicators_live") or {}).get("data", {})
    revenue = (load_json("revenue_live") or {}).get("revenue", {})
    inst = (load_json("institutional_live") or {}).get("data", {})
    klines = (load_json("klines") or {}).get("klines", {})

    stocks = stocks_data.get("stocks", [])
    print(f"資料：{len(stocks)} 檔個股 / {len(valuation)} 估值 / {len(indicators)} 技術 / {len(revenue)} 月營收 / {len(inst)} 法人 / {len(klines)} K 線")

    # 預先計算同業 P/E 統計
    industry_stats = calc_industry_pe_percentile(stocks, valuation)
    print(f"產業 P/E 統計：{len(industry_stats)} 個產業 ≥ 5 檔")

    ctx = {
        "valuation": valuation,
        "indicators": indicators,
        "revenue": revenue,
        "inst": inst,
        "klines": klines,
        "industry_stats": industry_stats,
    }

    out_data = {}
    label_counts = {}
    conf_total = 0
    for s in stocks:
        result = calc_fair_value_for_stock(s, ctx)
        if result:
            out_data[s["code"]] = result
            label_counts[result["label"]] = label_counts.get(result["label"], 0) + 1
            conf_total += result["confidence"]

    avg_conf = conf_total / len(out_data) if out_data else 0
    print(f"\n計算結果：{len(out_data)} 檔 / 平均信心度 {avg_conf:.1f} ⭐")
    print(f"\n位置分布：")
    for label, count in sorted(label_counts.items(), key=lambda x: -x[1]):
        print(f"  {label:<15} {count:>5}")

    payload = {
        "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source": "LeadFu Fair Value Range™ — 領富 AI 專有演算法",
        "count": len(out_data),
        "data": out_data,
    }

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 已輸出：{OUT.relative_to(ROOT)}")

    # 顯示 2330 範例
    if "2330" in out_data:
        r = out_data["2330"]
        print(f"\n--- 範例 2330 台積電 ---")
        print(f"  現價 {r['price']}")
        print(f"  合理區間 NT${r['low']:,.0f} ~ NT${r['high']:,.0f}")
        print(f"  位置 {r['position']*100:.1f}% → {r['label']}")
        print(f"  信心度 {r['confidence']} ⭐")


if __name__ == "__main__":
    main()
