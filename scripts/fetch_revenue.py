"""
領富 AI · 全市場公司月營收抓取
資料來源：三個免費公開 OpenAPI

端點：
  上市 TWSE: https://openapi.twse.com.tw/v1/opendata/t187ap05_L
  上櫃 TPEx: https://www.tpex.org.tw/openapi/v1/t187ap05_O
  興櫃 TPEx: https://www.tpex.org.tw/openapi/v1/t187ap05_R

產出：data/revenue_live.json
  格式：{ "<code>": { name, monthRevenue, mom, yoy, market, ... } }
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

URL_LISTED   = "https://openapi.twse.com.tw/v1/opendata/t187ap05_L"
URL_OTC      = "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap05_O"
URL_EMERGING = "https://www.tpex.org.tw/openapi/v1/t187ap05_R"
UA = "LeadFu-AI/1.0 (+https://leadfuai.com)"

_INSECURE_CTX = ssl.create_default_context()
_INSECURE_CTX.check_hostname = False
_INSECURE_CTX.verify_mode = ssl.CERT_NONE


def fetch_json(url, allow_insecure=False):
    req = Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urlopen(req, timeout=45) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (URLError, ssl.SSLError) as e:
        if allow_insecure and ("CERTIFICATE" in str(e) or isinstance(e.__cause__, ssl.SSLError)):
            print(f"  ⚠ SSL 驗證失敗，改用 unverified context")
            with urlopen(req, timeout=45, context=_INSECURE_CTX) as resp:
                return json.loads(resp.read().decode("utf-8"))
        raise


def to_iso_yyyymm(roc_yyyymm):
    """11504 → '2026/04'"""
    s = str(roc_yyyymm or "").strip()
    if len(s) != 5:
        return ""
    try:
        return f"{int(s[:3]) + 1911}/{s[3:5]}"
    except ValueError:
        return ""


def safe_int(x):
    try:
        return int(float(str(x).replace(",", "")))
    except (ValueError, TypeError):
        return 0


def safe_float(x, ndigits=2):
    try:
        return round(float(str(x).replace(",", "")), ndigits)
    except (ValueError, TypeError):
        return 0.0


def fmt_amount(n):
    """單位是千元：1,780,095 千元 → '17.8 億'"""
    if not n:
        return "0"
    if n >= 100_000:
        return f"{n/100_000:.2f} 億"
    if n >= 1_000:
        return f"{n/1_000:.1f} 千萬"
    return f"{n:,} 千"


def transform_record(r, market):
    """三市場 API 欄位都用中文 key 且結構一致"""
    code = (r.get("公司代號") or "").strip()
    if not code:
        return None

    month_rev  = safe_int(r.get("營業收入-當月營收"))
    last_month = safe_int(r.get("營業收入-上月營收"))
    last_year  = safe_int(r.get("營業收入-去年當月營收"))
    mom        = safe_float(r.get("營業收入-上月比較增減(%)"))
    yoy        = safe_float(r.get("營業收入-去年同月增減(%)"))
    cum_rev    = safe_int(r.get("累計營業收入-當月累計營收"))
    cum_last_y = safe_int(r.get("累計營業收入-去年累計營收"))
    cum_yoy    = safe_float(r.get("累計營業收入-前期比較增減(%)"))

    return code, {
        "code":             code,
        "name":             (r.get("公司名稱") or "").strip(),
        "industry":         (r.get("產業別") or "").strip(),
        "period":           to_iso_yyyymm(r.get("資料年月")),
        "monthRevenue":     month_rev,
        "monthRevenueFmt":  fmt_amount(month_rev),
        "lastMonth":        last_month,
        "lastYear":         last_year,
        "mom":              mom,
        "yoy":              yoy,
        "cumRevenue":       cum_rev,
        "cumRevenueFmt":    fmt_amount(cum_rev),
        "cumLastYear":      cum_last_y,
        "cumYoy":           cum_yoy,
        "market":           market
    }


def fetch_market(name, url, market, allow_insecure=False):
    print(f"\n▶ 抓 {name}: {url}")
    try:
        raw = fetch_json(url, allow_insecure=allow_insecure)
    except Exception as e:
        print(f"  ❌ 失敗: {e}")
        return {}

    print(f"  原始筆數: {len(raw)}")
    out = {}
    for r in raw:
        result = transform_record(r, market)
        if result:
            code, info = result
            out[code] = info
    print(f"  有效公司: {len(out)}")
    return out


def main():
    print("=" * 60)
    print(f"全市場月營收抓取 ・ {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 60)

    listed   = fetch_market("上市 (TWSE)", URL_LISTED,   "listed",   allow_insecure=True)
    otc      = fetch_market("上櫃 (TPEx)", URL_OTC,      "otc")
    emerging = fetch_market("興櫃 (TPEx)", URL_EMERGING, "emerging")

    revenue = {}
    revenue.update(emerging)
    revenue.update(otc)
    revenue.update(listed)

    print(f"\n合併後總公司數: {len(revenue)}")

    payload = {
        "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source": "TWSE + TPEx OpenAPI (t187ap05_L/_O/_R)",
        "count": len(revenue),
        "marketBreakdown": {
            "listed":   len(listed),
            "otc":      len(otc),
            "emerging": len(emerging)
        },
        "revenue": revenue
    }

    out = DATA_DIR / "revenue_live.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"✅ 已輸出: {out.relative_to(ROOT)} ({len(revenue)} 家)")

    # 年增率前 3
    sorted_yoy = sorted(revenue.values(), key=lambda r: r["yoy"], reverse=True)
    print("\n--- 年增率前 3 ---")
    for r in sorted_yoy[:3]:
        print(f"  [{r['market']:<8}] {r['code']} {r['name']}  {r['period']}  "
              f"營收 {r['monthRevenueFmt']}  月增 {r['mom']:+.1f}%  年增 {r['yoy']:+.1f}%")


if __name__ == "__main__":
    main()
