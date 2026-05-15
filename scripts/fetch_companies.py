"""
領富 AI · 全市場公司基本資料抓取
資料來源：三個免費公開 OpenAPI（依市場分別抓）

端點：
  上市 TWSE: https://openapi.twse.com.tw/v1/opendata/t187ap03_L
  上櫃 TPEx: https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O
  興櫃 TPEx: https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_R

包含：董事長、總經理、發言人、地址、電話、Email、網站、
      實收資本額、成立日期、上市日期、簽證會計師、股票代理人...

產出：data/companies_live.json
  格式：{ "<code>": { name, chairman, market, ... }, ... }
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

URL_LISTED   = "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"           # 上市
URL_OTC      = "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O"         # 上櫃
URL_EMERGING = "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_R"         # 興櫃
UA = "LeadFu-AI/1.0 (+https://leadfuai.com)"

# 台股產業代碼對照表（TWSE/TPEx 通用 SecuritiesIndustryCode）
INDUSTRY_CODE_NAME = {
    "01": "水泥",       "02": "食品",       "03": "塑膠",       "04": "紡織",
    "05": "電機機械",   "06": "電器電纜",   "07": "化學",       "08": "玻璃陶瓷",
    "09": "造紙",       "10": "鋼鐵",       "11": "橡膠",       "12": "汽車",
    "13": "電子",       "14": "建材營造",   "15": "航運",       "16": "觀光餐旅",
    "17": "金融保險",   "18": "貿易百貨",   "19": "綜合",       "20": "其他",
    "21": "化學",       "22": "生技醫療",   "23": "油電燃氣",   "24": "半導體",
    "25": "電腦及周邊", "26": "光電",       "27": "通信網路",   "28": "電子零組件",
    "29": "電子通路",   "30": "資訊服務",   "31": "其他電子",   "32": "文化創意",
    "33": "農業科技",   "34": "電子商務",   "35": "綠能環保",   "36": "數位雲端",
    "37": "運動休閒",   "38": "居家生活",   "80": "管理股票",   "91": "存託憑證",
    "99": "ETF"
}

def industry_name(code):
    """產業代碼 → 中文名"""
    code = (code or "").strip().zfill(2)
    return INDUSTRY_CODE_NAME.get(code, "")

# TWSE 政府 API SSL 退而求其次 context（公開資料無敏感性）
_INSECURE_CTX = ssl.create_default_context()
_INSECURE_CTX.check_hostname = False
_INSECURE_CTX.verify_mode = ssl.CERT_NONE


def fetch_json(url, allow_insecure=False):
    """抓取 JSON，遇 SSL 憑證問題自動 fallback（公開政府 API）"""
    req = Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urlopen(req, timeout=45) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (URLError, ssl.SSLError) as e:
        if allow_insecure and ("CERTIFICATE" in str(e) or isinstance(e.__cause__, ssl.SSLError)):
            print(f"  ⚠ SSL 驗證失敗，改用 unverified context（{url}）")
            with urlopen(req, timeout=45, context=_INSECURE_CTX) as resp:
                return json.loads(resp.read().decode("utf-8"))
        raise


def parse_date(s):
    """支援西元 YYYYMMDD 與民國 YYYMMDD"""
    if not s:
        return ""
    s = str(s).strip()
    try:
        if len(s) == 8:
            return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
        if len(s) == 7:
            year = int(s[:3]) + 1911
            return f"{year}-{s[3:5]}-{s[5:7]}"
    except (ValueError, IndexError):
        pass
    return s if s else ""


def clean(v):
    if v is None:
        return ""
    s = str(v).strip()
    return "" if s in ("", "-", "─", "─") else s


def fmt_capital(s):
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


def map_tpex_record(r, market):
    """TPEx 格式（上櫃/興櫃共用）"""
    code = clean(r.get("SecuritiesCompanyCode"))
    if not code:
        return None
    return code, {
        "code":           code,
        "name":           clean(r.get("CompanyName")),
        "abbrev":         clean(r.get("CompanyAbbreviation")),
        "industry":       clean(r.get("SecuritiesIndustryCode")),
        "address":        clean(r.get("Address")),
        "taxId":          clean(r.get("UnifiedBusinessNo.")),
        "chairman":       clean(r.get("Chairman")),
        "president":      clean(r.get("GeneralManager")),
        "spokesman":      clean(r.get("Spokesman")),
        "spokesmanTitle": clean(r.get("TitleOfSpokesman")),
        "deputy":         clean(r.get("DeputySpokesperson")),
        "phone":          clean(r.get("Telephone")),
        "fax":            clean(r.get("Fax")),
        "email":          clean(r.get("EmailAddress")),
        "website":        clean(r.get("WebAddress")),
        "founded":        parse_date(r.get("DateOfIncorporation")),
        "listed":         parse_date(r.get("DateOfListing")),
        "parValue":       clean(r.get("ParValueOfCommonStock")),
        "capital":        fmt_capital(r.get("Paidin.Capital.NTDollars")),
        "issuedShares":   clean(r.get("IssueShares")),
        "stockAgent":     clean(r.get("StockTransferAgent")),
        "stockAgentPhone": clean(r.get("StockTransferAgentTelephone")),
        "accountingFirm": clean(r.get("AccountingFirm")),
        "cpa1":           clean(r.get("CPA.CharteredPublicAccountant.First")),
        "cpa2":           clean(r.get("CPA.CharteredPublicAccountant.Second")),
        "reportType":     clean(r.get("PreparationOfFinancialReportType")),
        "symbol":         clean(r.get("Symbol")),
        "market":         market
    }


def map_twse_record(r):
    """TWSE 上市格式（注意：實際欄位名跟想像不同，已對照 API 實際 response）"""
    code = clean(r.get("公司代號") or r.get("Code"))
    if not code:
        return None
    return code, {
        "code":           code,
        "name":           clean(r.get("公司名稱") or r.get("Name")),
        "abbrev":         clean(r.get("公司簡稱")),
        "industry":       clean(r.get("產業別") or r.get("產業類別")),    # 真實欄位是「產業別」
        "address":        clean(r.get("住址")),
        "taxId":          clean(r.get("營利事業統一編號")),
        "chairman":       clean(r.get("董事長")),
        "president":      clean(r.get("總經理")),
        "spokesman":      clean(r.get("發言人")),
        "spokesmanTitle": clean(r.get("發言人職稱")),
        "deputy":         clean(r.get("代理發言人")),
        "phone":          clean(r.get("總機電話")),
        "fax":            clean(r.get("傳真機號碼")),
        "email":          clean(r.get("電子郵件信箱")),
        "website":        clean(r.get("網址") or r.get("公司網址")),       # 真實欄位是「網址」
        "founded":        parse_date(r.get("成立日期")),
        "listed":         parse_date(r.get("上市日期")),
        "parValue":       clean(r.get("普通股每股面額")),
        "capital":        fmt_capital(r.get("實收資本額") or r.get("實收資本額(元)")),
        "issuedShares":   clean(r.get("已發行普通股數或TDR原股發行股數") or r.get("已發行普通股數或TDR原發行股數")),
        "stockAgent":     clean(r.get("股票過戶機構")),
        "stockAgentPhone": clean(r.get("過戶電話")),
        "accountingFirm": clean(r.get("簽證會計師事務所")),
        "cpa1":           clean(r.get("簽證會計師1")),
        "cpa2":           clean(r.get("簽證會計師2")),
        "reportType":     clean(r.get("編制財務報表類型") or r.get("編製財務報告類型")),
        "symbol":         clean(r.get("英文簡稱")),
        "market":         "listed"
    }


def fetch_market(name, url, mapper, allow_insecure=False):
    print(f"\n▶ 抓 {name}: {url}")
    try:
        raw = fetch_json(url, allow_insecure=allow_insecure)
    except Exception as e:
        print(f"  ❌ 失敗: {e}")
        return {}

    print(f"  原始筆數: {len(raw)}")
    out = {}
    for r in raw:
        result = mapper(r)
        if result:
            code, info = result
            # 把產業代碼轉成中文名（給前端 / merge_stocks 用）
            info["industryName"] = industry_name(info.get("industry"))
            out[code] = info
    print(f"  有效公司: {len(out)}")
    return out


def main():
    print("=" * 60)
    print(f"全市場公司基本資料抓取 ・ {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 60)

    listed   = fetch_market("上市 (TWSE)", URL_LISTED, map_twse_record, allow_insecure=True)
    otc      = fetch_market("上櫃 (TPEx)", URL_OTC,    lambda r: map_tpex_record(r, "otc"),      allow_insecure=True)
    emerging = fetch_market("興櫃 (TPEx)", URL_EMERGING, lambda r: map_tpex_record(r, "emerging"), allow_insecure=True)

    # 合併（同 code 衝突時優先級：上市 > 上櫃 > 興櫃）
    companies = {}
    companies.update(emerging)
    companies.update(otc)
    companies.update(listed)

    print(f"\n合併後總公司數: {len(companies)}")

    payload = {
        "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source": "TWSE + TPEx OpenAPI (t187ap03_L/_O/_R)",
        "count": len(companies),
        "marketBreakdown": {
            "listed":   len(listed),
            "otc":      len(otc),
            "emerging": len(emerging)
        },
        "companies": companies
    }

    out = DATA_DIR / "companies_live.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"✅ 已輸出: {out.relative_to(ROOT)} ({len(companies)} 家公司)")

    # 範例（每市場各印 1 家熱門股驗證）
    print("\n--- 範例 ---")
    for code in ("2330", "6488", "6775"):
        if code in companies:
            c = companies[code]
            print(f"  [{c['market']:<8}] {code} {c['name']}")
            print(f"    董事長: {c['chairman']}  總經理: {c['president']}")
            print(f"    資本額: {c['capital']}  成立: {c['founded']}  上市: {c['listed']}")
            print(f"    地址: {c['address'][:36]}")
            print(f"    網站: {c['website']}")


if __name__ == "__main__":
    main()
