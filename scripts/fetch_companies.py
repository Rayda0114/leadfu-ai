"""
領富 AI · 興櫃公司基本資料抓取
資料來源：TPEx OpenAPI mopsfin_t187ap03_O (約 887 筆)

包含：董事長、總經理、發言人、地址、電話、Email、網站、
      實收資本額、成立日期、上市日期、簽證會計師、股票代理人...

產出：data/companies_live.json
       格式：{ "<code>": { name, chairman, ... }, ... }  方便 main.js O(1) 查
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

URL = "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_R"   # _R 結尾 = 興櫃，_O 結尾是上櫃（不要用錯）
UA = "LeadFu-AI/1.0 (+https://leadfu-ai.pages.dev)"


def fetch():
    req = Request(URL, headers={"User-Agent": UA, "Accept": "application/json"})
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def parse_date(s):
    """支援兩種格式：
       - 西元 YYYYMMDD (8 位數，例如 '19670218')
       - 民國 YYYMMDD  (7 位數，例如 '0701021')
    """
    if not s:
        return ""
    s = str(s).strip()
    try:
        if len(s) == 8:               # 西元
            return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
        if len(s) == 7:               # 民國
            year = int(s[:3]) + 1911
            return f"{year}-{s[3:5]}-{s[5:7]}"
    except (ValueError, IndexError):
        pass
    return ""


def clean(v):
    """空值統一回空字串"""
    if v is None:
        return ""
    s = str(v).strip()
    return "" if s in ("", "-", "─") else s


def fmt_capital(s):
    """實收資本額：1000000 → '1,000 千' 或 '10 億'"""
    s = clean(s)
    if not s:
        return ""
    try:
        n = float(s)
        if n >= 1e8:
            return f"{n/1e8:.2f} 億"
        if n >= 1e4:
            return f"{n/1e4:.1f} 萬"
        return f"{n:,.0f}"
    except ValueError:
        return s


def transform(raw):
    """轉成 { code: company_info } 字典，方便前端 O(1) 查"""
    out = {}
    for r in raw:
        code = clean(r.get("SecuritiesCompanyCode"))
        if not code:
            continue
        out[code] = {
            "code":         code,
            "name":         clean(r.get("CompanyName")),
            "abbrev":       clean(r.get("CompanyAbbreviation")),
            "industry":     clean(r.get("SecuritiesIndustryCode")),
            "address":      clean(r.get("Address")),
            "taxId":        clean(r.get("UnifiedBusinessNo.")),
            "chairman":     clean(r.get("Chairman")),
            "president":    clean(r.get("GeneralManager")),
            "spokesman":    clean(r.get("Spokesman")),
            "spokesmanTitle": clean(r.get("TitleOfSpokesman")),
            "deputy":       clean(r.get("DeputySpokesperson")),
            "phone":        clean(r.get("Telephone")),
            "fax":          clean(r.get("Fax")),
            "email":        clean(r.get("EmailAddress")),
            "website":      clean(r.get("WebAddress")),
            "founded":      parse_date(r.get("DateOfIncorporation")),
            "listed":       parse_date(r.get("DateOfListing")),
            "parValue":     clean(r.get("ParValueOfCommonStock")),
            "capital":      fmt_capital(r.get("Paidin.Capital.NTDollars")),
            "issuedShares": clean(r.get("IssueShares")),
            "stockAgent":   clean(r.get("StockTransferAgent")),
            "stockAgentPhone": clean(r.get("StockTransferAgentTelephone")),
            "accountingFirm": clean(r.get("AccountingFirm")),
            "cpa1":         clean(r.get("CPA.CharteredPublicAccountant.First")),
            "cpa2":         clean(r.get("CPA.CharteredPublicAccountant.Second")),
            "reportType":   clean(r.get("PreparationOfFinancialReportType")),
            "symbol":       clean(r.get("Symbol"))
        }
    return out


def main():
    print(f"[{datetime.now():%H:%M:%S}] 抓興櫃公司基本資料")
    try:
        raw = fetch()
    except (URLError, HTTPError) as e:
        print(f"❌ {e}")
        sys.exit(1)

    print(f"原始筆數: {len(raw)}")
    companies = transform(raw)
    print(f"有效公司: {len(companies)}")

    payload = {
        "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source": "TPEx OpenAPI mopsfin_t187ap03_O",
        "count": len(companies),
        "companies": companies
    }

    out = DATA_DIR / "companies_live.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"✅ 已輸出: {out.relative_to(ROOT)}")

    # 顯示 3 個範例
    print("\n--- 範例 ---")
    for i, (code, c) in enumerate(companies.items()):
        if i >= 3:
            break
        print(f"  {code} {c['name']}")
        print(f"    董事長: {c['chairman']}  總經理: {c['president']}")
        print(f"    資本: {c['capital']}  成立: {c['founded']}")
        print(f"    地址: {c['address'][:30]}...")
        print(f"    網站: {c['website']}")


if __name__ == "__main__":
    main()
