"""
領富 AI · 興櫃公司月營收抓取
資料來源：TPEx OpenAPI t187ap05_R

產出：data/revenue_live.json
       格式：{ "<code>": { name, monthRevenue, mom, yoy, ... } }
"""

import json
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

URL = "https://www.tpex.org.tw/openapi/v1/t187ap05_R"
UA = "LeadFu-AI/1.0 (+https://leadfu-ai.leadwealthai-ai.workers.dev)"


def fetch():
    req = Request(URL, headers={"User-Agent": UA, "Accept": "application/json"})
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


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
        return int(float(x))
    except (ValueError, TypeError):
        return 0


def safe_float(x, ndigits=2):
    try:
        return round(float(x), ndigits)
    except (ValueError, TypeError):
        return 0.0


def fmt_amount(n):
    """1780095 千元 → '17.8 億' / '1,780 萬'（單位是千元）"""
    if not n:
        return "0"
    if n >= 100_000:       # 千元 × 100000 = 1 億
        return f"{n/100_000:.2f} 億"
    if n >= 1_000:
        return f"{n/1_000:.1f} 千萬"
    return f"{n:,} 千"


def transform(raw):
    out = {}
    for r in raw:
        code = (r.get("公司代號") or "").strip()
        if not code:
            continue
        month_rev   = safe_int(r.get("營業收入-當月營收"))
        last_month  = safe_int(r.get("營業收入-上月營收"))
        last_year   = safe_int(r.get("營業收入-去年當月營收"))
        mom         = safe_float(r.get("營業收入-上月比較增減(%)"))
        yoy         = safe_float(r.get("營業收入-去年同月增減(%)"))
        cum_rev     = safe_int(r.get("累計營業收入-當月累計營收"))
        cum_last_y  = safe_int(r.get("累計營業收入-去年累計營收"))
        cum_yoy     = safe_float(r.get("累計營業收入-前期比較增減(%)"))

        out[code] = {
            "code": code,
            "name":         (r.get("公司名稱") or "").strip(),
            "industry":     (r.get("產業別") or "").strip(),
            "period":       to_iso_yyyymm(r.get("資料年月")),
            "monthRevenue":     month_rev,
            "monthRevenueFmt":  fmt_amount(month_rev),
            "lastMonth":     last_month,
            "lastYear":      last_year,
            "mom":           mom,
            "yoy":           yoy,
            "cumRevenue":    cum_rev,
            "cumRevenueFmt": fmt_amount(cum_rev),
            "cumLastYear":   cum_last_y,
            "cumYoy":        cum_yoy
        }
    return out


def main():
    print(f"[{datetime.now():%H:%M:%S}] 抓興櫃公司月營收")
    try:
        raw = fetch()
    except (URLError, HTTPError) as e:
        print(f"❌ {e}")
        sys.exit(1)

    print(f"原始筆數: {len(raw)}")
    revenue = transform(raw)
    print(f"有效公司: {len(revenue)}")

    payload = {
        "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source": "TPEx OpenAPI t187ap05_R",
        "count": len(revenue),
        "revenue": revenue
    }

    out = DATA_DIR / "revenue_live.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"✅ 已輸出: {out.relative_to(ROOT)}")

    # 顯示月增/年增最大的 3 檔
    sorted_yoy = sorted(revenue.values(), key=lambda r: r["yoy"], reverse=True)
    print("\n--- 年增率前 3 ---")
    for r in sorted_yoy[:3]:
        print(f"  {r['code']} {r['name']}  {r['period']}  "
              f"營收 {r['monthRevenueFmt']}  月增 {r['mom']:+.1f}%  年增 {r['yoy']:+.1f}%")


if __name__ == "__main__":
    main()
