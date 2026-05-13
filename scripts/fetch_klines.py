"""
領富 AI · K 線累積腳本
策略：每日跑一次，把 stocks_live.json 當日報價追加到 klines.json
      逐日累積，30 天後每檔有 30 根 K 線

產出：data/klines.json
格式：
{
  "updatedAt": "...",
  "klines": {
    "<code>": [
      {"date": "2026-05-13", "open": 24.5, "high": 25.15, "low": 24.5, "close": 24.7, "volume": 55},
      ...
    ],
    ...
  }
}

注意：第一次跑只會有 1 根 K 線，過了 N 天才會有 N 根。
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

STOCKS_FILE = DATA_DIR / "stocks_live.json"
KLINES_FILE = DATA_DIR / "klines.json"
RAW_PATTERN = "_raw_tpex_*.json"

MAX_DAYS = 30  # 每檔最多保留 30 天


def load_existing_klines():
    if KLINES_FILE.exists():
        with open(KLINES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"updatedAt": "", "klines": {}}


def load_today_stocks_with_ohlc():
    """從原始 TPEx 備份檔讀取，因為 stocks_live.json 沒有 OHLC，只有 close"""
    raw_files = sorted(DATA_DIR.glob(RAW_PATTERN), reverse=True)
    if not raw_files:
        return None, None
    latest = raw_files[0]
    with open(latest, "r", encoding="utf-8") as f:
        raw = json.load(f)

    # 解析資料日期
    date_iso = ""
    if raw and isinstance(raw, list):
        roc = (raw[0].get("Date") or "").strip()
        if len(roc) == 7:
            year = int(roc[:3]) + 1911
            date_iso = f"{year}-{roc[3:5]}-{roc[5:7]}"

    rows = []
    for r in raw:
        code = (r.get("SecuritiesCompanyCode") or "").strip()
        if not code:
            continue
        try:
            close  = float(r.get("LatestPrice") or 0)
            high   = float(r.get("Highest") or close)
            low    = float(r.get("Lowest") or close)
            prev   = float(r.get("PreviousAveragePrice") or close)
            vol    = int(float(r.get("TransactionVolume") or 0))
            # open 沒有提供 → 用 PreviousAveragePrice 當 open
            o = prev if prev > 0 else close
        except (ValueError, TypeError):
            continue
        if close <= 0:
            continue
        rows.append({
            "code": code,
            "open":   round(o, 2),
            "high":   round(high, 2),
            "low":    round(low, 2),
            "close":  round(close, 2),
            "volume": vol // 1000  # 股 → 張
        })
    return date_iso, rows


def main():
    print(f"[{datetime.now():%H:%M:%S}] 累積 K 線")

    if not STOCKS_FILE.exists():
        print(f"❌ 找不到 {STOCKS_FILE}，請先跑 fetch_emerging.py")
        sys.exit(1)

    today_date, today_rows = load_today_stocks_with_ohlc()
    if not today_rows:
        print("❌ 無原始備份檔可讀")
        sys.exit(1)
    print(f"今日 ({today_date}) 有 {len(today_rows)} 檔資料")

    store = load_existing_klines()
    klines = store.get("klines", {})

    appended = 0
    updated = 0
    for r in today_rows:
        code = r["code"]
        entry = {
            "date":   today_date,
            "open":   r["open"],
            "high":   r["high"],
            "low":    r["low"],
            "close":  r["close"],
            "volume": r["volume"]
        }
        if code not in klines:
            klines[code] = []
        # 若今日已記錄 → 覆蓋
        if klines[code] and klines[code][-1].get("date") == today_date:
            klines[code][-1] = entry
            updated += 1
        else:
            klines[code].append(entry)
            appended += 1
        # 修剪只保留最後 MAX_DAYS 天
        if len(klines[code]) > MAX_DAYS:
            klines[code] = klines[code][-MAX_DAYS:]

    out = {
        "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "maxDays":   MAX_DAYS,
        "stockCount": len(klines),
        "klines":    klines
    }
    with open(KLINES_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"新增 {appended} 檔當日 K 線、更新 {updated} 檔")
    print(f"資料庫共 {len(klines)} 檔個股，平均深度 {sum(len(v) for v in klines.values()) / max(len(klines),1):.1f} 天")
    print(f"✅ 已輸出: {KLINES_FILE.relative_to(ROOT)}")

    # 顯示 3 檔範例
    print("\n--- 範例 ---")
    for i, (code, klist) in enumerate(klines.items()):
        if i >= 3: break
        last = klist[-1]
        print(f"  {code}: {len(klist)} 天 ・ 最新 {last['date']} O{last['open']} H{last['high']} L{last['low']} C{last['close']} 量{last['volume']}")


if __name__ == "__main__":
    main()
