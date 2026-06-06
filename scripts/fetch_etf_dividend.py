#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_etf_dividend.py — ETF 配息歷史（官方源：各發行投信配息/收益分配 API）

逐投信抓 ETF 歷年配息（除息日 + 每受益權單位現金分配），算近一年合計(ttmCash)→ 真實殖利率。
依 stocks_live 的 ETF 名稱前綴路由：元大/國泰/富邦/復華/群益/中信。
輸出 etf_div_live.json：{code:{name,lastCash,lastExDate,ttmCash,firstDate,distCount}}
（沿用既有欄位，前端 etf.html / etf-compare / stock-detail 的殖利率直接吃。）

注意：投信 API 可能擋國外機房 IP；GitHub Actions 抓不到時維持前次快照。
"""
import json
import re
import time
import datetime
import ssl
import urllib.request
import urllib.parse
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
OUT = DATA_DIR / "etf_div_live.json"
SLEEP = 0.25
TODAY = datetime.date.today()
TTM_CUT = (TODAY - datetime.timedelta(days=365)).isoformat()
_YT_UID = "6f1a2b3c-4d5e-6789-abcd-ef0123456789"   # 元大 API 需 UUID 格式 DeviceId
_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE


def _open(url, data=None, headers=None, timeout=25):
    h = {"User-Agent": "Mozilla/5.0 (LeadFu-AI)", "Accept": "*/*"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h, method=("POST" if data is not None else "GET"))
    try:
        return urllib.request.urlopen(req, timeout=timeout).read()
    except Exception:
        return urllib.request.urlopen(req, timeout=timeout, context=_CTX).read()


def gj(url, **kw):
    return json.loads(_open(url, **kw).decode("utf-8", "ignore"))


def nd(s):
    """日期正規化 → YYYY-MM-DD。"""
    s = str(s or "").strip().replace(".", "/")
    m = re.search(r"(20\d{2})[/-](\d{1,2})[/-](\d{1,2})", s)
    return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}" if m else ""


def num(v):
    try:
        return float(str(v).replace(",", "").replace("%", "").strip())
    except (ValueError, TypeError):
        return None


# ───────── 元大 ─────────
def _yuanta_map(ctx):
    if "y" in ctx:
        return ctx["y"]
    m = {}
    try:
        d = gj("https://api.yuantafunds.com/ectranslation/api/trans?APIType=EC2API&AppName=FundWeb"
               f"&PageName=%2Ffund&Device=4&DeviceId={_YT_UID}&FuncId=FundList&FundType=ETF",
               headers={"Referer": "https://www.yuantafunds.com/"})
        for x in ((d.get("Data") or {}).get("FUND") or []):   # 清單在 Data.FUND
            sc, fid = str(x.get("STK_CD") or "").strip(), str(x.get("FUND_ID") or "").strip()
            if sc and fid:
                m[sc] = fid
    except Exception:
        pass
    ctx["y"] = m
    return m


def yuanta(code, ctx):
    fid = _yuanta_map(ctx).get(code)
    if not fid:
        return []
    # DeviceId 必須是 UUID 格式，否則回 Bad Request
    d = gj("https://api.yuantafunds.com/ectranslation/api/trans?APIType=EC2API&AppName=FundWeb"
           f"&PageName=%2Fmyfund%2Fdividend%2Fhistory&Device=4&DeviceId={_YT_UID}&FuncId=FundDividend"
           f"&SDate=20180101&EDate={TODAY:%Y%m%d}&FundId={fid}&FundType=ETF",
           headers={"Referer": "https://www.yuantafunds.com/"})
    rows = ((d.get("Data") or {}).get("Data")) or []
    return [(nd(x.get("SHARE_DATE")), num(x.get("DIVIDEN_PER_UNIT"))) for x in rows]


# ───────── 國泰（沿用 GetETFList 對照） ─────────
def _cathay_map(ctx):
    if "c" in ctx:
        return ctx["c"]
    m = {}
    for pg in range(1, 5):
        try:
            d = gj(f"https://cwapi.cathaysite.com.tw/api/ETF/GetETFList?currentPage={pg}",
                   headers={"Referer": "https://www.cathaysite.com.tw/"})
            for x in (d.get("result") or []):
                sc, fc = (x.get("stockCode") or "").strip(), (x.get("fundCode") or "").strip()
                if sc and fc:
                    m[sc] = fc
        except Exception:
            pass
        time.sleep(SLEEP)
    ctx["c"] = m
    return m


def cathay(code, ctx):
    fc = _cathay_map(ctx).get(code)
    if not fc:
        return []
    out = []
    for pg in range(1, 4):   # 近 3 頁（30 筆）涵蓋 TTM + 判齡
        try:
            d = gj(f"https://cwapi.cathaysite.com.tw/api/Fund/GetHistoryAllotInfo?fundCode={fc}&CurrentPage={pg}&PerPageCount=10",
                   headers={"Referer": "https://www.cathaysite.com.tw/"})
            lst = ((d.get("result") or {}).get("fundAllotInfoList")) or []
            if not lst:
                break
            for x in lst:
                out.append((nd(x.get("transDate")), num(x.get("allotMoney"))))
            if pg >= (d.get("totalPage") or 1):
                break
        except Exception:
            break
        time.sleep(SLEEP)
    return out


# ───────── 富邦（HTML） ─────────
def fubon(code, ctx):
    html = _open(f"https://websys.fsit.com.tw/FubonETF/Dividend/Detail.aspx?stkId={code}&sdate=2015/01/01&edate={TODAY:%Y/%m/%d}",
                 headers={"Referer": "https://websys.fsit.com.tw/FubonETF/Dividend/Dividend.aspx"}).decode("utf-8", "ignore")
    cells = [re.sub(r"<[^>]+>", "", c).replace("&nbsp;", " ").strip()
             for c in re.findall(r"<td[^>]*>(.*?)</td>", html, re.S)]
    out, i = [], 0
    while i + 6 < len(cells):
        if re.match(r"^20\d\d/\d\d$", cells[i]):   # 配息年月 → 一列 7 欄
            out.append((nd(cells[i + 5]), num(cells[i + 1])))   # [5]除息日 [1]每單位金額
            i += 7
        else:
            i += 1
    return out


# ───────── 復華 ─────────
def _fuhhwa_map(ctx):
    if "f" in ctx:
        return ctx["f"]
    m = {}
    try:
        d = gj("https://www.fhtrust.com.tw/api/fundList", headers={"Referer": "https://www.fhtrust.com.tw/"})
        for x in (d.get("result") or []):
            tk, fid = str(x.get("etf002") or "").strip(), str(x.get("fundID") or "").strip()
            if tk and fid:
                m[tk] = fid
    except Exception:
        pass
    ctx["f"] = m
    return m


def fuhhwa(code, ctx):
    fid = _fuhhwa_map(ctx).get(code)
    if not fid:
        return []
    sd = (TODAY - datetime.timedelta(days=730)).strftime("%Y/%m/%d")
    d = gj(f"https://www.fhtrust.com.tw/api/fundDividend?m=fund&fundID={fid}&sDate={sd}&eDate={TODAY:%Y/%m/%d}&dateType=divDate&ec001=3",
           headers={"Referer": "https://www.fhtrust.com.tw/"})
    res = d.get("result") or []
    divs = (res[0].get("dividend") if res else []) or []
    return [(nd(x.get("divDate")), num(x.get("mDiv"))) for x in divs]


# ───────── 群益（沿用 items 對照） ─────────
def _capital_map(ctx):
    if "g" in ctx:
        return ctx["g"]
    m = {}
    try:
        d = gj("https://www.capitalfund.com.tw/CFWeb/api/etf/items", data=b"",
               headers={"Content-Type": "application/x-www-form-urlencoded"})
        for x in (d.get("data") or d.get("result") or []):
            sc, fn = (x.get("stockNo") or "").strip(), str(x.get("fundNo") or "").strip()
            if sc and fn:
                m[sc] = fn
    except Exception:
        pass
    ctx["g"] = m
    return m


def capital(code, ctx):
    fn = _capital_map(ctx).get(code)
    if not fn:
        return []
    try:
        body = json.dumps({"searchType": 3, "interestCycle": "", "fundid": int(fn)}).encode()
    except ValueError:
        return []
    d = gj("https://www.capitalfund.com.tw/CFWeb/api/etf/dividendDataHistory",
           data=body, headers={"Content-Type": "application/json", "Referer": "https://www.capitalfund.com.tw/"})
    return [(nd(x.get("interestDate")), num(x.get("amt"))) for x in (d.get("data") or [])]


# ───────── 中信（token + CNO） ─────────
def _ctbc(ctx):
    if "t" in ctx:
        return ctx["t"], ctx["tm"]
    tok, m = "", {}
    try:
        d = gj("https://www.ctbcinvestments.com.tw/API/home/AuthToken?token=www.ctbcinvestments.com",
               data=b'{"token":"www.ctbcinvestments.com"}',
               headers={"Content-Type": "application/json", "Referer": "https://www.ctbcinvestments.com.tw/"})
        tok = ((d.get("Data") or {}).get("token")) or ""
    except Exception:
        pass
    try:
        d = gj("https://www.ctbcinvestments.com.tw/API/etf/ETFList?token=www.ctbcinvestments.com",
               data=b"{}", headers={"Content-Type": "application/json", "Referer": "https://www.ctbcinvestments.com.tw/"})
        for x in (((d.get("Data") or {}).get("Data")) or []):
            tk, cno = str(x.get("ETF_ID") or "").strip(), str(x.get("CNO") or "").strip()
            if tk and cno:
                m[tk] = cno
    except Exception:
        pass
    ctx["t"], ctx["tm"] = tok, m
    return tok, m


def ctbc(code, ctx):
    tok, m = _ctbc(ctx)
    cno = m.get(code)
    if not tok or not cno:
        return []
    body = json.dumps({"token": tok, "CNO": cno}).encode()
    d = gj(f"https://www.ctbcinvestments.com.tw/API/etf/ETFDetail?token={urllib.parse.quote(tok)}",
           data=body, headers={"Content-Type": "application/json", "Referer": "https://www.ctbcinvestments.com.tw/"})
    rows = ((d.get("Data") or {}).get("DivHist")) or []
    return [(nd(x.get("DIVIDENT_DATE")), num(x.get("UNIT_NET"))) for x in rows]


ADAPTERS = [("元大", yuanta), ("國泰", cathay), ("富邦", fubon),
            ("復華", fuhhwa), ("群益", capital), ("中信", ctbc)]


def main():
    stocks = json.loads((DATA_DIR / "stocks_live.json").read_text(encoding="utf-8")).get("stocks", [])
    etfs = [s for s in stocks if s.get("category") == "ETF"]
    ctx, out, by = {}, {}, {}
    for s in etfs:
        code, name = s.get("code"), s.get("name", "")
        fn = next((f for pre, f in ADAPTERS if name.startswith(pre)), None)
        if not fn:
            continue
        try:
            recs = [(d, c) for d, c in fn(code, ctx) if d and isinstance(c, (int, float)) and c > 0]
        except Exception as e:
            print(f"  [warn] {code} {name}: {str(e)[:70]}")
            recs = []
        if not recs:
            continue
        recs = sorted(set(recs))                # 去重 + 由舊到新
        last_d, last_c = recs[-1]
        ttm = sum(c for d, c in recs if d >= TTM_CUT)
        cnt = sum(1 for d, c in recs if d >= TTM_CUT)
        out[code] = {"name": name, "lastCash": round(last_c, 4), "lastExDate": last_d,
                     "ttmCash": round(ttm, 4), "firstDate": recs[0][0], "distCount": cnt}
        by[fn.__name__] = by.get(fn.__name__, 0) + 1
        time.sleep(SLEEP)

    if not out:
        print("[error] 配息：一檔都沒抓到（投信 API 可能擋 IP），維持前次資料")
        return
    OUT.write_text(json.dumps({"updatedAt": TODAY.isoformat(),
                               "source": "各發行投信配息/收益分配 API（元大/國泰/富邦/復華/群益/中信）",
                               "count": len(out), "data": out}, ensure_ascii=False), encoding="utf-8")
    print(f"✅ ETF 配息：{by}，共 {len(out)} 檔 → etf_div_live.json")


if __name__ == "__main__":
    main()
