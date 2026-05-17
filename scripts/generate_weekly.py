"""
領富 AI · 產業週報自動生成
每週一早上跑（GitHub Actions cron），AI 整理上週各產業重點。

資料源（全部本地，不另外打 API）：
  stocks_live.json     當日收盤 / 漲跌（用來算週漲幅）
  klines.json          30 天歷史 OHLCV（算週初週末變化）
  institutional_live.json  三大法人買賣超
  margin_live.json      上市融資融券
  margin_tpex_live.json 上櫃融資融券
  sbl_live.json         借券（外資空單）
  revenue_live.json     月營收年增
  valuation_live.json   殖利率 / P/E / P/B

AI 透過 Cloudflare Worker /api/ask（共用既有 Nvidia 配置，無需另設 secret）。

產出：data/weekly_report.json
{
  "weekYear": 2026, "weekNum": 20,
  "weekStart": "2026-05-12", "weekEnd": "2026-05-16",
  "generatedAt": "...",
  "market": { "taiex": ..., "otc": ..., "summary": "AI 寫的 200 字" },
  "industries": [
    {
      "name": "半導體",
      "stockCount": 232,
      "narrative": "AI 寫的 200-300 字",
      "highlights": [
        { "code": "2330", "name": "台積電", "kind": "週漲幅", "value": "+5.2%" },
        ...
      ]
    },
    ...
  ]
}
"""

import json
import os
import ssl
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import Request, urlopen

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUT = DATA_DIR / "weekly_report.json"

# AI 端點：呼叫自家 Worker，共用既有配置
ASK_URL = os.environ.get("ASK_URL", "https://leadfuai.com/api/ask")
UA = "Mozilla/5.0 LeadFuAI-WeeklyGen/1.0"

_INSECURE_CTX = ssl.create_default_context()
_INSECURE_CTX.check_hostname = False
_INSECURE_CTX.verify_mode = ssl.CERT_NONE

# 主要產業（取股數多的、有經濟意義的）
PRIMARY_INDUSTRIES = [
    "半導體", "電子零組件", "光電", "電腦及周邊", "通信網路",
    "金融保險", "生技醫療", "鋼鐵", "化學", "建材營造",
    "電機機械", "汽車", "食品", "紡織", "觀光餐旅",
    "綠能環保", "資訊服務", "數位雲端", "其他電子"
]


def load(name):
    p = DATA_DIR / f"{name}.json"
    if not p.exists():
        return None
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def week_return(bars):
    """從 klines 算「上週五 vs 前週五」5 個交易日漲跌幅"""
    if not bars or len(bars) < 6:
        return None
    bars = sorted(bars, key=lambda b: b.get("date", ""))
    last = bars[-1]["close"]
    prior = bars[-6]["close"]   # 5 交易日前
    if prior <= 0:
        return None
    return round((last - prior) / prior * 100, 2)


def aggregate(stocks, klines, inst, sbl, rev, val, margin):
    """按產業聚合每檔個股的關鍵指標"""
    by_industry = {}
    for s in stocks:
        code = s["code"]
        cat = s.get("category", "其他")
        if cat not in by_industry:
            by_industry[cat] = []
        bars = klines.get(code, [])
        wr = week_return(bars)
        i = inst.get(code, {})
        b = sbl.get(code, {})
        r = rev.get(code, {})
        v = val.get(code, {})
        m = margin.get(code, {})

        by_industry[cat].append({
            "code": code,
            "name": s["name"],
            "market": s.get("market"),
            "price": s.get("price"),
            "volume_lots": s.get("volume", 0),
            "week_return": wr,
            "foreign_net": i.get("foreign_net_lots", 0),
            "trust_net": i.get("trust_net_lots", 0),
            "total_inst_net": i.get("total_net_lots", 0),
            "sbl_change": b.get("sbl_change", 0),
            "margin_change": m.get("margin_change", 0),
            "revenue_yoy": r.get("yoy") if r else None,
            "yield_pct": v.get("yield_pct") if v else None,
            "pe_ratio": v.get("pe_ratio") if v else None,
        })
    return by_industry


def pick_highlights(industry_stocks):
    """從一個產業挑出 5 個值得寫進報告的個股"""
    highlights = []
    by_wk = sorted([s for s in industry_stocks if s["week_return"] is not None],
                   key=lambda x: x["week_return"], reverse=True)
    by_inst = sorted(industry_stocks, key=lambda x: x["total_inst_net"], reverse=True)
    by_sbl = sorted(industry_stocks, key=lambda x: x["sbl_change"], reverse=True)
    by_yield = sorted([s for s in industry_stocks if s["yield_pct"]],
                      key=lambda x: x["yield_pct"], reverse=True)
    by_rev = sorted([s for s in industry_stocks if s["revenue_yoy"] is not None],
                    key=lambda x: x["revenue_yoy"], reverse=True)

    seen = set()
    def add(item, kind, value):
        if item["code"] in seen:
            return
        seen.add(item["code"])
        highlights.append({
            "code": item["code"], "name": item["name"],
            "kind": kind, "value": value
        })

    if by_wk:
        add(by_wk[0], "週漲幅 #1", f"+{by_wk[0]['week_return']:.1f}%" if by_wk[0]['week_return'] >= 0 else f"{by_wk[0]['week_return']:.1f}%")
        if len(by_wk) > 1 and by_wk[-1]["week_return"] < 0:
            add(by_wk[-1], "週跌幅 #1", f"{by_wk[-1]['week_return']:.1f}%")
    if by_inst and by_inst[0]["total_inst_net"] > 100:
        add(by_inst[0], "法人加碼", f"+{by_inst[0]['total_inst_net']:,} 張")
    if by_sbl and by_sbl[0]["sbl_change"] > 1_000_000:
        add(by_sbl[0], "外資借券放空", f"+{by_sbl[0]['sbl_change']/1_000_000:.1f}M 股")
    if by_rev and by_rev[0]["revenue_yoy"] is not None and by_rev[0]["revenue_yoy"] > 20:
        add(by_rev[0], "月營收年增", f"+{by_rev[0]['revenue_yoy']:.1f}%")
    if by_yield and by_yield[0]["yield_pct"] >= 4:
        add(by_yield[0], "高殖利率", f"{by_yield[0]['yield_pct']:.2f}%")

    return highlights[:5]


def industry_summary_data(industry_stocks):
    """給 AI 看的「壓縮版資料表」"""
    if not industry_stocks:
        return None
    wk = [s["week_return"] for s in industry_stocks if s["week_return"] is not None]
    avg_wk = sum(wk) / len(wk) if wk else None
    foreign_total = sum(s["foreign_net"] for s in industry_stocks)
    return {
        "stock_count": len(industry_stocks),
        "avg_week_return": round(avg_wk, 2) if avg_wk is not None else None,
        "foreign_net_total": foreign_total,
        "highlights": pick_highlights(industry_stocks),
    }


def call_ai(prompt, max_tokens=4000, retries=3):
    """呼叫 Cloudflare Worker /api/ask（共用既有 Nvidia 配置）
    Worker 回傳格式：{ answer, model, usage }
    """
    body = json.dumps({
        "question": prompt,
        "max_tokens": max_tokens,
        "stream": False
    }).encode("utf-8")

    last_err = None
    for attempt in range(1, retries + 1):
        try:
            req = Request(ASK_URL, data=body, method="POST", headers={
                "Content-Type": "application/json",
                "User-Agent": UA
            })
            with urlopen(req, timeout=120, context=_INSECURE_CTX) as resp:
                raw = resp.read().decode("utf-8")
            data = json.loads(raw)
            if isinstance(data, dict):
                if data.get("error"):
                    raise RuntimeError(f"Worker 回傳錯誤：{data['error']}")
                return data.get("answer", "")
            return ""
        except Exception as e:
            last_err = e
            print(f"  ⚠ AI 呼叫第 {attempt} 次失敗：{e}")
            time.sleep(5 * attempt)
    print(f"  ❌ AI 三次都失敗，最後錯誤：{last_err}")
    return ""


def week_info():
    """回傳 (year, week_num, start_date, end_date)：上週一到上週五"""
    today = datetime.now()
    # 找上週五（最近的週五，但若今天 >= 週六則用本週五）
    weekday = today.weekday()   # 0=Mon
    # 想要的是「上個交易週」：通常週一跑時抓上上週一 ~ 上週五
    # 簡化：以「過去 7 天」當作週區間
    end = today
    while end.weekday() != 4:   # 0=Mon, 4=Fri
        end -= timedelta(days=1)
    start = end - timedelta(days=4)   # 週一
    iso_year, iso_week, _ = end.isocalendar()
    return iso_year, iso_week, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def main():
    print("=" * 60)
    print(f"產業週報生成 ・ {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 60)

    # 載入全部資料
    stocks   = (load("stocks_live") or {}).get("stocks", [])
    klines   = (load("klines") or {}).get("klines", {})
    inst     = (load("institutional_live") or {}).get("data", {})
    sbl      = (load("sbl_live") or {}).get("data", {})
    rev      = (load("revenue_live") or {}).get("revenue", {})
    val      = (load("valuation_live") or {}).get("data", {})
    margin1  = (load("margin_live") or {}).get("data", {})
    margin2  = (load("margin_tpex_live") or {}).get("data", {})
    margin = {**margin1, **margin2}

    print(f"資料：{len(stocks)} 檔個股 / {len(klines)} 檔 K 線 / {len(inst)} 筆法人 / {len(rev)} 筆月營收")

    if not stocks:
        print("❌ 沒有 stocks_live.json 資料")
        sys.exit(1)

    # 聚合
    by_industry = aggregate(stocks, klines, inst, sbl, rev, val, margin)
    print(f"聚合：{len(by_industry)} 個產業")

    # 整體市場（加權／櫃買週漲跌）
    market_summary = {
        "weekStart": None,
        "weekEnd": None,
        "totalStocks": len(stocks),
    }

    # 挑要寫進報告的產業（主要產業 + 有資料）
    industries_for_report = []
    for ind_name in PRIMARY_INDUSTRIES:
        stocks_in_ind = by_industry.get(ind_name, [])
        if len(stocks_in_ind) < 3:
            continue
        agg = industry_summary_data(stocks_in_ind)
        if not agg:
            continue
        agg["name"] = ind_name
        industries_for_report.append(agg)
        if len(industries_for_report) >= 10:
            break

    print(f"報告產業：{len(industries_for_report)}")

    # 多次小呼叫策略：1 次整體 + 每個產業一次
    week_year, week_num, week_start, week_end = week_info()

    style_guide = ("風格穩重客觀，避免「飆股、噴出、強烈推薦、必漲」等用詞；"
                   "多用「觀察、值得留意、資金流向、動能、籌碼結構」。"
                   "讀者是 45-75 歲高資產退休族。"
                   "禁止給買賣建議。用繁體中文。")

    # 1. 整體市場摘要
    overall_brief = "\n".join([
        f"- {ind['name']}：{ind['stock_count']} 檔，平均週漲跌 {ind['avg_week_return']}%，外資 {'買超' if ind['foreign_net_total']>=0 else '賣超'} {abs(ind['foreign_net_total']):,} 張"
        for ind in industries_for_report
    ])
    market_prompt = f"""請為台股 {week_start} ~ {week_end} 寫一段整體市場觀察。

10 大產業表現：
{overall_brief}

請寫 180~220 字一段（不要分點、不要加標題、不要 markdown），
內容包含：本週資金面強弱輪動、外資動向、值得留意的產業現象。
{style_guide}

直接回應這一段文字即可，前後不要有任何說明或標題。"""

    print("\n▶ 呼叫 AI 寫整體市場摘要...")
    market_summary_text = call_ai(market_prompt, max_tokens=600).strip()
    print(f"  市場摘要字數：{len(market_summary_text)}")

    # 2. 每個產業一次呼叫
    industry_narratives = {}
    for i, ind in enumerate(industries_for_report, 1):
        highlights_str = "、".join([f"{h['code']} {h['name']} ({h['kind']} {h['value']})" for h in ind["highlights"]])
        ind_prompt = f"""請為「{ind['name']}」產業寫一段本週觀察。

資料：
- {ind['stock_count']} 檔個股
- 平均週漲跌 {ind['avg_week_return']}%
- 外資 {'買超' if ind['foreign_net_total']>=0 else '賣超'} {abs(ind['foreign_net_total']):,} 張
- 本週重點個股：{highlights_str}

請寫 180~250 字一段（不要分點、不要加標題、不要 markdown）：
1. 本週這個產業的整體動能（用平均週漲跌與外資數字佐證）
2. 1-2 檔重點個股的觀察與可能原因
3. 結尾給「中性的觀察提醒」（例如「值得追蹤」「建議搭配本益比與基本面評估」）
{style_guide}

直接回應這一段文字即可，前後不要有任何標題或說明。"""

        print(f"  [{i}/{len(industries_for_report)}] {ind['name']} ...", end=" ", flush=True)
        text = call_ai(ind_prompt, max_tokens=600).strip()
        industry_narratives[ind["name"]] = text
        print(f"({len(text)} 字)")
        time.sleep(1.5)   # 不要打太快被 rate limit

    # 組裝最終結構
    report = {
        "weekYear": week_year,
        "weekNum": week_num,
        "weekStart": week_start,
        "weekEnd": week_end,
        "generatedAt": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "market": {
            "totalStocks": len(stocks),
            "summary": market_summary_text or f"本週 {week_start} ~ {week_end} 全市場 {len(stocks)} 檔。"
        },
        "industries": [
            {
                "name": ind["name"],
                "stockCount": ind["stock_count"],
                "avgWeekReturn": ind["avg_week_return"],
                "foreignNetTotal": ind["foreign_net_total"],
                "narrative": industry_narratives.get(ind["name"], "本週本產業資料整理中，請稍後再回來。"),
                "highlights": ind["highlights"]
            } for ind in industries_for_report
        ]
    }

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 已輸出：{OUT.relative_to(ROOT)}")
    print(f"  market summary 字數：{len(market_summary_text)}")
    print(f"  industries: {len(report['industries'])} 個（narrative 平均字數 {sum(len(i['narrative']) for i in report['industries']) // max(len(report['industries']),1)}）")


if __name__ == "__main__":
    main()
