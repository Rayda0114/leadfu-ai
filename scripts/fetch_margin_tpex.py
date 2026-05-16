"""
領富 AI · 上櫃融資融券抓取（散戶籌碼面 - 上櫃）
資料來源：TPEx 櫃買中心「上櫃股票融資融券餘額」

端點：https://www.tpex.org.tw/www/zh-tw/margin/balance?response=json
產出：data/margin_tpex_live.json

每檔個股紀錄：
  margin_balance / margin_change / short_balance / short_change / net_offset
（欄位與 fetch_margin.py 上市版一致，方便前端共用）
"""

import json
import ssl
import sys
from datetime import datetime
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

URL = "https://www.tpex.org.tw/www/zh-tw/margin/balance?response=json"


def fetch_tpex_margin():
    req = Request(URL, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except (URLError, ssl.SSLError):
        with urlopen(req, timeout=30, context=_INSECURE_CTX) as r:
            return json.loads(r.read().decode("utf-8"))


def safe_int(x):
    if x in (None, "", "-"):
        return 0
    try:
        return int(str(x).replace(",", "").replace("--", "0").strip() or "0")
    except (ValueError, TypeError):
        return 0


def transform(raw):
    """
    TPEx 上櫃融資融券欄位：
    [0]代號 [1]名稱
    融資: [2]前資餘額 [3]資買 [4]資賣 [5]現償 [6]資餘額 [7]資屬證金 [8]資使用率 [9]資限額
    融券: [10]前券餘額 [11]券賣 [12]券買 [13]券償 [14]券餘額 [15]券屬證金 [16]券使用率 [17]券限額
    [18]資券相抵 [19]備註
    """
    out = {}
    if not raw.get("tables"):
        return out
    table = raw["tables"][0]
    for row in table.get("data", []):
        if len(row) < 15:
            continue
        code = (row[0] or "").strip()
        name = (row[1] or "").strip()
        if not code or not name or len(code) > 6:
            continue
        # 上櫃也有 4 位數股號，但 ETF 是 5-6 位。允許 4-6 位但須為數字（含字母如 00679B）
        if not code[:4].isdigit():
            continue

        margin_prev = safe_int(row[2])
        margin_today = safe_int(row[6])
        short_prev = safe_int(row[10])
        short_today = safe_int(row[14])

        out[code] = {
            "code": code,
            "name": name,
            "margin_balance":  margin_today,
            "margin_change":   margin_today - margin_prev,
            "short_balance":   short_today,
            "short_change":    short_today - short_prev,
            "net_offset":      safe_int(row[18]) if len(row) > 18 else 0,
            "market":          "TPEx",
        }
    return out


def main():
    print("=" * 60)
    print(f"上櫃融資融券抓取 ・ {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 60)

    try:
        raw = fetch_tpex_margin()
    except Exception as e:
        print(f"❌ TPEx 取資料失敗：{e}")
        sys.exit(1)

    if not raw.get("tables"):
        print("❌ 無資料表")
        sys.exit(1)

    table = raw["tables"][0]
    print(f"✅ {table.get('title', '')} - {table.get('date', '')}")

    data = transform(raw)
    print(f"有效個股：{len(data)} 檔")

    payload = {
        "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source": "TPEx 櫃買中心 上櫃股票融資融券餘額",
        "sourceDate": raw.get("date", ""),
        "count": len(data),
        "data": data,
    }
    out = DATA_DIR / "margin_tpex_live.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"✅ 已輸出：{out.relative_to(ROOT)}")

    # 顯示融資增加最多前 5（上櫃）
    margin_inc = sorted(data.values(), key=lambda x: x["margin_change"], reverse=True)[:5]
    print("\n--- 上櫃融資增加前 5 (散戶積極看多) ---")
    for s in margin_inc:
        print(f"  {s['code']} {s['name']:<12} 融資 +{s['margin_change']:,} (餘 {s['margin_balance']:,})")


if __name__ == "__main__":
    main()
