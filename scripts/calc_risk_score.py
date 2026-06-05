#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
calc_risk_score.py — 領富 AI · 個股風險分數（防錯雷達升級）

把多項風險訊號加權成每檔 0-100 的「總風險分數」+ 等級 + 主要原因，
並保留每日歷史以判斷「最近 7 天風險是否升高」。

訊號（皆公開資料）：交易所注意/處置股、今日大跌、成交量爆量/萎縮、外資今日大賣、
月營收年減、本業虧損、跌破合理區間下緣、近期波動劇烈、流動性偏低、跌破月線、借券賣出增加。

輸入：data/ 下 stocks / attention / institutional / revenue / financials /
      fair_value / indicators / margin(+tpex) / sbl / klines
輸出：
  data/risk_score_live.json      { code: {score,level,reasons[],trend,prevScore} }（score≥門檻者）
  data/risk_score_history.json   { code: [{d,s},...] } 每日分數（給 7 天趨勢；最多保留 8 筆）

等級：<25 低 / 25-49 中 / 50-74 高 / ≥75 極高
非投資建議，僅供「重新檢查持有理由」之提醒。
"""
import json
import sys
import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
TODAY = datetime.date.today()
TODAY_S = TODAY.isoformat()

INCLUDE_MIN = 12     # 分數 ≥ 此值才寫進 live（聚焦真正有風險的）
HIST_KEEP = 8        # 每檔保留最近幾筆歷史
TREND_DAYS = 6       # 與幾天前比較（抓「近一週」）
TREND_UP = 12        # 分數上升多少視為「風險升高」


def load(name, key=None):
    try:
        d = json.loads((DATA_DIR / name).read_text(encoding="utf-8"))
        return d.get(key, {}) if key else d
    except Exception as e:
        print(f"[warn] 讀 {name} 失敗: {e}")
        return {}


def num(x):
    return x if isinstance(x, (int, float)) and not isinstance(x, bool) else None


def pct_change(price, change):
    prev = (price or 0) - (change or 0)
    return (change / prev * 100) if prev else 0.0


def avg_vol(bars):
    """前 20 根（不含當日）的平均量；不足則用現有的。"""
    if not bars or len(bars) < 2:
        return None
    hist = [b.get("volume") or 0 for b in bars[:-1]][-20:]
    return (sum(hist) / len(hist)) if hist else None


def score_stock(s, D):
    """回傳 (score, reasons[])。score 已 cap 0-100。"""
    code = s.get("code")
    price = s.get("price") or 0
    pts = 0
    reasons = []  # (weight, text)

    att = D["att"].get(code)
    if att:
        if att.get("type") == "處置":
            pts += 40; reasons.append((40, "列為處置股"))
        else:
            pts += 22; reasons.append((22, "列為注意股"))

    pc = pct_change(price, s.get("change") or 0)
    if pc <= -7:
        pts += 18; reasons.append((18, f"今日重挫 {pc:.1f}%"))
    elif pc <= -5:
        pts += 12; reasons.append((12, f"今日跌幅大 {pc:.1f}%"))
    elif pc <= -3:
        pts += 6; reasons.append((6, f"今日下跌 {pc:.1f}%"))

    # 成交量異常（vs 20 日均量）
    bars = D["kl"].get(code)
    av = avg_vol(bars)
    vol = s.get("volume") or 0
    if av and av > 0:
        if vol >= av * 3 and vol >= 50:
            pts += 10; reasons.append((10, f"成交量爆量 {vol/av:.1f}×均量"))
        elif vol <= av * 0.2 and vol >= 0:
            pts += 6; reasons.append((6, "成交量大幅萎縮"))

    inst = D["inst"].get(code)
    fn = num(inst.get("foreign_net_lots")) if inst else None
    if fn is not None:
        if fn <= -3000:
            pts += 14; reasons.append((14, f"外資今日大賣 {abs(int(fn)):,} 張"))
        elif fn <= -1000:
            pts += 7; reasons.append((7, f"外資今日賣超 {abs(int(fn)):,} 張"))

    r = D["rev"].get(code)
    yoy = num(r.get("yoy")) if r else None
    if yoy is not None:
        if yoy <= -50:
            pts += 18; reasons.append((18, f"月營收年減 {abs(yoy):.0f}%"))
        elif yoy <= -30:
            pts += 12; reasons.append((12, f"月營收年減 {abs(yoy):.0f}%"))
        elif yoy <= -10:
            pts += 6; reasons.append((6, f"月營收轉弱（年減 {abs(yoy):.0f}%）"))

    fin = D["fin"].get(code)
    op = num(fin.get("op_margin")) if fin else None
    if op is not None and op < 0:
        pts += 14
        reasons.append((14, "本業大幅虧損" if op < -100 else f"本業虧損（營益率 {op:.1f}%）"))

    fv = D["fv"].get(code)
    pos = num(fv.get("position")) if fv else None
    if pos is not None:
        if pos < 0:
            pts += 12; reasons.append((12, "已跌破合理區間下緣"))
        elif pos <= 0.12:
            pts += 6; reasons.append((6, "逼近合理區間下緣"))

    ind = D["ind"].get(code)
    if ind and ind.get("bb_upper") and ind.get("bb_lower") and ind.get("bb_middle"):
        bbw = (ind["bb_upper"] - ind["bb_lower"]) / ind["bb_middle"] * 100
        if bbw > 45:
            pts += 8; reasons.append((8, "近期股價波動劇烈"))
        elif bbw > 30:
            pts += 4; reasons.append((4, "近期波動偏大"))
    if ind and num(ind.get("ma20")) and price > 0 and price < ind["ma20"]:
        pts += 4; reasons.append((4, "跌破月線"))

    if av is not None:
        if av <= 20:
            pts += 8; reasons.append((8, "成交量偏低、流動性差"))
        elif av <= 100:
            pts += 4; reasons.append((4, "流動性偏低"))

    sbl = D["sbl"].get(code)
    sc = num(sbl.get("short_change")) if sbl else None
    if sc is not None and sc > 0 and av and sc >= av:  # 借券賣出單日增量 ≥ 一日均量
        pts += 5; reasons.append((5, "借券賣出明顯增加"))

    pts = max(0, min(100, pts))
    reasons.sort(key=lambda x: -x[0])
    return pts, [t for _, t in reasons[:5]]


def level_of(score):
    if score >= 75:
        return "極高"
    if score >= 50:
        return "高"
    if score >= 25:
        return "中"
    return "低"


def main():
    print(f"[{datetime.datetime.now():%H:%M:%S}] 計算個股風險分數")
    mgn = load("margin_live.json", "data") or {}
    mgn.update(load("margin_tpex_live.json", "data") or {})
    D = dict(
        att=load("attention_live.json", "data") or {},
        inst=load("institutional_live.json", "data") or {},
        rev=load("revenue_live.json", "revenue") or {},
        fin=load("financials_live.json", "data") or {},
        fv=load("fair_value_live.json", "data") or {},
        ind=load("indicators_live.json", "data") or {},
        sbl=load("sbl_live.json", "data") or {},
        mgn=mgn,
        kl=load("klines.json", "klines") or {},
    )
    stocks = load("stocks_live.json", "stocks") or []
    if not stocks:
        print("[error] 無 stocks，中止"); sys.exit(1)

    history = load("risk_score_history.json") or {}
    if not isinstance(history, dict):
        history = {}

    out = {}
    for s in stocks:
        code = s.get("code")
        if not code:
            continue
        score, reasons = score_stock(s, D)
        # 更新歷史（只記有一定風險的，控制檔案大小）
        if score >= 10:
            hist = [h for h in history.get(code, []) if isinstance(h, dict)]
            hist = [h for h in hist if h.get("d") != TODAY_S]
            hist.append({"d": TODAY_S, "s": score})
            history[code] = hist[-HIST_KEEP:]
        # 7 天趨勢
        trend, prev_score = "new", None
        hist = history.get(code, [])
        past = None
        cutoff = (TODAY - datetime.timedelta(days=TREND_DAYS)).isoformat()
        for h in hist:
            if h.get("d", "") <= cutoff:
                past = h
        if past is None and len(hist) >= 2:
            past = hist[0]  # 沒滿一週就用最早一筆
        if past is not None:
            prev_score = past["s"]
            diff = score - prev_score
            trend = "up" if diff >= TREND_UP else ("down" if diff <= -TREND_UP else "flat")

        if score >= INCLUDE_MIN:
            out[code] = {
                "score": score,
                "level": level_of(score),
                "reasons": reasons,
                "trend": trend,
                "prevScore": prev_score,
            }

    # 修剪過期歷史（>12 天沒更新的 code 移除）
    stale_cut = (TODAY - datetime.timedelta(days=12)).isoformat()
    for code in list(history.keys()):
        h = history[code]
        if not h or h[-1].get("d", "") < stale_cut:
            del history[code]

    (DATA_DIR / "risk_score_live.json").write_text(json.dumps({
        "updatedAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source": "領富 AI 風險分數（多訊號加權）",
        "count": len(out),
        "data": out,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    (DATA_DIR / "risk_score_history.json").write_text(
        json.dumps(history, ensure_ascii=False), encoding="utf-8")

    # 警示歷史：每天存一筆當日高風險事件（score≥50），保留近 60 天 → 給「警示歷史」用
    names = {s.get("code"): s.get("name", "") for s in stocks if s.get("code")}
    today_items = [{"code": c, "name": names.get(c, ""), "score": v["score"], "level": v["level"], "reasons": v["reasons"][:3]}
                   for c, v in sorted(out.items(), key=lambda kv: -kv[1]["score"]) if v["score"] >= 50]
    ah = load("alert_history.json") or {}
    hist_list = [e for e in (ah.get("history") or []) if isinstance(e, dict) and e.get("date") != TODAY_S]
    hist_list.append({"date": TODAY_S, "count": len(today_items), "items": today_items[:40]})
    hist_list = sorted(hist_list, key=lambda e: e.get("date", ""))[-60:]
    (DATA_DIR / "alert_history.json").write_text(json.dumps(
        {"updatedAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "history": hist_list},
        ensure_ascii=False), encoding="utf-8")

    lv = {}
    for v in out.values():
        lv[v["level"]] = lv.get(v["level"], 0) + 1
    print(f"✅ 風險分數 {len(out)} 檔（門檻≥{INCLUDE_MIN}）：{lv}；歷史檔 {len(history)} 檔")


if __name__ == "__main__":
    main()
