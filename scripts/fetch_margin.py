"""
領富 AI · 融資融券抓取（散戶籌碼面）
資料來源：證交所 MI_MARGN 每日信用交易彙總

端點：https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN
產出：data/margin_live.json

每檔個股紀錄：
  融資餘額、融資增減（散戶看多訊號）
  融券餘額、融券增減（散戶看空訊號）
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


def fetch_margin(date_str):
    url = f"https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN?date={date_str}&selectType=ALL&response=json"
    req = Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (URLError, ssl.SSLError):
        with urlopen(req, timeout=30, context=_INSECURE_CTX) as resp:
            return json.loads(resp.read().decode("utf-8"))


def safe_int(x):
    if x in (None, "", "-"):
        return 0
    try:
        return int(str(x).replace(",", "").replace("--", "0").strip() or "0")
    except (ValueError, TypeError):
        return 0


def transform(raw):
    """
    Table 1 fields:
    [0]代號 [1]名稱
    融資: [2]買 [3]賣 [4]現金償還 [5]前日餘額 [6]今日餘額 [7]次一營業日限額
    融券: [8]買 [9]賣 [10]現券償還 [11]前日餘額 [12]今日餘額 [13]次一營業日限額
    [14]資券互抵 [15]註記
    """
    out = {}
    if len(raw.get("tables", [])) < 2:
        return out
    table = raw["tables"][1]
    for row in table.get("data", []):
        if len(row) < 13:
            continue
        code = (row[0] or "").strip()
        name = (row[1] or "").strip()
        if not code or not name or len(code) != 4 or not code.isdigit():
            continue

        margin_prev = safe_int(row[5])    # 融資前日餘額
        margin_today = safe_int(row[6])   # 融資今日餘額
        short_prev = safe_int(row[11])    # 融券前日餘額
        short_today = safe_int(row[12])   # 融券今日餘額

        out[code] = {
            "code": code,
            "name": name,
            "margin_balance":  margin_today,         # 融資餘額（張）
            "margin_change":   margin_today - margin_prev,  # 融資增減（+ 散戶看多 / - 散戶減碼）
            "short_balance":   short_today,           # 融券餘額（張）
            "short_change":    short_today - short_prev,    # 融券增減（+ 散戶看空 / - 軋空訊號）
            "net_offset":      safe_int(row[14])      # 資券互抵
        }
    return out


def main():
    print("=" * 60)
    print(f"融資融券抓取 ・ {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 60)

    raw = None
    date_str = ""
    for days_back in range(0, 5):
        d = datetime.now() - timedelta(days=days_back)
        date_str = d.strftime("%Y%m%d")
        try:
            print(f"\n▶ 嘗試 {date_str}...")
            raw = fetch_margin(date_str)
            if raw.get("stat") == "OK" and raw.get("tables"):
                print(f"  ✅ {raw.get('tables', [{}])[0].get('title', '')}")
                break
        except Exception as e:
            print(f"  ❌ {e}")
    if not raw or not raw.get("tables"):
        print("\n❌ 5 天都沒資料，跳過")
        sys.exit(1)

    data = transform(raw)
    print(f"\n有效個股：{len(data)} 檔")

    payload = {
        "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source": "TWSE MI_MARGN 信用交易彙總",
        "sourceDate": date_str,
        "count": len(data),
        "data": data
    }
    out = DATA_DIR / "margin_live.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"✅ 已輸出：{out.relative_to(ROOT)}")

    # 顯示融資增加最多的前 5
    margin_inc = sorted(data.values(), key=lambda x: x["margin_change"], reverse=True)[:5]
    print("\n--- 融資增加前 5 (散戶積極看多) ---")
    for s in margin_inc:
        print(f"  {s['code']} {s['name']:<10} 融資 +{s['margin_change']:,} (餘 {s['margin_balance']:,}) 融券增減 {s['short_change']:+,}")


if __name__ == "__main__":
    main()
