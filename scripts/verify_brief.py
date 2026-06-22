#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
領富 AI · L3 選題 brief「AI 查證輔助」

把一份 brief 裡的個股代號、名稱配對、具體數字,拿去比對【站上已抓好的官方真資料】
(data/companies_live.json、fair_value_live.json、financials_live.json),產出一張
「逐條查證清單」(verify_report),供主編在審核 UI 逐項打勾/打叉。

⚠️ 設計鐵則(YMYL):
  - 這支腳本【只比對、不下結論】。它能告訴你「代號存不存在、官方名稱是什麼、官方產業、
    目前估值標籤、財報數字」,以及「文中把哪個名稱配到哪個代號」對不對。
  - 站上資料【查不到】的(外資估值、法說會口頭、聚合本益比…)一律標 need_human=「查不到→請人工查官方來源」,
    絕不假裝查證過。
  - 數字錯了最傷讀者,所以具體數字一律提醒人工核對原始出處。
  - 最終是否採信、是否發佈,永遠是人。

用法(獨立執行,印出 verify_report):
  python3 scripts/verify_brief.py /Users/rayda/code/xuanti/samples/swarm_brief_20260619.md
  python3 scripts/verify_brief.py brief.json

被 push 端引用(產生 verify_report 一起送):
  from verify_brief import build_verify_report
  report = build_verify_report(brief, data_dir="data")
"""

import json
import os
import re
import sys

# 台股上市/上櫃產業代碼 → 名稱(TWSE 標準分類;查不到的代碼就顯示原碼)
INDUSTRY_MAP = {
    "01": "水泥", "02": "食品", "03": "塑膠", "04": "紡織纖維", "05": "電機機械",
    "06": "電器電纜", "08": "玻璃陶瓷", "09": "造紙", "10": "鋼鐵", "11": "橡膠",
    "12": "汽車", "14": "建材營造", "15": "航運", "16": "觀光餐旅", "17": "金融保險",
    "18": "貿易百貨", "19": "綜合", "20": "其他", "21": "化學", "22": "生技醫療",
    "23": "油電燃氣", "24": "半導體", "25": "電腦及週邊設備", "26": "光電",
    "27": "通信網路", "28": "電子零組件", "29": "電子通路", "30": "資訊服務",
    "31": "其他電子", "32": "文化創意", "33": "農業科技", "34": "電子商務", "35": "綠能環保",
    "36": "數位雲端", "37": "運動休閒", "38": "居家生活", "80": "管理股票",
}

# 具體數字樣式:百分比、倍數、金額、年份範圍等(用來提醒人工核對來源)
_NUM_RE = re.compile(r"\d+(?:\.\d+)?\s*(?:%|％|倍|億|兆|萬|元)")


def _load(data_dir, fn):
    try:
        with open(os.path.join(data_dir, fn), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _companies(data_dir):
    """code -> {name, abbrev, industry}"""
    d = _load(data_dir, "companies_live.json") or {}
    return d.get("companies", {}) if isinstance(d, dict) else {}


def _fair_value(data_dir):
    """code -> {name, label, position, low, high, price}"""
    d = _load(data_dir, "fair_value_live.json") or {}
    rows = d.get("data", {}) if isinstance(d, dict) else {}
    return rows if isinstance(rows, dict) else {}


def _financials(data_dir):
    d = _load(data_dir, "financials_live.json") or {}
    rows = d.get("data", {}) if isinstance(d, dict) else {}
    return rows if isinstance(rows, dict) else {}


def _rows_and_date(data_dir, fn):
    """回傳 (code->row dict, sourceDate)。"""
    d = _load(data_dir, fn) or {}
    rows = d.get("data", {}) if isinstance(d, dict) else {}
    date = (d.get("sourceDate") or d.get("updatedAt") or "") if isinstance(d, dict) else ""
    return (rows if isinstance(rows, dict) else {}), date


def _fmt(n):
    """整數加千分位；非數字原樣回傳。"""
    try:
        return f"{int(round(float(n))):,}"
    except Exception:
        return str(n)


def _signed(n):
    try:
        v = int(round(float(n)))
        return f"+{v:,}" if v > 0 else f"{v:,}"
    except Exception:
        return str(n)


def _norm(s):
    return re.sub(r"\s+", "", str(s or ""))


def _name_matches(claimed, official_name, official_abbrev):
    """文中名稱是否對得上官方名稱/簡稱(任一方向包含即算對)。"""
    c, n, a = _norm(claimed), _norm(official_name), _norm(official_abbrev)
    if not c:
        return None  # 沒提供名稱,無法比對
    for off in (a, n):
        if off and (c == off or c in off or off in c):
            return True
    return False


def _check_code(code, claimed_name, comp, fv, fin, inst=None, streak=None, margin=None):
    """對單一代號做查證,回一個 item。"""
    inst = inst or {}; streak = streak or {}; margin = margin or {}
    item = {"type": "ticker", "code": code, "claim_name": claimed_name or None, "source": "data/companies_live.json"}
    info = comp.get(code)
    if not info:
        item["verdict"] = "not_found"
        item["note"] = f"代號 {code} 不在站上上市櫃名冊 → 可能打錯或非台股,請人工確認"
        return item

    official_name = info.get("name") or info.get("abbrev") or ""
    abbrev = info.get("abbrev") or ""
    ind_code = str(info.get("industry") or "")
    industry = INDUSTRY_MAP.get(ind_code, ind_code or "—")
    item["official_name"] = official_name
    item["official_abbrev"] = abbrev
    item["industry"] = industry

    # 名稱↔代號配對(最關鍵:抓「代號安錯公司」)
    match = _name_matches(claimed_name, official_name, abbrev)
    if match is True:
        item["verdict"] = "ok"
        item["note"] = f"{abbrev or official_name}（{code}）代號與名稱相符；產業={industry}"
    elif match is False:
        item["verdict"] = "mismatch"
        item["note"] = f"⚠ 文中寫「{claimed_name} {code}」,但 {code} 官方是「{abbrev or official_name}」→ 名稱配錯,請改正"
    else:
        item["verdict"] = "ok_name_unknown"
        item["note"] = f"代號 {code} 存在=「{abbrev or official_name}」；產業={industry}（文中未明寫名稱,無法比對配對）"

    # 附上目前估值標籤(供「估值過高/過低」類主張參考;非買賣建議)
    v = fv.get(code)
    if isinstance(v, dict) and v.get("label"):
        item["valuation_label"] = v.get("label")
        item["source"] = item["source"] + " + fair_value_live.json"
    # 附最新一季財報摘要(供數字類主張對照)
    f = fin.get(code)
    if isinstance(f, dict):
        item["financials"] = {k: f.get(k) for k in ("year", "quarter", "revenue_m", "gross_margin", "net_margin") if k in f}

    # 附籌碼(供「外資撤退/融資過熱」類主張直接對照,免人工再查;單位:張)
    chips = {}
    ii = inst.get(code)
    if isinstance(ii, dict):
        for k in ("foreign_net_lots", "trust_net_lots", "dealer_net_lots", "total_net_lots"):
            if ii.get(k) is not None:
                chips[k] = ii.get(k)
    st = streak.get(code)
    if isinstance(st, dict) and st.get("days"):
        chips["inst_streak"] = {"dir": st.get("dir"), "days": st.get("days")}
    mg = margin.get(code)
    if isinstance(mg, dict):
        for k in ("margin_balance", "margin_change"):
            if mg.get(k) is not None:
                chips[k] = mg.get(k)
    if chips:
        # 給 UI 直接顯示的一行摘要
        parts = []
        if "foreign_net_lots" in chips:
            parts.append(f"外資 {_signed(chips['foreign_net_lots'])} 張")
        if "total_net_lots" in chips:
            parts.append(f"三大法人 {_signed(chips['total_net_lots'])} 張")
        if "inst_streak" in chips:
            parts.append(f"連{chips['inst_streak']['days']}{'買' if chips['inst_streak']['dir']=='buy' else '賣'}")
        if "margin_balance" in chips:
            mc = f"（{_signed(chips['margin_change'])}）" if "margin_change" in chips else ""
            parts.append(f"融資餘額 {_fmt(chips['margin_balance'])}{mc}")
        chips["summary"] = "、".join(parts)
        item["chips"] = chips
        item["source"] = item["source"] + " + institutional/margin_live.json"
    return item


# ───────────────────────── 數字審查:分類 + 本地比對 + 來源路由 ─────────────────────────
# 站上即時資料的基準年(跨年時更新,或日後改讀各檔 sourceDate)。早於此年的股價 = 歷史價,本地查不到。
CURRENT_YEAR = 2026
_YEAR_RE = re.compile(r"(?:19|20)\d{2}")


def _num_val(raw):
    """從 '1310 元' / '15 倍' / '10%' 抽出數值;抽不到回 None。"""
    m = re.search(r"\d+(?:\.\d+)?", raw)
    return float(m.group(0)) if m else None


def _years_in(ctx):
    return [int(y) for y in _YEAR_RE.findall(ctx)]


def _src(name, url=None):
    return {"name": name, "url": url}


# 官方來源路由表:只回「該去哪查 + 連結」,不下結論。{code} 會填入上下文抓到的代號。
def _route_for(kind, code):
    g = (lambda path: f"https://goodinfo.tw/tw/{path}?STOCK_ID={code}") if code else (lambda path: None)
    table = {
        "historical_price": ("route", "歷史股價:站上只有即時資料,請查官方歷史行情核對。",
                             _src("證交所 個股日成交歷史 / Goodinfo K線", g("ShowK_Chart.asp"))),
        "index_move":       ("route", "指數漲跌:非台股個股,站上無此指數,請查指數行情來源核對日期與幅度。",
                             _src("指數行情(費半 SOX/台指/美股大盤)", "https://invest.cnyes.com/index/GI/SOX")),
        "pe_multiple":      ("route", "本益比/評價倍數:站上無 PE 欄位(只有合理價區間),且常為族群概化 → 建議抽樣數檔個股 PE 佐證,勿寫成全族群定論。",
                             _src("Goodinfo 個股本益比 / 證交所 PE 殖利率 PB", g("StockBzPerformance.asp"))),
        "share_pct":        ("route", "佔比/市佔:屬公司或產業聚合數,請以公司財報、法說會簡報或產業報告核對原始出處。",
                             _src("公開資訊觀測站 MOPS(財報/法說會)", "https://mops.twse.com.tw/mops/web/t100sb02_1")),
        "market_convention":("need_human", "市場慣例/門檻(如『常用 X% 為界』):屬主觀判斷,無單一官方來源 → 主編自行斟酌措辭,避免寫成事實。", None),
        "forecast":         ("need_human", "未來預估/時程:屬預測值,無法事前查證 → 請標清楚預估機構與發布日,勿寫成定論。", None),
        "unknown":          ("need_human", "具體數字:站上無對應 → 請以公司法說會、重訊、財報核對原始出處;查不到者勿寫成定論。",
                             _src("公開資訊觀測站 MOPS(重訊 t05st01 / 財報 t164sb04)", "https://mops.twse.com.tw/mops/web/t05st01")),
    }
    verdict, note, source = table.get(kind, table["unknown"])
    return {"verdict": verdict, "note": note, "suggested_source": source}


def _classify_number(raw, ctx):
    has = lambda *ws: any(w in ctx for w in ws)
    is_pct = ("%" in raw or "％" in raw)
    is_mult = ("倍" in raw)
    is_money = ("元" in raw)
    years = _years_in(ctx)

    if has("外資", "投信", "自營", "三大法人", "買賣超", "賣超", "買超", "融資", "融券") or raw.endswith("張"):
        return "inst_chips"
    if is_pct and has("毛利", "淨利", "營益", "利益率", "利潤率"):
        return "margin_ratio"
    if is_pct and has("費半", "費城", "SOX", "台指", "加權", "那斯達克", "道瓊", "標普", "指數", "夜盤"):
        return "index_move"
    if is_mult or has("本益比", "ＰＥ", "PE", "評價", "重估"):
        return "pe_multiple"
    if has("市場常用", "慣例", "業界", "為界", "門檻", "通常", "一般認為", "普遍"):
        return "market_convention"
    if has("預估", "上看", "看到", "目標", "CAGR", "年複合", "可望", "預計", "上修", "下修", "未來") \
            or any(y > CURRENT_YEAR for y in years):
        return "forecast"
    if is_pct and has("佔比", "占比", "比重", "市佔", "佔率", "營收佔"):
        return "share_pct"
    if is_money and any(y < CURRENT_YEAR for y in years):
        return "historical_price"
    if is_money and has("股價", "收盤", "現價", "報價", "目前", "現在", "今日"):
        return "current_price"
    return "unknown"


def _audit_number(raw, ctx, comp, fv, fin, num_span=None):
    """對單一數字:分類 → 能對本地就比對(✅/⚠️),對不到就路由官方來源。
    num_span:(lo,hi) 數字本身在 ctx 的位置,掃代號時要跳過,免得數字(如 1310)被當成台股代號。"""
    kind = _classify_number(raw, ctx)
    item = {"raw": raw, "kind": kind, "context": re.sub(r"\s+", " ", ctx).strip()[:140]}

    # 上下文裡的台股代號(供本地比對 / 路由連結帶代號);跳過數字自己,避免 1310 元 被當成代號 1310
    code = None
    for m in re.finditer(r"(?<!\d)(\d{4})(?!\d)", ctx):
        if num_span and not (m.end() <= num_span[0] or m.start() >= num_span[1]):
            continue
        if m.group(1) in comp or m.group(1) in fv:
            code = m.group(1)
            break

    # ── 本地可比對:現價 ──
    if kind == "current_price" and code and isinstance(fv.get(code), dict) and fv[code].get("price") is not None:
        official, claimed = float(fv[code]["price"]), _num_val(raw)
        item["local_ref"] = {"field": "現價", "value": official, "source": "fair_value_live.json"}
        if claimed is not None and official:
            ok = abs(claimed - official) / official <= 0.02  # 容差 2%
            item["verdict"] = "match" if ok else "mismatch"
            item["note"] = f"文中 {raw} vs 站上現價 {official} 元 → {'相符' if ok else '不符,請確認'}"
            return item

    # ── 本地可比對:毛利率/淨利率 ──
    if kind == "margin_ratio" and code and isinstance(fin.get(code), dict):
        claimed = _num_val(raw)
        cands = {"毛利率": fin[code].get("gross_margin"), "淨利率": fin[code].get("net_margin"),
                 "營益率": fin[code].get("op_margin")}
        best = min(((abs(claimed - v), k, v) for k, v in cands.items() if v is not None and claimed is not None),
                   default=None)
        if best is not None:
            diff, fld, v = best
            item["local_ref"] = {"field": fld, "value": v, "source": "financials_live.json"}
            item["verdict"] = "match" if diff <= 0.5 else "mismatch"  # 容差 0.5 個百分點
            item["note"] = f"文中 {raw} vs 站上{fld} {v}% → {'相符' if diff <= 0.5 else '不符或非同一指標,請確認'}"
            return item

    # ── 籌碼類:指出本地有逐檔數據可對(細節在上方 ticker items 的 chips) ──
    if kind == "inst_chips":
        item["verdict"] = "need_human"
        item["note"] = "籌碼數字(法人買賣超/融資):本地有逐檔資料,請對照上方該代號的『籌碼』欄位核對(單位:張)。"
        item["suggested_source"] = _src("站上 institutional_live / margin_live(逐檔)", None)
        if code:
            item["code"] = code
        return item

    # ── 對不到本地 → 路由官方來源 ──
    item.update(_route_for(kind, code))
    if code:
        item["code"] = code
    return item


def build_verify_report(brief, data_dir="data"):
    comp = _companies(data_dir)
    fv = _fair_value(data_dir)
    fin = _financials(data_dir)
    inst, inst_date = _rows_and_date(data_dir, "institutional_live.json")
    streak, _ = _rows_and_date(data_dir, "inst_streak_live.json")
    margin, margin_date = _rows_and_date(data_dir, "margin_live.json")

    text_blob = "\n".join([
        str(brief.get("title_hint") or ""),
        str(brief.get("thesis") or ""),
        "\n".join(brief.get("risk_notes") or []),
        ((brief.get("source_meta") or {}).get("brief_md") or "") if isinstance(brief.get("source_meta"), dict) else "",
    ])

    items = []
    seen = set()

    # brief 自己宣告的個股代號(sectors[].sample_tickers)= 權威「這些是股票」清單
    declared = set()
    for s in (brief.get("sectors") or []):
        for code in (s.get("sample_tickers") or []):
            if re.fullmatch(r"\d{4}", str(code)):
                declared.add(str(code))

    # (1) 從全文抓「中文名 + 4 碼代號」配對,逐一比對(抓代號安錯公司)
    for m in re.finditer(r"([一-鿿]{2,6})\s*([0-9]{4})(?![0-9])", text_blob):
        name, code = m.group(1), m.group(2)
        if code not in comp:        # 不是台股代號 → 跳過
            continue
        if code in seen:
            continue
        it = _check_code(code, name, comp, fv, fin, inst, streak, margin)
        # 防誤報:名稱對不上、且 brief 沒把它列為個股 → 多半是年份/價格(如「放量在 2027」),跳過不報
        if it["verdict"] == "mismatch" and code not in declared:
            continue
        seen.add(code)
        items.append(it)

    # (2) 補上 sectors[].sample_tickers 裡、全文配對沒抓到的代號(只驗存在/產業/估值)
    for s in (brief.get("sectors") or []):
        for code in (s.get("sample_tickers") or []):
            code = str(code)
            if code in seen or not re.fullmatch(r"\d{4}", code):
                continue
            seen.add(code)
            it = _check_code(code, None, comp, fv, fin, inst, streak, margin)
            it["sector_hint"] = s.get("sector")
            items.append(it)

    # (3) 具體數字 → 逐個分類:能對站上資料就比對(✅/⚠️),對不到就路由「該查的官方來源」
    audits, seen = [], set()
    for m in _NUM_RE.finditer(text_blob):
        raw = m.group(0).strip()
        ctx_start = max(0, m.start() - 30)
        ctx = text_blob[ctx_start: m.end() + 30]  # ±30 字上下文供分類
        a = _audit_number(raw, ctx, comp, fv, fin, num_span=(m.start() - ctx_start, m.end() - ctx_start))
        dedupe_key = (raw, a["kind"])  # 同數字+同類型只留一筆,避免清單灌水
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        audits.append(a)

    summary = {}
    for a in audits:
        summary[a["verdict"]] = summary.get(a["verdict"], 0) + 1
    number_item = {
        "type": "numbers",
        # 整體 verdict 仍以「是否還需人工」為準:有不符→mismatch;全部本地相符→ok;否則 need_human
        "verdict": ("mismatch" if summary.get("mismatch") else
                    "ok" if audits and set(summary) <= {"match"} else "need_human"),
        "count": len(audits),
        "samples": [a["raw"] for a in audits][:25],  # 保留舊欄位,UI 不致 break
        "summary": summary,                           # 各 verdict 計數:match/mismatch/route/need_human
        "details": audits,                            # 逐數字審查結果(分類+本地比對+來源路由)
        "note": "每個數字已分類:current_price/margin_ratio 可對站上資料自動比對;historical_price/index_move/pe_multiple/share_pct 已附『該查的官方來源』;market_convention/forecast 屬主觀或未來值,以主編判斷為準。",
        "source": "本地比對 data/(現價/財報/籌碼) + 官方來源路由",
    }

    counts = {"ok": 0, "ok_name_unknown": 0, "mismatch": 0, "not_found": 0}
    for it in items:
        counts[it["verdict"]] = counts.get(it["verdict"], 0) + 1

    return {
        "basis": "比對站上官方資料:companies_live(名冊/產業) + fair_value_live(估值標籤) + financials_live(財報) + 籌碼(法人買賣超/融資餘額" + (("，資料日 " + str(inst_date or margin_date)) if (inst_date or margin_date) else "") + ")",
        "disclaimer": "本清單僅做『資料比對』,非查證背書;數字與口頭主張須人工核對官方來源,發佈與否由編輯決定。",
        "ticker_summary": counts,
        "ticker_total": len(items),
        "items": items,
        "numbers": number_item,
    }


def _load_brief(path):
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    if path.lower().endswith(".json"):
        return json.loads(raw)
    # markdown → 借用 push 端的解析器
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import push_brief_to_leadfu as p
    return p.brief_from_markdown(raw, path)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 scripts/verify_brief.py <brief.md|brief.json> [data_dir]", file=sys.stderr)
        sys.exit(1)
    data_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    brief = _load_brief(sys.argv[1])
    report = build_verify_report(brief, data_dir=data_dir)
    c = report["ticker_summary"]
    s = report["numbers"]["summary"]
    print(f"查證了 {report['ticker_total']} 檔代號 → 相符 {c.get('ok',0)+c.get('ok_name_unknown',0)}"
          f"、配錯 {c.get('mismatch',0)}、查無 {c.get('not_found',0)}；"
          f"數字 {report['numbers']['count']} 處 → 本地相符 {s.get('match',0)}、不符 {s.get('mismatch',0)}、"
          f"路由官方來源 {s.get('route',0)}、人工判斷 {s.get('need_human',0)}",
          file=sys.stderr)
    print(json.dumps(report, ensure_ascii=False, indent=2))
