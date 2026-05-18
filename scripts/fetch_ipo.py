"""
領富 AI · 新股 IPO 行事曆抓取
資料來源：TWSE OpenAPI 上市新公司資料
  https://openapi.twse.com.tw/v1/company/newlisting

每筆資料：
  Code             股票代號
  Company          公司名稱
  ApplicationDate  申請日（ROC）
  Chairman         董事長
  AmountofCapital  資本額（千元）
  CommitteeDate    審議委員會日
  ApprovedDate     核准日
  AgreementDate    簽約日
  ListingDate      掛牌日
  Underwriter      主辦承銷商
  UnderwritingPrice 承銷價

過濾邏輯：
  - 只保留近 90 天內掛牌 或 尚未掛牌（未來）的個股
  - 結果按 ListingDate 升冪排序
"""

import json
import ssl
import sys
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
OUT = DATA_DIR / "ipo_live.json"

URL = "https://openapi.twse.com.tw/v1/company/newlisting"
UA = "Mozilla/5.0 (Windows NT 10.0) Chrome/121.0.0.0 Safari/537.36"

_INSECURE_CTX = ssl.create_default_context()
_INSECURE_CTX.check_hostname = False
_INSECURE_CTX.verify_mode = ssl.CERT_NONE


def fetch_twse_ipo():
    req = Request(URL, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except (URLError, ssl.SSLError):
        with urlopen(req, timeout=30, context=_INSECURE_CTX) as r:
            return json.loads(r.read().decode("utf-8"))


def roc_to_iso(roc):
    """115/01/23 或 1150123 -> 2026-01-23"""
    if not roc or not isinstance(roc, str):
        return ""
    roc = roc.strip().replace("/", "")
    if not roc.isdigit():
        return ""
    # 容錯：可能是 6 或 7 碼
    if len(roc) == 7:
        year = int(roc[:3]) + 1911
        return f"{year}-{roc[3:5]}-{roc[5:7]}"
    if len(roc) == 6:
        year = int(roc[:2]) + 1911
        return f"{year}-{roc[2:4]}-{roc[4:6]}"
    return ""


def parse_capital(s):
    """資本額（千元）→ 整數（億元）"""
    if not s:
        return None
    try:
        thousand = int(str(s).replace(",", "").strip())
        return round(thousand / 100_000, 2)   # 千 → 億
    except (ValueError, TypeError):
        return None


def parse_price(s):
    """承銷價字串 → float（容錯）"""
    if not s:
        return None
    try:
        return float(str(s).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


def main():
    print("=" * 60)
    print(f"IPO 新股抓取 ・ {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 60)

    try:
        raw = fetch_twse_ipo()
    except Exception as e:
        print(f"❌ 抓取失敗：{e}")
        sys.exit(1)

    print(f"原始資料：{len(raw)} 筆")

    today = datetime.now().date()
    cutoff_past = today - timedelta(days=90)    # 過去 90 天內掛牌
    cutoff_future = today + timedelta(days=365) # 未來 1 年內

    rows = []
    for r in raw:
        code = (r.get("Code") or "").strip()
        company = (r.get("Company") or "").strip()
        if not code or not company:
            continue
        # 跳過代號太短或太長（異常資料）
        if len(code) < 4 or len(code) > 6:
            continue

        listing_iso = roc_to_iso(r.get("ListingDate"))
        apply_iso = roc_to_iso(r.get("ApplicationDate"))
        approved_iso = roc_to_iso(r.get("ApprovedDate"))
        committee_iso = roc_to_iso(r.get("CommitteeDate"))

        # 過濾：必須有掛牌日，且在合理範圍
        # 沒掛牌日的，可能還在 IPO 流程中（送件 → 審議 → 核准 → 掛牌 通常 6-18 個月）
        if not listing_iso:
            if apply_iso:
                try:
                    apply_d = datetime.strptime(apply_iso, "%Y-%m-%d").date()
                    # 保留申請日在「過去 18 個月內」的 — 涵蓋完整 IPO 流程
                    if apply_d < today - timedelta(days=540):
                        continue
                except ValueError:
                    continue
            else:
                continue
        else:
            try:
                list_d = datetime.strptime(listing_iso, "%Y-%m-%d").date()
                if list_d < cutoff_past or list_d > cutoff_future:
                    continue
            except ValueError:
                continue

        # 判斷狀態
        if listing_iso:
            try:
                list_d = datetime.strptime(listing_iso, "%Y-%m-%d").date()
                if list_d > today:
                    status = "即將掛牌"
                else:
                    status = "已掛牌"
                    days_ago = (today - list_d).days
                    if days_ago <= 7:
                        status = "新掛牌（本週）"
                    elif days_ago <= 30:
                        status = "新掛牌（近 1 月）"
            except ValueError:
                status = "—"
        else:
            status = "申請中"

        rows.append({
            "code": code,
            "name": company,
            "chairman": (r.get("Chairman") or "").strip(),
            "capital_yi": parse_capital(r.get("AmountofCapital ") or r.get("AmountofCapital")),
            "underwriter": (r.get("Underwriter") or "").strip(),
            "underwriting_price": parse_price(r.get("UnderwritingPrice")),
            "application_date": apply_iso,
            "approved_date": approved_iso,
            "committee_date": committee_iso,
            "listing_date": listing_iso,
            "market": "上市",
            "status": status,
            "note": (r.get("Note") or "").strip()[:100],
        })

    # 排序：未來日期優先，再來是最近過去
    def sort_key(r):
        d = r.get("listing_date") or r.get("application_date") or ""
        if not d:
            return (3, "")
        try:
            ld = datetime.strptime(d, "%Y-%m-%d").date()
            if ld > today:
                return (0, d)   # 即將掛牌：優先
            return (1, d)       # 已掛牌：依日期
        except ValueError:
            return (2, "")
    rows.sort(key=sort_key)

    payload = {
        "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source": "TWSE OpenAPI 上市新公司資料",
        "count": len(rows),
        "data": rows,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"\n有效資料：{len(rows)} 筆")
    print(f"✅ 已輸出：{OUT.relative_to(ROOT)}")

    # 顯示前 5 筆給人看
    print("\n--- 前 5 筆 ---")
    for r in rows[:5]:
        ld = r.get("listing_date") or "未定"
        price = r.get("underwriting_price") or "—"
        print(f"  {r['code']} {r['name']:<14} 掛牌 {ld}  承銷價 {price}  狀態 {r['status']}")


if __name__ == "__main__":
    main()
