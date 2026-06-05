#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
watchlist_alerts.py — 自選股「今日異動」偵測（給每日 LINE 推播用）

只偵測「當日新鮮事件」（每天用新資料算，不會同一件天天重複報）：
  🔥 爆量      ：今日量 ≥ 前 N 日均量 × 倍數
  🏦 外資大買/大賣：外資買賣超 ≥ ±門檻（張）
  📈 站上月線 / 📉 跌破月線：昨收 vs 今日 MA20 穿越（附技術 signal）

純 stdlib、只讀 data/*.json。klines 較大（~10MB），main 端只 load 一次。

單獨測試（用真實資料、不需 Supabase）：
  python scripts/watchlist_alerts.py 2330 2317 2454 2303 2881
"""
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# ── 門檻（可調）──
VOL_SPIKE_MULT = 2.0    # 爆量：今日量 ≥ 前 N 日均量的倍數
VOL_LOOKBACK = 5        # 均量回看天數
VOL_MIN_LOTS = 500      # 今日量至少這麼多張才算（濾掉冷門股雜訊）
# 外資大買/大賣：要「夠大」(絕對張數) 且「佔當日成交量比重夠高」才算異動，
# 否則大型權值股天天都有幾千張法人進出 → 會變成每天洗版、失去警示意義
FOREIGN_MIN = 1000      # 外資買賣超絕對門檻（張）
FOREIGN_PCT = 0.20      # 且外資淨額需佔當日成交量 ≥ 20%


def _load(name):
    try:
        return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[warn] 讀 {name} 失敗: {e}")
        return {}


def load_alert_data():
    """一次載入警示需要的資料（klines / 指標 / 法人）。"""
    return {
        "kl": _load("klines.json").get("klines", {}),
        "ind": _load("indicators_live.json").get("data", {}),
        "inst": _load("institutional_live.json").get("data", {}),
    }


def _alerts_for(code, kl, ind, inst):
    """回傳單一股票的警示字串 list（可能 0~多筆）。"""
    out = []
    series = kl.get(code) or []

    # 1) 爆量：今日量 vs 前 N 日均量
    if len(series) >= VOL_LOOKBACK + 1:
        today_vol = series[-1].get("volume") or 0
        prev = series[-VOL_LOOKBACK - 1:-1]
        avg = sum((d.get("volume") or 0) for d in prev) / len(prev) if prev else 0
        if avg > 0 and today_vol >= VOL_MIN_LOTS and today_vol >= avg * VOL_SPIKE_MULT:
            out.append(f"🔥 爆量：今日 {today_vol:,} 張，約近 {VOL_LOOKBACK} 日均量的 {today_vol / avg:.1f} 倍")

    # 2) 外資大買 / 大賣超（夠大 + 佔當日量比重夠高才算異動）
    it = inst.get(code)
    today_vol = (series[-1].get("volume") or 0) if series else 0
    if it and today_vol > 0:
        f = it.get("foreign_net_lots") or 0
        pct = abs(f) / today_vol
        if abs(f) >= FOREIGN_MIN and pct >= FOREIGN_PCT:
            if f > 0:
                out.append(f"🏦 外資大買超 {f:,} 張（佔今日量 {pct * 100:.0f}%）")
            else:
                out.append(f"🏦 外資大賣超 {abs(f):,} 張（佔今日量 {pct * 100:.0f}%）")

    # 3) 站上 / 跌破月線（昨收 vs 今日 MA20 穿越），附技術 signal
    ic = ind.get(code)
    if ic and len(series) >= 2:
        ma20 = ic.get("ma20")
        today_close = series[-1].get("close")
        prev_close = series[-2].get("close")
        sig = (ic.get("signal") or "").strip()
        if ma20 and today_close and prev_close:
            if prev_close <= ma20 < today_close:
                out.append(f"📈 站上月線（MA20 {ma20:.1f}）" + (f"｜{sig}" if sig else ""))
            elif prev_close >= ma20 > today_close:
                out.append(f"📉 跌破月線（MA20 {ma20:.1f}）" + (f"｜{sig}" if sig else ""))

    return out


def alerts_for_codes(codes, data):
    """給一組代號 + 已載入的 data，回傳 {code: [警示字串,...]}（只含有警示的股）。"""
    out = {}
    for c in codes:
        a = _alerts_for(c, data["kl"], data["ind"], data["inst"])
        if a:
            out[c] = a
    return out


if __name__ == "__main__":
    import sys
    codes = sys.argv[1:] or ["2330", "2317", "2454", "2308", "2303", "2881", "2882", "2891", "2412", "3008"]
    data = load_alert_data()
    print(f"[info] 載入 klines {len(data['kl'])}、指標 {len(data['ind'])}、法人 {len(data['inst'])}")
    res = alerts_for_codes(codes, data)
    print(f"[info] 測試 {len(codes)} 檔，{len(res)} 檔有警示：")
    for c, al in res.items():
        for a in al:
            print(f"  {c}：{a}")
    if not res:
        print("  （這批今天沒有觸發警示）")
