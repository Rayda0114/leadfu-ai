"""
領富 AI · 公告資料抓取
資料來源：
  1. /mopsfin_t187ap04_O      上櫃公司每月重大訊息
  2. /tpex_esb_warning_information   興櫃注意股
  3. /tpex_esb_disposal_information  興櫃處置股

產出：data/announcements_live.json
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

BASE_TPEX = "https://www.tpex.org.tw/openapi/v1"
BASE_TWSE = "https://openapi.twse.com.tw/v1"
UA = "LeadFu-AI/1.0 (+https://leadfuai.com)"

_INSECURE_CTX = ssl.create_default_context()
_INSECURE_CTX.check_hostname = False
_INSECURE_CTX.verify_mode = ssl.CERT_NONE


def fetch_url(url, allow_insecure=False):
    req = Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (URLError, ssl.SSLError) as e:
        if allow_insecure and ("CERTIFICATE" in str(e) or isinstance(e.__cause__, ssl.SSLError)):
            with urlopen(req, timeout=30, context=_INSECURE_CTX) as resp:
                return json.loads(resp.read().decode("utf-8"))
        raise


def fetch(endpoint):
    """舊版相容：TPEx 端點"""
    return fetch_url(f"{BASE_TPEX}/{endpoint}")


def roc_to_iso(roc_date):
    """民國年 1150513 → 西元 2026-05-13"""
    if not roc_date or len(str(roc_date)) != 7:
        return ""
    s = str(roc_date)
    try:
        year = int(s[:3]) + 1911
        return f"{year}-{s[3:5]}-{s[5:7]}"
    except ValueError:
        return ""


def normalize_major_tpex(raw):
    """上櫃重大訊息（TPEx 格式）"""
    out = []
    for r in raw:
        date = roc_to_iso(r.get("Date", ""))
        title = (r.get("主旨") or "").strip()
        code  = (r.get("SecuritiesCompanyCode") or "").strip()
        name  = (r.get("CompanyName") or "").strip()
        if not (title and code):
            continue
        if len(title) > 80:
            title = title[:78] + "..."
        out.append({
            "date": date, "code": code, "name": name,
            "title": title, "type": "重大訊息", "market": "otc"
        })
    return out


def normalize_major_twse(raw):
    """上市重大訊息（TWSE 格式）"""
    out = []
    for r in raw:
        date = roc_to_iso(r.get("發言日期") or r.get("出表日期", ""))
        title = (r.get("主旨 ") or r.get("主旨") or "").strip()  # TWSE 欄位名後面有空格
        code  = (r.get("公司代號") or "").strip()
        name  = (r.get("公司名稱") or "").strip()
        if not (title and code):
            continue
        if len(title) > 80:
            title = title[:78] + "..."
        out.append({
            "date": date, "code": code, "name": name,
            "title": title, "type": "重大訊息", "market": "listed"
        })
    return out


def normalize_warning(raw):
    """興櫃注意股"""
    out = []
    for r in raw:
        code = (r.get("證券代號") or "").strip()
        name = (r.get("證券名稱") or "").strip()
        info = (r.get("注意股資訊") or "").strip()
        date = roc_to_iso(r.get("公告日期", ""))
        if not (code and name and info):
            continue
        if len(info) > 80:
            info = info[:78] + "..."
        out.append({
            "date": date,
            "code": code,
            "name": name,
            "title": "[注意股] " + info,
            "type": "注意股"
        })
    return out


def normalize_disposal(raw):
    """興櫃處置股"""
    out = []
    for r in raw:
        code = (r.get("證券代號") or "").strip()
        name = (r.get("證券名稱") or "").strip()
        reason = (r.get("處置原因") or "").strip()
        detail = (r.get("處置內容") or "").strip()
        date = roc_to_iso(r.get("公告日期", ""))
        if not (code and name):
            continue
        title = f"[處置股] {reason}"
        if detail:
            title += " ・ " + detail
        if len(title) > 80:
            title = title[:78] + "..."
        out.append({
            "date": date,
            "code": code,
            "name": name,
            "title": title,
            "type": "處置股"
        })
    return out


def main():
    print(f"[{datetime.now():%H:%M:%S}] 抓取公告資料")
    sources = [
        # (URL, normalizer, label, allow_insecure)
        (f"{BASE_TWSE}/opendata/t187ap04_L",         normalize_major_twse, "上市重大訊息", True),
        (f"{BASE_TPEX}/mopsfin_t187ap04_O",          normalize_major_tpex, "上櫃重大訊息", False),
        (f"{BASE_TPEX}/tpex_esb_warning_information",  normalize_warning,    "興櫃注意股",    False),
        (f"{BASE_TPEX}/tpex_esb_disposal_information", normalize_disposal,   "興櫃處置股",    False),
    ]

    all_ann = []
    for url, normalizer, label, allow_insecure in sources:
        try:
            raw = fetch_url(url, allow_insecure=allow_insecure)
            items = normalizer(raw)
            print(f"  {label}: 原始 {len(raw)} → 有效 {len(items)}")
            all_ann.extend(items)
        except (URLError, HTTPError, ValueError, ssl.SSLError) as e:
            print(f"  {label}: ❌ {e}")

    # 排序：日期倒序
    all_ann.sort(key=lambda a: a.get("date", ""), reverse=True)
    # 上限 120 筆（三市場資料量大，給多一點）
    all_ann = all_ann[:120]

    print(f"\n合計 {len(all_ann)} 筆公告")
    for a in all_ann[:5]:
        print(f"  {a['date']}  {a['code']} {a['name']}  [{a['type']}]  {a['title'][:50]}")

    payload = {
        "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source": "TPEx OpenAPI（上櫃重大訊息 + 興櫃注意/處置）",
        "count": len(all_ann),
        "announcements": all_ann
    }

    out = DATA_DIR / "announcements_live.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 已輸出: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
