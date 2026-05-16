"""
領富 AI · 技術指標計算
從 data/klines.json 計算 KD、MACD、布林通道、RSI、5/10/20MA

產出：data/indicators_live.json
{
  "code": {
    "k": 75.3, "d": 68.2,                       # KD 9 日
    "macd": 1.23, "signal": 0.98, "histogram": 0.25,
    "rsi": 62.1,                                # RSI 14
    "ma5": 100.2, "ma10": 99.5, "ma20": 98.1,
    "bb_upper": 105.3, "bb_middle": 98.1, "bb_lower": 90.8,
    "signal_text": "中性偏多" / "黃金交叉" / "死亡交叉" 等
  }
}

註：klines.json 預設 30 天，MACD 26 EMA 在 30 天下會略失準（用足夠近似）。
"""

import json
import sys
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
KLINES = DATA_DIR / "klines.json"
OUT = DATA_DIR / "indicators_live.json"


def ema(values, period):
    """指數移動平均，回傳長度同 values 的列表"""
    if not values:
        return []
    k = 2.0 / (period + 1)
    out = [values[0]]
    for v in values[1:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def sma(values, period):
    """簡單移動平均，最後 N 個 → 1 個數"""
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def kd(klines, n=9):
    """KD 指標（9 日，標準台股流派）"""
    if len(klines) < n:
        return None, None
    rsv_list = []
    for i in range(n - 1, len(klines)):
        window = klines[i - n + 1: i + 1]
        hi = max(b["high"] for b in window)
        lo = min(b["low"] for b in window)
        close = klines[i]["close"]
        rsv = 50 if hi == lo else (close - lo) / (hi - lo) * 100
        rsv_list.append(rsv)
    # K, D 用前值 × 2/3 + 當值 × 1/3
    k_val = 50.0
    d_val = 50.0
    for rsv in rsv_list:
        k_val = k_val * 2 / 3 + rsv / 3
        d_val = d_val * 2 / 3 + k_val / 3
    return round(k_val, 2), round(d_val, 2)


def macd(closes, fast=12, slow=26, signal=9):
    """MACD 指標（DIF, MACD signal, OSC histogram）"""
    if len(closes) < slow:
        return None, None, None
    fast_ema = ema(closes, fast)
    slow_ema = ema(closes, slow)
    # 補齊長度（短期 EMA 開頭塞 NaN）
    dif = [f - s for f, s in zip(fast_ema, slow_ema)]
    sig = ema(dif, signal)
    hist = dif[-1] - sig[-1]
    return round(dif[-1], 3), round(sig[-1], 3), round(hist, 3)


def rsi(closes, period=14):
    """RSI 14 日"""
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    # Wilder smoothing
    avg_g = sum(gains[:period]) / period
    avg_l = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_g = (avg_g * (period - 1) + gains[i]) / period
        avg_l = (avg_l * (period - 1) + losses[i]) / period
    if avg_l == 0:
        return 100.0
    rs = avg_g / avg_l
    return round(100 - (100 / (1 + rs)), 2)


def bollinger(closes, period=20, dev=2.0):
    """布林通道（中軸 = SMA20，上下軌 = ±2σ）"""
    if len(closes) < period:
        return None, None, None
    window = closes[-period:]
    mid = sum(window) / period
    var = sum((x - mid) ** 2 for x in window) / period
    std = var ** 0.5
    return round(mid + dev * std, 2), round(mid, 2), round(mid - dev * std, 2)


def classify(k, d, dif, sig, rsi_v, close, bb_upper, bb_lower):
    """訊號文字（給散戶看得懂）"""
    signals = []
    if k is not None and d is not None:
        if k > d and k < 30:
            signals.append("KD 低檔黃金交叉")
        elif k > d and k > 70:
            signals.append("KD 高檔交叉")
        elif k < d and k > 70:
            signals.append("KD 高檔死亡交叉")
        elif k < d and k < 30:
            signals.append("KD 低檔交叉")
        elif k > d:
            signals.append("KD 多頭")
        else:
            signals.append("KD 空頭")
    if dif is not None and sig is not None:
        if dif > sig and dif > 0:
            signals.append("MACD 多頭")
        elif dif < sig and dif < 0:
            signals.append("MACD 空頭")
        elif dif > sig:
            signals.append("MACD 轉強")
    if rsi_v is not None:
        if rsi_v > 80:
            signals.append("RSI 超買")
        elif rsi_v < 20:
            signals.append("RSI 超賣")
    if bb_upper and close > bb_upper:
        signals.append("突破布林上軌")
    elif bb_lower and close < bb_lower:
        signals.append("跌破布林下軌")
    if not signals:
        return "盤整"
    return " · ".join(signals)


def main():
    print("=" * 60)
    print(f"技術指標計算 ・ {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 60)

    if not KLINES.exists():
        print(f"❌ {KLINES.relative_to(ROOT)} 不存在")
        sys.exit(1)

    with open(KLINES, "r", encoding="utf-8") as f:
        raw = json.load(f)
    klines_all = raw.get("klines", {})
    print(f"讀取 {len(klines_all)} 檔 K 線")

    out = {}
    for code, bars in klines_all.items():
        if not bars or len(bars) < 9:
            continue
        # bars 已按日期升冪
        bars_sorted = sorted(bars, key=lambda b: b.get("date", ""))
        closes = [b["close"] for b in bars_sorted]

        k_val, d_val = kd(bars_sorted)
        dif, sig, hist = macd(closes)
        rsi_v = rsi(closes)
        bb_up, bb_mid, bb_lo = bollinger(closes)
        ma5 = sma(closes, 5)
        ma10 = sma(closes, 10)
        ma20 = sma(closes, 20)

        last_close = closes[-1]
        signal_text = classify(k_val, d_val, dif, sig, rsi_v, last_close, bb_up, bb_lo)

        out[code] = {
            "k": k_val,
            "d": d_val,
            "macd_dif": dif,
            "macd_signal": sig,
            "macd_hist": hist,
            "rsi": rsi_v,
            "ma5":  round(ma5, 2) if ma5  is not None else None,
            "ma10": round(ma10, 2) if ma10 is not None else None,
            "ma20": round(ma20, 2) if ma20 is not None else None,
            "bb_upper":  bb_up,
            "bb_middle": bb_mid,
            "bb_lower":  bb_lo,
            "last_close": last_close,
            "signal": signal_text,
        }

    payload = {
        "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source": "領富 AI 內建技術指標計算（從 TWSE/TPEx K 線）",
        "count": len(out),
        "data": out,
    }

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"✅ 已輸出：{OUT.relative_to(ROOT)} ({len(out)} 檔)")

    # 顯示幾個示例
    print("\n--- 範例（前 3 檔有 KD 訊號的）---")
    for code, ind in list(out.items())[:5]:
        print(f"  {code}: K={ind['k']} D={ind['d']} MACD={ind['macd_dif']} RSI={ind['rsi']} | {ind['signal']}")


if __name__ == "__main__":
    main()
