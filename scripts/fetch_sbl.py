"""
領富 AI · 借券（外資 / 大股東借券賣壓）抓取
資料來源：TWSE 信用額度總量管制餘額表 TWT93U
（包含「融券」與「借券賣出」兩部分）

端點：https://www.twse.com.tw/rwd/zh/marginTrading/TWT93U?date=YYYYMMDD&response=json
產出：data/sbl_live.json

每檔個股紀錄：
  short_balance        融券今日餘額（股）
  short_change         融券當日增減
  sbl_balance          借券賣出今日餘額（股）= 法人空頭部位
  sbl_change           借券賣出當日增減
  sbl_quota            次一營業日可借券限額
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


def fetch(date_str):
    url = f"https://www.twse.com.tw/rwd/zh/marginTrading/TWT93U?date={date_str}&response=json"
    req = Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except (URLError, ssl.SSLError):
        with urlopen(req, timeout=30, context=_INSECURE_CTX) as r:
            return json.loads(r.read().decode("utf-8"))


def safe_int(x):
    if x in (None, "", "-", " "):
        return 0
    try:
        return int(str(x).replace(",", "").replace("--", "0").strip() or "0")
    except (ValueError, TypeError):
        return 0


def transform(raw):
    """
    TWT93U 欄位（融券 + 借券賣出 並列）：
    [0]代號 [1]名稱
    融券: [2]前日餘額 [3]賣出 [4]買進 [5]現券 [6]今日餘額 [7]次營業日限額
    借券賣出: [8]前日餘額 [9]當日賣出 [10]當日還券 [11]當日調整 [12]當日餘額 [13]次營業日可限額
    [14]備註
    """
    out = {}
    rows = raw.get("data", [])
    for row in rows:
        if len(row) < 13:
            continue
        code = (row[0] or "").strip()
        name = (row[1] or "").strip()
        if not code or not name:
            continue
        # 含 ETF（4-6 位），前 4 位需為數字
        if not code[:4].isdigit():
            continue

        short_prev   = safe_int(row[2])
        short_today  = safe_int(row[6])
        sbl_prev     = safe_int(row[8])
        sbl_today    = safe_int(row[12])
        sbl_quota    = safe_int(row[13]) if len(row) > 13 else 0

        out[code] = {
            "code": code,
            "name": name,
            "short_balance":  short_today,
            "short_change":   short_today - short_prev,
            "sbl_balance":    sbl_today,
            "sbl_change":     sbl_today - sbl_prev,
            "sbl_quota":      sbl_quota,
        }
    return out


def main():
    print("=" * 60)
    print(f"借券資料抓取 ・ {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 60)

    raw = None
    date_str = ""
    for days_back in range(0, 5):
        d = datetime.now() - timedelta(days=days_back)
        date_str = d.strftime("%Y%m%d")
        try:
            print(f"\n▶ 嘗試 {date_str}...")
            raw = fetch(date_str)
            if raw.get("stat") == "OK" and raw.get("data"):
                print(f"  ✅ {raw.get('title', '')} ・ {raw.get('total', 0)} 筆")
                break
        except Exception as e:
            print(f"  ❌ {e}")
            raw = None
    if not raw or not raw.get("data"):
        print("\n❌ 5 天都沒資料")
        sys.exit(1)

    data = transform(raw)
    print(f"\n有效個股：{len(data)} 檔")

    payload = {
        "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source": "TWSE 信用額度總量管制餘額表 TWT93U（融券 + 借券賣出）",
        "sourceDate": date_str,
        "count": len(data),
        "data": data,
    }
    out = DATA_DIR / "sbl_live.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"✅ 已輸出：{out.relative_to(ROOT)}")

    # 借券賣出增加前 5（法人加碼放空）
    sbl_inc = sorted(data.values(), key=lambda x: x["sbl_change"], reverse=True)[:5]
    print("\n--- 借券賣出增加前 5 (法人空頭加碼) ---")
    for s in sbl_inc:
        print(f"  {s['code']} {s['name']:<12} 借券 +{s['sbl_change']:,} (餘 {s['sbl_balance']:,})")


if __name__ == "__main__":
    main()
