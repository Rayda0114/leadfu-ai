"""
領富 AI · 估值指標抓取（本益比 / 殖利率 / 股價淨值比）
資料來源：證交所 BWIBBU_d 個股日本益比、殖利率及股價淨值比

端點：https://www.twse.com.tw/rwd/zh/afterTrading/BWIBBU_d
產出：data/valuation_live.json

欄位：
  證券代號 / 名稱 / 收盤價 / 殖利率(%) / 股利年度 / 本益比 / 股價淨值比 / 財報年/季
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


def fetch_bwibbu(date_str):
    url = f"https://www.twse.com.tw/rwd/zh/afterTrading/BWIBBU_d?date={date_str}&selectType=ALL&response=json"
    req = Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (URLError, ssl.SSLError):
        with urlopen(req, timeout=30, context=_INSECURE_CTX) as resp:
            return json.loads(resp.read().decode("utf-8"))


def safe_float(x):
    if x in (None, "", "-", "N/A"):
        return None
    try:
        return float(str(x).replace(",", ""))
    except (ValueError, TypeError):
        return None


def transform(raw):
    """
    fields: [代號, 名稱, 收盤價, 殖利率(%), 股利年度, 本益比, 股價淨值比, 財報年/季]
    """
    out = {}
    for row in raw.get("data", []):
        if len(row) < 8:
            continue
        code = (row[0] or "").strip()
        name = (row[1] or "").strip()
        if not code or not name or len(code) != 4 or not code.isdigit():
            continue
        out[code] = {
            "code": code,
            "name": name,
            "yield_pct":   safe_float(row[3]),  # 殖利率 %
            "dividend_yr": str(row[4] or "").strip(),
            "pe_ratio":    safe_float(row[5]),  # 本益比
            "pb_ratio":    safe_float(row[6]),  # 股價淨值比
            "report":      str(row[7] or "").strip()
        }
    return out


def main():
    print("=" * 60)
    print(f"估值指標抓取（本益比/殖利率/股價淨值比）・ {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 60)

    raw = None
    date_str = ""
    for days_back in range(0, 5):
        d = datetime.now() - timedelta(days=days_back)
        date_str = d.strftime("%Y%m%d")
        try:
            print(f"\n▶ 嘗試 {date_str}...")
            raw = fetch_bwibbu(date_str)
            if raw.get("stat") == "OK" and raw.get("data"):
                print(f"  ✅ {raw.get('title', '')}")
                print(f"  原始筆數：{len(raw['data'])}")
                break
        except Exception as e:
            print(f"  ❌ {e}")
    if not raw or not raw.get("data"):
        print("\n❌ 5 天都沒資料，跳過")
        sys.exit(1)

    data = transform(raw)
    print(f"\n有效個股：{len(data)} 檔")

    payload = {
        "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source": "TWSE BWIBBU_d 個股日本益比、殖利率及股價淨值比",
        "sourceDate": date_str,
        "count": len(data),
        "data": data
    }
    out = DATA_DIR / "valuation_live.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"✅ 已輸出：{out.relative_to(ROOT)}")

    # 顯示高殖利率前 5 / 低本益比前 5
    high_yield = sorted([s for s in data.values() if s["yield_pct"] is not None],
                       key=lambda x: x["yield_pct"] or 0, reverse=True)[:5]
    print("\n--- 殖利率前 5（最賺利息）---")
    for s in high_yield:
        pe = f"P/E {s['pe_ratio']}" if s['pe_ratio'] else "本益比 -"
        print(f"  {s['code']} {s['name']:<8} 殖利率 {s['yield_pct']:.2f}%・{pe}")


if __name__ == "__main__":
    main()
