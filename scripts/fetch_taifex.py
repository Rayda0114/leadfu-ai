#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_taifex.py — 大盤風險溫度計（官方源：台灣期交所 TAIFEX OpenAPI）

定位：股票投資人的「大盤波動風險雷達」，不是期貨交易工具。
  只做「風險提醒」，不給買賣點、不喊單、不寫多空訊號。

抓：
  1. 台指期(TX) 日盤(一般) + 夜盤(盤後) 收盤與漲跌 — DailyMarketReportFut
  2. 選擇權 Put/Call Ratio（未平倉比，避險情緒）— PutCallRatio
  3. 結算日（每月第三個週三，程式計算）
→ 算出「明日大盤波動風險：低/中/高」（透明規則式，附判讀理由）
輸出 taifex_live.json
"""
import json
import datetime
import ssl
import urllib.request
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
OUT = DATA_DIR / "taifex_live.json"
_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE


def gj(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (LeadFu-AI)", "Accept": "application/json"})
    try:
        return json.loads(urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "ignore"))
    except Exception:
        return json.loads(urllib.request.urlopen(req, timeout=25, context=_CTX).read().decode("utf-8", "ignore"))


def fnum(v):
    try:
        return float(str(v).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


def pct_from(last, change):
    """漲跌幅% = change ÷ 前一基準價（last - change）。"""
    if last is None or change is None:
        return None
    base = last - change
    return round(change / base * 100, 2) if base else None


def fetch_inst(asof_ymd):
    """三大法人 臺股期貨 多空淨額未平倉口數（外資/投信/自營）— TAIFEX CSV（Big5）。
    asof_ymd: 期貨資料的交易日 'YYYYMMDD'，用單日查詢（區間查詢跨非交易日會回 HTML 錯誤頁）。"""
    if not asof_ymd or len(asof_ymd) != 8 or not asof_ymd.isdigit():
        return None
    d = f"{asof_ymd[:4]}/{asof_ymd[4:6]}/{asof_ymd[6:]}"
    body = f"queryStartDate={d}&queryEndDate={d}&commodityId=".encode()
    req = urllib.request.Request("https://www.taifex.com.tw/cht/3/futContractsDateDown", data=body,
                                 headers={"User-Agent": "Mozilla/5.0 (LeadFu-AI)", "Content-Type": "application/x-www-form-urlencoded"}, method="POST")
    try:
        raw = urllib.request.urlopen(req, timeout=25).read()
    except Exception:
        raw = urllib.request.urlopen(req, timeout=25, context=_CTX).read()
    rows = [l.split(",") for l in raw.decode("big5", "ignore").split("\n") if l.strip()]
    tx = [r for r in rows[1:] if len(r) >= 14 and "臺股期貨" in r[1]]
    if not tx:
        return None
    latest = max(r[0] for r in tx)
    out = {"date": latest.replace("/", "-")}
    for r in tx:
        if r[0] != latest:
            continue
        net = fnum(r[13])
        if "外資" in r[2]:
            out["foreign"] = net
        elif "投信" in r[2]:
            out["trust"] = net
        elif "自營" in r[2]:
            out["dealer"] = net
    return out


def fetch_taiex():
    """加權指數(TAIEX)收盤 — TWSE FMTQIK；用來算期現背離(基差=台指期-加權)。"""
    try:
        d = gj("https://openapi.twse.com.tw/v1/exchangeReport/FMTQIK")
        if d:
            return fnum(d[-1].get("TAIEX")), d[-1].get("Date")
    except Exception:
        pass
    return None, None


def fetch_large_trader(asof_ymd):
    """大額交易人 臺股期貨 前十大淨部位（所有契約合計、口數）— TAIFEX CSV(Big5)。
    到期月份代碼：999999=所有契約合計(口數)、202606=近月、666666=百分比列(不取)；交易人類別 0=所有交易人。"""
    if not asof_ymd or len(asof_ymd) != 8 or not asof_ymd.isdigit():
        return None
    d = f"{asof_ymd[:4]}/{asof_ymd[4:6]}/{asof_ymd[6:]}"
    body = f"queryStartDate={d}&queryEndDate={d}".encode()
    req = urllib.request.Request("https://www.taifex.com.tw/cht/3/largeTraderFutDown", data=body,
                                 headers={"User-Agent": "Mozilla/5.0 (LeadFu-AI)", "Content-Type": "application/x-www-form-urlencoded"}, method="POST")
    try:
        raw = urllib.request.urlopen(req, timeout=25).read()
    except Exception:
        raw = urllib.request.urlopen(req, timeout=25, context=_CTX).read()
    for l in raw.decode("big5", "ignore").split("\n"):
        c = l.split(",")
        if len(c) >= 10 and c[1].strip() == "TX" and c[3].strip() == "999999" and c[4].strip() == "0":
            buy10, sell10, oi = fnum(c[7]), fnum(c[8]), fnum(c[9])
            if buy10 is not None and sell10 is not None:
                net = round(buy10 - sell10)
                return {"top10Net": net, "oi": int(oi) if oi else None,
                        "netPct": round(net / oi * 100, 1) if oi else None}
    return None


def third_wednesday(year, month):
    d = datetime.date(year, month, 1)
    # 第一個週三
    first_wed = 1 + (2 - d.weekday()) % 7
    return datetime.date(year, month, first_wed + 14)


def next_settlement(today):
    s = third_wednesday(today.year, today.month)
    if s < today:
        ny, nm = (today.year + (1 if today.month == 12 else 0), 1 if today.month == 12 else today.month + 1)
        s = third_wednesday(ny, nm)
    return s


def main():
    today = datetime.date.today()

    # ── 1. 台指期 日盤/夜盤（futDataDown：盤後當天即發布；OpenAPI 落後 1-2 天故棄用為主源）──
    tx_day, tx_night, asof = None, None, ""

    def _fut_csv(d):
        """期交所每日行情下載（Big5 CSV），含一般+盤後。回 list[dict-like row list]。"""
        import urllib.parse as _up
        body = _up.urlencode({"down_type": "1", "commodity_id": "TX",
                              "queryStartDate": d.strftime("%Y/%m/%d"),
                              "queryEndDate": d.strftime("%Y/%m/%d")}).encode()
        req = urllib.request.Request("https://www.taifex.com.tw/cht/3/futDataDown", data=body,
                                     headers={"User-Agent": "Mozilla/5.0 (LeadFu-AI)"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                raw = r.read()
        except (urllib.error.URLError, ssl.SSLError):
            with urllib.request.urlopen(req, timeout=30, context=_CTX) as r:
                raw = r.read()
        text = raw.decode("big5", "ignore")
        rows = [ln.split(",") for ln in text.splitlines()[1:] if ln.strip()]
        return [r for r in rows if len(r) >= 18 and r[1].strip() == "TX"]

    try:
        rows = []
        for back in range(0, 5):   # 今天起往回找最近一個有資料的交易日
            d = today - datetime.timedelta(days=back)
            rows = _fut_csv(d)
            if rows:
                break
        if rows:
            sess = lambda r: r[17].strip()
            gen = [r for r in rows if sess(r) == "一般"]
            gen.sort(key=lambda r: -(fnum(r[9]) or 0))   # 近月 = 一般時段量最大
            if gen:
                fr = gen[0]
                cm = fr[2].strip()
                asof = fr[0].strip().replace("/", "-")
                d_last, d_chg = fnum(fr[6]), fnum(fr[7])
                d_hi, d_lo = fnum(fr[4]), fnum(fr[5])
                rng = round((d_hi - d_lo) / d_last * 100, 2) if (d_hi and d_lo and d_last) else None
                tx_day = {"last": d_last, "change": d_chg, "pct": pct_from(d_last, d_chg), "rangePct": rng, "month": cm}
                night = next((r for r in rows if sess(r) == "盤後" and r[2].strip() == cm), None)
                if night:
                    n_last = fnum(night[6])
                    ov = round((n_last - d_last) / d_last * 100, 2) if (n_last and d_last) else None
                    tx_night = {"last": n_last, "change": fnum(night[7]), "pct": ov, "month": cm,
                                "vsLabel": "較日盤收盤"}
    except Exception as e:
        print(f"[warn] 台指期(futDataDown): {e}")

    # 後備：OpenAPI（可能落後 1-2 天）
    if tx_day is None:
        try:
            fut = gj("https://openapi.taifex.com.tw/v1/DailyMarketReportFut")
            tx = [r for r in fut if r.get("Contract") == "TX"]
            gen = [r for r in tx if r.get("TradingSession") == "一般"]
            gen.sort(key=lambda r: -(fnum(r.get("Volume")) or 0))
            if gen:
                front = gen[0]
                cm = front.get("ContractMonth(Week)")
                asof = front.get("Date", "")
                d_last, d_chg = fnum(front.get("Last")), fnum(front.get("Change"))
                d_hi, d_lo = fnum(front.get("High")), fnum(front.get("Low"))
                rng = round((d_hi - d_lo) / d_last * 100, 2) if (d_hi and d_lo and d_last) else None
                tx_day = {"last": d_last, "change": d_chg, "pct": pct_from(d_last, d_chg), "rangePct": rng, "month": cm}
                night = next((r for r in tx if r.get("TradingSession") == "盤後" and r.get("ContractMonth(Week)") == cm), None)
                if night:
                    n_last = fnum(night.get("Last"))
                    ov = round((n_last - d_last) / d_last * 100, 2) if (n_last and d_last) else None
                    tx_night = {"last": n_last, "change": fnum(night.get("Change")), "pct": ov, "month": cm,
                                "vsLabel": "較日盤收盤"}
        except Exception as e:
            print(f"[warn] 台指期(OpenAPI 後備): {e}")

    # ── 2. Put/Call Ratio（取最新一筆） ──
    pc = None
    try:
        pcr = gj("https://openapi.taifex.com.tw/v1/PutCallRatio")
        pcr.sort(key=lambda r: r.get("Date", ""), reverse=True)
        if pcr:
            top = pcr[0]
            pc = {"date": top.get("Date"), "oiRatio": fnum(top.get("PutCallOIRatio%")), "volRatio": fnum(top.get("PutCallVolumeRatio%"))}
    except Exception as e:
        print(f"[warn] P/C: {e}")

    # ── 2.5 三大法人期貨多空（外資台指期淨部位） ──
    inst = None
    try:
        inst = fetch_inst(asof)
    except Exception as e:
        print(f"[warn] 三大法人: {e}")

    # ── 2.6 期現背離（基差 = 台指期日盤 − 加權指數） ──
    taiex, basis = None, None
    try:
        taiex, _ = fetch_taiex()
        if taiex and tx_day and tx_day.get("last"):
            basis = round(tx_day["last"] - taiex)
    except Exception as e:
        print(f"[warn] 加權指數: {e}")

    # ── 2.7 大額交易人（前十大淨部位，所有契約合計） ──
    lt = None
    try:
        lt = fetch_large_trader(asof)
    except Exception as e:
        print(f"[warn] 大額交易人: {e}")

    # ── 3. 結算日 ──
    settle = next_settlement(today)
    days_to_settle = (settle - today).days

    # ── 4. 風險溫度（透明規則式） ──
    pts, reasons = 0, []
    np_ = tx_night["pct"] if tx_night else None
    if np_ is not None:
        if np_ <= -1.5:
            pts += 3; reasons.append(f"台指期夜盤大跌 {np_:.2f}%")
        elif np_ <= -0.7:
            pts += 2; reasons.append(f"台指期夜盤下跌 {np_:.2f}%")
        elif np_ <= -0.2:
            pts += 1; reasons.append(f"台指期夜盤小跌 {np_:.2f}%")
        elif np_ >= 0.7:
            pts -= 1; reasons.append(f"台指期夜盤上漲 {np_:.2f}%（風險偏低）")
    dp_ = tx_day["pct"] if tx_day else None
    if dp_ is not None and dp_ <= -1.5:
        pts += 1; reasons.append(f"今日大盤重挫 {dp_:.2f}%")
    if pc and pc.get("oiRatio") is not None:
        if pc["oiRatio"] >= 130:
            pts += 1; reasons.append(f"選擇權 Put/Call 未平倉比偏高（{pc['oiRatio']:.0f}%，避險升溫）")
        elif pc["oiRatio"] <= 70:
            pts += 1; reasons.append(f"選擇權 Put/Call 未平倉比偏低（{pc['oiRatio']:.0f}%，多頭過熱）")
    if inst and inst.get("foreign") is not None and inst["foreign"] <= -50000:
        pts += 1; reasons.append(f"外資台指期淨空 {abs(int(inst['foreign'])):,} 口（法人偏空）")
    elif inst and inst.get("foreign") is not None and inst["foreign"] >= 30000:
        pts -= 1; reasons.append(f"外資台指期淨多 {int(inst['foreign']):,} 口（法人偏多，風險偏低）")
    if basis is not None and basis <= -150:
        pts += 1; reasons.append(f"台指期逆價差 {basis} 點（期貨大幅貼水，偏空）")
    if tx_day and tx_day.get("rangePct") is not None and tx_day["rangePct"] >= 3.0:
        pts += 1; reasons.append(f"台指期今日振幅 {tx_day['rangePct']:.1f}%（波動明顯加大）")
    if lt and lt.get("netPct") is not None:
        if lt["netPct"] <= -15:
            pts += 1; reasons.append(f"大額交易人前十大淨空 {abs(lt['top10Net']):,} 口（佔OI {abs(lt['netPct'])}%，偏空）")
        elif lt["netPct"] >= 15:
            pts -= 1; reasons.append(f"大額交易人前十大淨多 {lt['top10Net']:,} 口（佔OI {lt['netPct']}%，偏多）")
    if days_to_settle <= 3:
        pts += 1; reasons.append(f"距結算日僅 {days_to_settle} 天，波動易放大")

    level = "高" if pts >= 4 else ("中" if pts >= 2 else "低")
    if not reasons:
        reasons.append("各項期貨指標平穩，無明顯系統性風險訊號")

    out = {
        "updatedAt": today.isoformat(),
        "asof": f"{asof[:4]}-{asof[4:6]}-{asof[6:]}" if len(asof) == 8 else asof,
        "txDay": tx_day, "txNight": tx_night, "putCall": pc, "inst": inst,
        "taiex": taiex, "basis": basis, "largeTrader": lt,
        "settlementDate": settle.isoformat(), "daysToSettle": days_to_settle,
        "risk": {"level": level, "points": pts, "reasons": reasons},
        "source": "台灣期貨交易所 TAIFEX OpenAPI",
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"✅ 大盤風險溫度計：日盤 {dp_}% 夜盤 {np_}% P/C(OI) {pc['oiRatio'] if pc else '—'} → 風險【{level}】({pts}分)")
    print(f"   理由：{reasons}")
    print(f"   結算日 {settle}（{days_to_settle} 天後）")


if __name__ == "__main__":
    main()
