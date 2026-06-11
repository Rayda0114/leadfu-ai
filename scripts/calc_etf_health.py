"""
領富 AI · 高股息 ETF 健檢
殖利率是不是「真的」：TTM 配息率 vs 近 6 月含息報酬、溢價、規模、配息頻率 → 體檢徽章
資料源（全官方/站內既有）：etf_div_live + etf_nav_live + returns_live + stocks_live + etf_basic_live
輸出：data/etf_health_live.json
"""
import json, sys
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

def load(n):
    p = DATA / n
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}

def main():
    div = load("etf_div_live.json").get("data", {})
    nav = load("etf_nav_live.json").get("data", {})
    ret = load("returns_live.json").get("data", {})
    basic = load("etf_basic_live.json").get("data", {})
    stocks = {str(s["code"]): s for s in load("stocks_live.json").get("stocks", [])}

    out = {}
    for code, dv in div.items():
        s = stocks.get(code)
        if not s or not s.get("price") or not dv.get("ttmCash"):
            continue
        price = float(s["price"])
        ttm_yield = round(dv["ttmCash"] / price * 100, 2)
        r = ret.get(code) or {}
        r6 = r.get("r6m")
        # 近 6 月含息總報酬估算 = 價格報酬 + 半年配息/現價
        total6 = round(r6 + dv["ttmCash"] / 2 / price * 100, 2) if r6 is not None else None
        nv = nav.get(code) or {}
        prem = nv.get("premium")
        aum = nv.get("aumYi")
        b = basic.get(code) or {}
        badges = []   # [text, level g/a/r]
        if ttm_yield >= 5 and total6 is not None and total6 < 0:
            badges.append(["賺息賠價差：高配息但近 6 月含息報酬為負", "r"])
        elif ttm_yield >= 5 and total6 is not None and total6 < ttm_yield / 2:
            badges.append(["配息高但總報酬偏低，留意是否「配本金感」", "a"])
        if prem is not None and prem >= 1:
            badges.append([f"溢價 {prem}%：買貴於淨值", "a"])
        elif prem is not None and prem <= -1:
            badges.append([f"折價 {abs(prem)}%", "g"])
        if aum is not None and aum < 10:
            badges.append([f"規模僅 {aum} 億：流動性與清算風險留意", "a"])
        if dv.get("distCount", 0) >= 4:
            badges.append([f"年配 {dv['distCount']} 次（{'月配' if dv['distCount'] >= 12 else '季配'}型）", "g"])
        if not badges:
            badges.append(["本次檢查無明顯警示", "g"])
        out[code] = {
            "name": dv.get("name") or s.get("name"), "price": price,
            "ttm_cash": dv["ttmCash"], "ttm_yield": ttm_yield,
            "last_ex": dv.get("lastExDate"), "dist_count": dv.get("distCount"),
            "r6m": r6, "total6": total6,
            "premium": prem, "aum_yi": aum,
            "index": b.get("index"), "badges": badges,
        }
    payload = {"updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M"),
               "note": "高股息 ETF 健檢：殖利率 vs 總報酬、溢價、規模、配息頻率（公開資料整理、非投資建議）",
               "count": len(out), "data": out}
    (DATA / "etf_health_live.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print(f"✅ etf_health_live.json：{len(out)} 檔")

if __name__ == "__main__":
    main()
