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


def _check_code(code, claimed_name, comp, fv, fin):
    """對單一代號做查證,回一個 item。"""
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
    return item


def build_verify_report(brief, data_dir="data"):
    comp = _companies(data_dir)
    fv = _fair_value(data_dir)
    fin = _financials(data_dir)

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
        it = _check_code(code, name, comp, fv, fin)
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
            it = _check_code(code, None, comp, fv, fin)
            it["sector_hint"] = s.get("sector")
            items.append(it)

    # (3) 具體數字 → 一律提醒人工核對原始出處(站上資料多半沒有這類聚合/估值數字)
    nums = sorted(set(m.group(0).strip() for m in _NUM_RE.finditer(text_blob)))
    number_item = {
        "type": "numbers",
        "verdict": "need_human",
        "count": len(nums),
        "samples": nums[:25],
        "note": "具體數字(本益比/佔比/金額/時程)站上多無原始出處,請逐一以公司法說會、重訊、財報核對;查不到者勿寫成定論。",
        "source": None,
    }

    counts = {"ok": 0, "ok_name_unknown": 0, "mismatch": 0, "not_found": 0}
    for it in items:
        counts[it["verdict"]] = counts.get(it["verdict"], 0) + 1

    return {
        "basis": "比對站上官方資料:companies_live(名冊/產業) + fair_value_live(估值標籤) + financials_live(財報)",
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
    print(f"查證了 {report['ticker_total']} 檔代號 → 相符 {c.get('ok',0)+c.get('ok_name_unknown',0)}"
          f"、配錯 {c.get('mismatch',0)}、查無 {c.get('not_found',0)}；具體數字 {report['numbers']['count']} 處需人工核對",
          file=sys.stderr)
    print(json.dumps(report, ensure_ascii=False, indent=2))
