"""
領富 AI · 三大法人買賣超日報抓取
資料來源：證交所 T86 三大法人買賣超日報

端點：https://www.twse.com.tw/rwd/zh/fund/T86?date=YYYYMMDD&selectType=ALL&response=json

抓取：上市股票（TWSE）的外資/投信/自營商買賣超
產出：data/institutional_live.json
"""

import json
import ssl
import sys
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36"

_INSECURE_CTX = ssl.create_default_context()
_INSECURE_CTX.check_hostname = False
_INSECURE_CTX.verify_mode = ssl.CERT_NONE


def fetch_t86(date_str):
    """抓 TWSE T86 三大法人買賣超日報
    date_str: 'YYYYMMDD'
    """
    url = f"https://www.twse.com.tw/rwd/zh/fund/T86?date={date_str}&selectType=ALL&response=json"
    req = Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (URLError, ssl.SSLError):
        with urlopen(req, timeout=30, context=_INSECURE_CTX) as resp:
            return json.loads(resp.read().decode("utf-8"))


def safe_int(x):
    """'319,357,360' → 319357360"""
    if not x:
        return 0
    try:
        return int(str(x).replace(",", "").replace("-", "0") if str(x).strip() in ("-", "") else str(x).replace(",", ""))
    except (ValueError, TypeError):
        return 0


def transform(raw):
    """T86 原始 → 字典結構 { code: {...} }
    fields:
      [0]證券代號 [1]證券名稱 [4]外陸資買賣超 [7]外資自營商買賣超
      [10]投信買賣超 [11]自營商買賣超(總) [18]三大法人買賣超
    """
    out = {}
    for row in raw.get("data", []):
        if len(row) < 19:
            continue
        code = (row[0] or "").strip()
        name = (row[1] or "").strip()
        if not code or not name:
            continue
        # 只要 4 碼純數字代號（過濾權證/ETF 等）
        if len(code) != 4 or not code.isdigit():
            continue

        # 股數 → 張數（÷ 1000）
        foreign_net = (safe_int(row[4]) + safe_int(row[7])) // 1000   # 外資+外資自營
        trust_net = safe_int(row[10]) // 1000                          # 投信
        dealer_net = safe_int(row[11]) // 1000                         # 自營商
        total_net = safe_int(row[18]) // 1000                          # 三大法人合計

        out[code] = {
            "code": code,
            "name": name,
            "foreign_net_lots": foreign_net,   # 外資買賣超（張，正=買超 負=賣超）
            "trust_net_lots":   trust_net,     # 投信
            "dealer_net_lots":  dealer_net,    # 自營商
            "total_net_lots":   total_net,     # 三大法人合計
            "market": "listed"
        }
    return out


def main():
    print("=" * 60)
    print(f"三大法人買賣超抓取 ・ {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 60)

    # 嘗試今日，如沒資料退回前 1-3 個工作日
    for days_back in range(0, 5):
        d = datetime.now() - timedelta(days=days_back)
        date_str = d.strftime("%Y%m%d")
        try:
            print(f"\n▶ 嘗試查詢 {date_str}...")
            raw = fetch_t86(date_str)
            stat = raw.get("stat", "")
            if stat == "OK" and raw.get("data"):
                print(f"  ✅ 找到資料：{raw.get('title', '')}")
                print(f"  原始筆數：{len(raw['data'])}")
                break
            else:
                print(f"  ⚠ 該日無資料 (stat={stat!r})")
        except Exception as e:
            print(f"  ❌ 查詢失敗：{e}")
            continue
    else:
        print("\n❌ 連 5 天都沒資料，可能是 TWSE 故障，先用既有檔案。")
        sys.exit(1)

    data = transform(raw)
    print(f"\n4 碼有效個股：{len(data)} 檔")

    payload = {
        "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source": "TWSE T86 三大法人買賣超日報",
        "sourceDate": date_str,
        "title": raw.get("title", ""),
        "count": len(data),
        "data": data
    }

    out = DATA_DIR / "institutional_live.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"✅ 已輸出：{out.relative_to(ROOT)}")

    # 顯示外資買超前 5 / 賣超前 5
    sorted_foreign = sorted(data.values(), key=lambda x: x["foreign_net_lots"], reverse=True)
    print("\n--- 外資買超前 5 ---")
    for s in sorted_foreign[:5]:
        print(f"  {s['code']} {s['name']:<10} 外資 +{s['foreign_net_lots']:,} 張・投信 {s['trust_net_lots']:+,}・自營 {s['dealer_net_lots']:+,}")
    print("\n--- 外資賣超前 5 ---")
    for s in sorted_foreign[-5:][::-1]:
        print(f"  {s['code']} {s['name']:<10} 外資 {s['foreign_net_lots']:+,} 張・投信 {s['trust_net_lots']:+,}・自營 {s['dealer_net_lots']:+,}")


if __name__ == "__main__":
    main()
