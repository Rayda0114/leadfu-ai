#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_etf_holdings.py — ETF 成分股（官方源：各發行投信每日 PCF API）

ETF 成分股無單一官方總表，法定公告人為「發行投信」。本腳本逐投信串接其 PCF。
依 stocks_live.json 的 ETF「名稱前綴」路由到對應投信 adapter：
  元大→yuanta、國泰→cathay、富邦→fubon、復華→fuhhwa、群益→capital、中信→ctbc
（端點規格由逆向各投信官網 PCF 頁取得；皆為官方公告資料）

輸出 etf_holdings_live.json：{code:{asof, top:[{code,name,weight}], count}}
注意：投信 API 可能擋國外機房 IP；GitHub Actions 抓不到時維持前次快照。
"""
import json
import re
import io
import time
import zipfile
import datetime
import ssl
import urllib.request
import urllib.parse
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
OUT = DATA_DIR / "etf_holdings_live.json"
TOP_N = 15
SLEEP = 0.25
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


def get_json(url, **kw):
    return json.loads(_open(url, **kw).decode("utf-8", "ignore"))


def topn(holds):
    holds = [h for h in holds if h.get("name")]
    holds.sort(key=lambda x: -(x.get("weight") or 0))
    return holds


def _wf(v):
    """權重轉數值（容許字串「37.29」「37.29%」）。"""
    try:
        return round(float(str(v).replace("%", "").replace(",", "").strip()), 2)
    except (ValueError, TypeError):
        return None


# ───────────────────────── 元大投信 ─────────────────────────
def yuanta(code, ctx):
    d = get_json("https://etfapi.yuantaetfs.com/ectranslation/api/bridge?APIType=ETFAPI"
                 "&CompanyName=YUANTAFUNDS&FuncId=PCF/Daily&AppName=ETF&Device=3&Platform=ETF"
                 f"&ticker={code}&date={ctx['ymd']}&DeviceId=leadfu-ai")
    sw = ((d.get("FundWeights") or {}).get("StockWeights")) or []
    return topn([{"code": (x.get("code") or "").strip(), "name": (x.get("name") or "").strip(),
                  "weight": round(x["weights"], 2) if isinstance(x.get("weights"), (int, float)) else None} for x in sw])


# ───────────────────────── 國泰投信 ─────────────────────────
def _cathay_map(ctx):
    if "cathay" in ctx:
        return ctx["cathay"]
    m = {}
    for pg in range(1, 5):
        try:
            d = get_json(f"https://cwapi.cathaysite.com.tw/api/ETF/GetETFList?currentPage={pg}",
                         headers={"Referer": "https://www.cathaysite.com.tw/ETF/purchase"})
            for x in (d.get("result") or []):
                sc, fc = (x.get("stockCode") or "").strip(), (x.get("fundCode") or "").strip()
                if sc and fc:
                    m[sc] = fc
        except Exception:
            pass
        time.sleep(SLEEP)
    ctx["cathay"] = m
    return m


def cathay(code, ctx):
    fc = _cathay_map(ctx).get(code)
    if not fc:
        return []
    d = get_json(f"https://cwapi.cathaysite.com.tw/api/BuySale/GetStocksList?FundCode={fc}&SearchDate={ctx['slash']}&IsTest=false",
                 headers={"Referer": "https://www.cathaysite.com.tw/ETF/purchase"})
    rows = d.get("result") or []
    px = ctx["px"]
    # 國泰只給每籃股數，無權重% → 用「股數×現價」估算權重
    items = []
    for x in rows:
        t = (x.get("prod") or "").strip()
        sh = float(str(x.get("basketShares") or "0").replace(",", "") or 0)
        items.append({"code": t, "name": (x.get("prodName") or "").strip(), "mv": sh * (px.get(t) or 0)})
    tot = sum(i["mv"] for i in items) or 1
    return topn([{"code": i["code"], "name": i["name"], "weight": round(i["mv"] / tot * 100, 2)} for i in items])


# ───────────────────────── 富邦投信（HTML） ─────────────────────────
def fubon(code, ctx):
    html = _open(f"https://websys.fsit.com.tw/FubonETF/Fund/Assets.aspx?stkId={code}",
                 headers={"Referer": "https://websys.fsit.com.tw/FubonETF/"}).decode("utf-8", "ignore")
    cells = re.findall(r"<td[^>]*>(.*?)</td>", html, re.S)
    cells = [re.sub(r"<[^>]+>", "", c).replace("&nbsp;", " ").strip() for c in cells]
    # 找表頭「股票代碼」，其後每 5 欄一筆：代號/名稱/股數/金額/權重%
    out = []
    for i, c in enumerate(cells):
        if "股票代碼" in c:
            j = i + 5   # 跳過 5 欄表頭（股票代碼/股票名稱/股數/金額/權重%）
            while j + 4 < len(cells):
                t = cells[j]
                if not re.match(r"^\d{4,6}[A-Z]?$", t):   # 代號欄不再是代號 → 表格結束
                    break
                w = cells[j + 4].replace("%", "").replace(",", "")
                out.append({"code": t, "name": cells[j + 1],
                            "weight": round(float(w), 2) if re.match(r"^\d+(\.\d+)?$", w) else None})
                j += 5
            break
    return topn(out)


# ───────────────────────── 復華投信（XLSX） ─────────────────────────
# 復華 ticker→內部碼（由官網 etf_list 取得；變動極少，直接內建）
_FUHHWA_MAP = {
    "00929": "ETF21", "00731": "ETF08", "00712": "ETF07", "006207": "ETF01", "00877": "ETF19",
    "00924": "ETF20", "00949": "ETF22", "00991A": "ETF23", "00998A": "ETF24", "00986D": "ETF25",
    "00789B": "ETF16", "00791B": "ETF18", "00768B": "ETF14", "00758B": "ETF10", "00759B": "ETF11",
    "00760B": "ETF12", "00710B": "ETF05", "00711B": "ETF06", "00650L": "ETF03", "00651R": "ETF04",
}
def _fuhhwa_map(ctx):
    return _FUHHWA_MAP


def fuhhwa(code, ctx):
    intc = _fuhhwa_map(ctx).get(code)
    if not intc:
        return []
    for ymd in ctx["ymd_try"]:
        try:
            raw = _open(f"https://www.fhtrust.com.tw/api/assetsExcel/{intc}/{ymd}",
                        headers={"Referer": "https://www.fhtrust.com.tw/ETF/etf_list"})
            if raw[:2] != b"PK":   # 不是 xlsx（查無資料回 JSON）→ 換日期
                continue
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                xml = z.read("xl/sharedStrings.xml").decode("utf-8", "ignore")
            strs = re.findall(r"<(?:t|x:t)[^>]*>(.*?)</(?:t|x:t)>", xml, re.S)
            # 找表頭「權重(%)」位置，其後每 5 個字串一筆：代號/名稱/股數/金額/權重
            hi = next((k for k, s in enumerate(strs) if "權重" in s), -1)
            if hi < 0:
                continue
            out = []
            k = hi + 1
            while k + 4 < len(strs):
                t = strs[k].strip()
                if not re.match(r"^\d{4,6}[A-Z]?$", t):
                    break
                w = strs[k + 4].replace("%", "").strip()
                out.append({"code": t, "name": strs[k + 1].strip(),
                            "weight": round(float(w), 2) if re.match(r"^\d+(\.\d+)?$", w) else None})
                k += 5
            if out:
                return topn(out)
        except Exception:
            continue
    return []


# ───────────────────────── 群益投信 ─────────────────────────
def _capital_map(ctx):
    if "capital" in ctx:
        return ctx["capital"]
    m = {}
    try:
        d = get_json("https://www.capitalfund.com.tw/CFWeb/api/etf/items",
                     data=b"", headers={"Content-Type": "application/x-www-form-urlencoded"})
        for x in (d.get("data") or d.get("result") or []):
            sc, fn = (x.get("stockNo") or "").strip(), str(x.get("fundNo") or "").strip()
            if sc and fn:
                m[sc] = fn
    except Exception:
        pass
    ctx["capital"] = m
    return m


def capital(code, ctx):
    fn = _capital_map(ctx).get(code)
    if not fn:
        return []
    body = urllib.parse.urlencode({"fundId": fn, "date": "null"}).encode()
    d = get_json("https://www.capitalfund.com.tw/CFWeb/api/etf/buyback",
                 data=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
    stocks = ((d.get("data") or {}).get("stocks")) or []
    return topn([{"code": (x.get("stocNo") or "").strip(), "name": (x.get("stocName") or "").strip(),
                  "weight": x.get("weightRound") if isinstance(x.get("weightRound"), (int, float)) else None} for x in stocks])


# ───────────────────────── 中信投信（token + FID） ─────────────────────────
def _ctbc_map(ctx):
    if "ctbc" in ctx:
        return ctx["ctbc"]
    m = {}
    try:
        d = get_json("https://www.ctbcinvestments.com.tw/API/etf/ETFList?token=www.ctbcinvestments.com",
                     data=b"{}", headers={"Content-Type": "application/json",
                                          "Referer": "https://www.ctbcinvestments.com.tw/Etf/Buyback"})
        for x in ((d.get("Data") or {}).get("Data") or []):
            tk, fid = (str(x.get("ETF_ID") or "")).strip(), (x.get("FID") or "").strip()
            if tk and fid:
                m[tk] = fid
    except Exception:
        pass
    ctx["ctbc"] = m
    return m


def _ctbc_token(ctx):
    if "ctbc_tok" in ctx:
        return ctx["ctbc_tok"]
    tok = ""
    try:
        d = get_json("https://www.ctbcinvestments.com.tw/API/home/AuthToken?token=www.ctbcinvestments.com",
                     data=b'{"token":"www.ctbcinvestments.com"}',
                     headers={"Content-Type": "application/json", "Referer": "https://www.ctbcinvestments.com.tw/Etf/Buyback"})
        tok = ((d.get("Data") or {}).get("token")) or ""
    except Exception:
        pass
    ctx["ctbc_tok"] = tok
    return tok


def ctbc(code, ctx):
    fid = _ctbc_map(ctx).get(code)
    tok = _ctbc_token(ctx)
    if not fid or not tok:
        return []
    body = json.dumps({"token": tok, "FID": fid, "StartDate": ctx["dash"]}).encode()
    d = get_json(f"https://www.ctbcinvestments.com.tw/API/etf/Buyback?token={urllib.parse.quote(tok)}",
                 data=body, headers={"Content-Type": "application/json",
                                     "Referer": "https://www.ctbcinvestments.com.tw/Etf/Buyback"})
    detail = ((d.get("Data") or {}).get("Detail")) or []
    stock_block = next((b for b in detail if b.get("Code") == "STOCK"), None)
    rows = (stock_block or {}).get("Data") or []
    return topn([{"code": (str(x.get("code_") or "")).strip(), "name": (x.get("name_") or "").strip(),
                  "weight": _wf(x.get("weights_"))} for x in rows])


ADAPTERS = [("元大", yuanta), ("國泰", cathay), ("富邦", fubon),
            ("復華", fuhhwa), ("群益", capital), ("中信", ctbc)]


def main():
    stocks = json.loads((DATA_DIR / "stocks_live.json").read_text(encoding="utf-8")).get("stocks", [])
    etfs = [s for s in stocks if s.get("category") == "ETF"]
    px = {s["code"]: s.get("price") for s in stocks if s.get("code")}

    # 交易日：元大 0050 試 today..-6
    today = datetime.date.today()
    base = None
    for back in range(0, 7):
        dt = today - datetime.timedelta(days=back)
        try:
            if yuanta("0050", {"ymd": dt.strftime("%Y%m%d")}):
                base = dt
                break
        except Exception:
            pass
        time.sleep(SLEEP)
    if not base:
        print("[error] 找不到有效 PCF 交易日（投信 API 可能擋 IP/休市），維持前次資料")
        return

    ctx = {"ymd": base.strftime("%Y%m%d"), "slash": base.strftime("%Y/%m/%d"),
           "dash": base.strftime("%Y-%m-%d"), "px": px,
           "ymd_try": [(base - datetime.timedelta(days=k)).strftime("%Y%m%d") for k in range(0, 4)]}
    print(f"[info] PCF 基準日 {ctx['slash']}；ETF {len(etfs)} 檔")

    prev = {}
    if OUT.exists():
        try:
            prev = json.loads(OUT.read_text(encoding="utf-8")).get("data", {})
        except Exception:
            prev = {}

    data = dict(prev)
    by = {}
    for s in etfs:
        code, name = s.get("code"), s.get("name", "")
        fn = next((f for pre, f in ADAPTERS if name.startswith(pre)), None)
        if not fn:
            continue
        try:
            hold = fn(code, ctx)
            if hold:
                data[code] = {"asof": ctx["dash"], "top": hold[:TOP_N], "count": len(hold)}
                by[fn.__name__] = by.get(fn.__name__, 0) + 1
        except Exception as e:
            print(f"  [warn] {code} {name}: {str(e)[:80]}")
        time.sleep(SLEEP)

    OUT.write_text(json.dumps({"updatedAt": today.isoformat(), "asof": ctx["dash"],
                               "source": "各發行投信每日 PCF（元大/國泰/富邦/復華/群益/中信）",
                               "count": len(data), "data": data}, ensure_ascii=False), encoding="utf-8")
    print(f"✅ ETF 成分股：本次更新 {by}，累積 {len(data)} 檔 → etf_holdings_live.json")


if __name__ == "__main__":
    main()
