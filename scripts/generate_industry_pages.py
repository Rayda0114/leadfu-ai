"""
領富 AI · 產業頁產生器
- 依個股 category 分組，每個產業產生一頁靜態 HTML：pages/industries/{slug}.html
- 內容（伺服器端、非薄頁）：產業概況 + 速覽（檔數/市場分布/今日漲跌/需注意股數）
  + 成分股表（連到個股頁，含風險等級與主因）+ 資料來源/更新日期/免責 + JSON-LD
- 每日由 GitHub Actions 跑（建議放在 run_all 內、generate_sitemap 之前）
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from html import escape

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "pages" / "industries"
BASE = "https://leadfuai.com"
CSS_V = "3.23.7"
JS_V = "3.24.9"
TODAY = datetime.now().strftime("%Y-%m-%d")

# 產業（category）→（英文 slug, 一句產業概況）。未列入者（其他/其他電子/存託憑證等模糊分類）不產生獨立頁。
INDUSTRY = {
    "半導體": ("semiconductor", "半導體是台股權值核心，涵蓋晶圓代工、IC 設計、封測、設備與材料，與全球景氣循環及 AI、手機、車用需求高度連動。"),
    "生技醫療": ("biotech", "生技醫療涵蓋新藥、學名藥、醫療器材與保健，題材與股價波動大、個股差異懸殊，需特別留意臨床進度與獲利能力。"),
    "電子零組件": ("electronic-components", "電子零組件包含被動元件、連接器、PCB、機殼與散熱等，是電子產業的中游供應鏈，訂單與庫存循環明顯。"),
    "ETF": ("etf", "ETF（指數股票型基金）一籃子持有多檔成分股，分散單一個股風險，適合長期分批布局；仍需留意追蹤標的、費用與槓桿/反向型風險。"),
    "光電": ("optoelectronics", "光電涵蓋面板、LED、光學鏡頭與太陽能等，景氣循環性強、價格波動大，獲利與供需與報價連動緊密。"),
    "電腦及周邊": ("computer-peripherals", "電腦及周邊包含品牌與代工、伺服器、機殼與周邊裝置，受 PC/NB 與資料中心、AI 伺服器需求驅動。"),
    "電機機械": ("electrical-machinery", "電機機械涵蓋重電、自動化設備與機械零件，與基礎建設、製造業資本支出及電網升級需求相關。"),
    "通信網路": ("telecom", "通信網路包含電信營運、網通設備與基地台等，電信營運股相對穩健、網通股則受 5G 與資料中心題材帶動。"),
    "建材營造": ("construction", "建材營造涵蓋營建、建材與資產開發，與房市景氣、利率與公共工程連動，常具資產題材但循環性明顯。"),
    "綠能環保": ("green-energy", "綠能環保涵蓋太陽能、風電、儲能與環保處理，受政策補貼與能源轉型驅動，題材性強但獲利波動大。"),
    "觀光餐旅": ("tourism", "觀光餐旅包含旅遊、餐飲與飯店，與消費景氣、出入境人潮高度相關，旺淡季與事件衝擊明顯。"),
    "資訊服務": ("it-services", "資訊服務涵蓋系統整合、軟體與雲端服務，營收相對穩定、毛利較高，受數位轉型與資安需求帶動。"),
    "紡織": ("textile", "紡織涵蓋上游纖維到成衣代工，機能性布料與品牌代工為亮點，與消費景氣及原物料價格相關。"),
    "鋼鐵": ("steel", "鋼鐵屬景氣循環股，獲利隨鋼價與下游需求波動，與基礎建設、營建及全球製造業景氣連動。"),
    "化學": ("chemical", "化學涵蓋塑化原料、特用化學與材料，與油價、供需循環相關，部分公司具高股息特性。"),
    "數位雲端": ("cloud", "數位雲端涵蓋雲端服務、電商與數位平台，成長題材性高，需留意獲利能力與本夢比。"),
    "金融保險": ("finance", "金融保險涵蓋銀行、壽險、證券與金控，獲利與利率、股債市及景氣連動，多具穩定配息特性。"),
    "汽車": ("automotive", "汽車涵蓋整車、零組件與電動車供應鏈，受車市景氣、電動化趨勢與供應鏈轉移影響。"),
    "食品": ("food", "食品屬民生必需的防禦型類股，需求相對穩定，與原物料成本及消費通路布局相關。"),
    "電子通路": ("electronics-distribution", "電子通路為半導體與零組件的代理與通路商，營收規模大、毛利較薄，受終端需求與庫存循環影響。"),
    "居家生活": ("home-living", "居家生活涵蓋家具、家電與生活用品，與消費景氣、房市及通路布局相關。"),
    "航運": ("shipping", "航運包含貨櫃、散裝與空運，屬高度景氣循環股，運價波動劇烈、股價彈性大，需留意供需與運價指數。"),
    "運動休閒": ("sports-leisure", "運動休閒涵蓋自行車、運動用品與休閒器材，與消費趨勢、外銷訂單及健康意識相關。"),
    "文化創意": ("culture-creative", "文化創意涵蓋影視、出版、遊戲與內容，題材性強、獲利受作品週期影響，波動較大。"),
    "塑膠": ("plastics", "塑膠涵蓋塑化原料與加工製品，與油價、供需循環相關，龍頭多具規模與配息優勢。"),
    "電器電纜": ("electrical-cable", "電器電纜涵蓋電線電纜與家電，與電網建設、營建及銅價等原物料連動。"),
    "貿易百貨": ("trading-retail", "貿易百貨涵蓋零售通路與百貨量販，與消費景氣、來客與電商競爭相關。"),
    "油電燃氣": ("utilities", "油電燃氣屬公用事業型防禦股，現金流穩定、配息穩健，受能源價格與費率政策影響。"),
    "橡膠": ("rubber", "橡膠涵蓋輪胎與橡膠製品，與車市、原物料（天然/合成橡膠）價格及外銷需求相關。"),
    "水泥": ("cement", "水泥屬景氣循環的傳產類股，與營建、公共工程需求連動，龍頭多具高股息特性。"),
    "造紙": ("paper", "造紙涵蓋工業用紙與紙器，與紙價、原物料成本及電商包裝需求相關。"),
    "農業科技": ("agritech", "農業科技涵蓋飼料、水產與農業生技，與糧食需求、原物料價格及疫情/天候相關。"),
    "玻璃陶瓷": ("glass-ceramics", "玻璃陶瓷涵蓋玻璃、陶瓷與耐火材料，與營建、面板及工業需求相關。"),
}

LEVEL_COLOR = {"高": "#c0392b", "警示": "#c0392b", "中": "#e08e0b", "低": "#1a7a45"}


def load(name):
    p = DATA / name
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def risk_of(risk, code):
    return risk.get(str(code)) or risk.get(code) or {}


def render(cat, slug, intro, lst, risk):
    N = len(lst)
    listed = sum(1 for s in lst if s.get("status") == "上市")
    otc = sum(1 for s in lst if s.get("status") == "上櫃")
    emerg = sum(1 for s in lst if s.get("status") == "興櫃")
    up = sum(1 for s in lst if (s.get("change") or 0) > 0)
    down = sum(1 for s in lst if (s.get("change") or 0) < 0)
    flat = N - up - down
    watch = sum(1 for s in lst if risk_of(risk, s.get("code")).get("level") in ("中", "高", "警示"))

    order = {"高": 0, "警示": 0, "中": 1, "低": 3}
    lst_sorted = sorted(
        lst,
        key=lambda s: (order.get(risk_of(risk, s.get("code")).get("level"), 2), str(s.get("code")))
    )

    rows = []
    for s in lst_sorted:
        code = escape(str(s.get("code", "")))
        name = escape(str(s.get("name", "")))
        mkt = escape(str(s.get("status", "")))
        r = risk_of(risk, s.get("code"))
        level = r.get("level")
        reason = (r.get("reasons") or [""])[0] if r.get("reasons") else ""
        if level and level != "低":
            badge = (f'<span class="ind-lv" style="background:{LEVEL_COLOR.get(level, "#888")};">'
                     f'{escape(level)}</span>')
            rtext = f'<div class="ind-reason">{escape(reason)}</div>' if reason else ""
        elif level == "低":
            badge = '<span class="ind-lv-low">低</span>'
            rtext = ""
        else:
            badge = '<span class="ind-na">—</span>'
            rtext = ""
        rows.append(
            f'<tr><td><a href="/stock/{code}">{code}</a></td>'
            f'<td><a href="/stock/{code}">{name}</a></td>'
            f'<td class="c">{mkt}</td>'
            f'<td>{badge}{rtext}</td></tr>'
        )
    rows_html = "\n".join(rows)

    title = f"{cat}類股一覽：成分股 + 風險檢查（{N} 檔）- 領富 AI"
    desc = (f"領富 AI 整理台股「{cat}」類股共 {N} 檔（上市 {listed}、上櫃 {otc}、興櫃 {emerg}），"
            f"含成分股清單、風險等級與注意股檢查。資料來源 TWSE 證交所、TPEx 櫃買中心，每日更新。")
    url = f"{BASE}/pages/industries/{slug}"
    kw = f"{cat},{cat}類股,{cat}個股,{cat}成分股,台股{cat},{cat}風險,{cat}注意股"

    jsonld = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "CollectionPage",
                "@id": f"{url}#page",
                "name": f"{cat}類股一覽",
                "description": desc,
                "url": url,
                "isPartOf": {"@id": f"{BASE}/#website"},
                "about": cat,
                "dateModified": TODAY,
                "publisher": {"@id": f"{BASE}/#organization"},
                "inLanguage": "zh-TW",
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "首頁", "item": f"{BASE}/"},
                    {"@type": "ListItem", "position": 2, "name": "產業分類", "item": f"{BASE}/pages/industries"},
                    {"@type": "ListItem", "position": 3, "name": f"{cat}類股"},
                ],
            },
        ],
    }
    jsonld_str = json.dumps(jsonld, ensure_ascii=False, indent=2)

    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{escape(title)}</title>
<meta name="description" content="{escape(desc)}">
<meta name="keywords" content="{escape(kw)}">
<link rel="canonical" href="{url}">
<meta property="og:title" content="{escape(cat)}類股一覽：成分股 + 風險檢查">
<meta property="og:description" content="{escape(desc)}">
<meta property="og:type" content="website">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{BASE}/icons/icon-512.png">
<meta name="theme-color" content="#1B4332">
<link rel="icon" type="image/svg+xml" href="../../icons/icon.svg">
<script type="application/ld+json">
{jsonld_str}
</script>
<link rel="stylesheet" href="../../css/style.css?v={CSS_V}">
<style>
  .ind-wrap {{ max-width: 900px; margin: 0 auto; padding: 18px 12px 50px; }}
  .ind-intro {{ font-size: 15px; color: #444; line-height: 1.8; margin: 6px 0 18px; }}
  .ind-stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin: 16px 0 22px; }}
  .ind-stat {{ background: #f7faf8; border: 1px solid #e8ece9; border-radius: 14px; padding: 16px 12px; text-align: center; }}
  .ind-stat b {{ display: block; font-size: 26px; font-weight: 800; color: #1B4332; line-height: 1.1; font-variant-numeric: tabular-nums; }}
  .ind-stat span {{ display: block; font-size: 13px; color: #555; margin-top: 6px; }}
  .ind-stat.warn b {{ color: #c0392b; }}
  .ind-table {{ width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #e8ece9; border-radius: 12px; overflow: hidden; font-size: 14px; }}
  .ind-table th {{ background: #f2f6f3; text-align: left; padding: 11px 12px; font-weight: 700; color: #1B4332; font-size: 13px; }}
  .ind-table td {{ padding: 10px 12px; border-top: 1px solid #f0f2f1; }}
  .ind-table td.c {{ text-align: center; color: #666; }}
  .ind-table a {{ color: #1B4332; font-weight: 600; text-decoration: none; }}
  .ind-table a:hover {{ text-decoration: underline; }}
  .ind-lv {{ color: #fff; padding: 2px 9px; border-radius: 10px; font-size: 12px; font-weight: 700; }}
  .ind-lv-low {{ color: #1a7a45; font-size: 12px; }}
  .ind-na {{ color: #bbb; font-size: 12px; }}
  .ind-reason {{ font-size: 11.5px; color: #999; margin-top: 3px; }}
  .ind-src {{ font-size: 12.5px; color: #888; margin: 16px 0; }}
  .ind-disc {{ background: #fdf6ec; border: 1px solid #f0e2c8; border-radius: 12px; padding: 14px 16px; font-size: 13px; color: #7a6a4a; line-height: 1.7; margin-top: 22px; }}
  .ind-tools {{ display: flex; flex-wrap: wrap; gap: 10px; margin: 18px 0; }}
  .ind-tools a {{ background: #eef7f1; color: #1B4332; padding: 9px 16px; border-radius: 999px; text-decoration: none; font-size: 14px; font-weight: 600; }}
  .ind-tools a:hover {{ background: #e0efe6; }}
</style>
</head>
<body>

<header class="top-bar">
  <div class="container top-bar-inner">
    <div class="top-left"><span id="todayDate"></span><span class="divider">|</span><span>台股全市場財經資訊網</span></div>
    <div class="top-right"><a href="../login.html">會員登入</a><a href="../register.html">免費註冊</a><a href="https://line.me/R/ti/p/@130tqckv" class="line-cta" target="_blank" rel="noopener">LINE 客服</a></div>
  </div>
</header>

<div class="logo-bar">
  <div class="container logo-bar-inner">
    <a href="../../index.html" class="logo">
      <span class="logo-bi">領富</span><span class="logo-ai">AI</span>
      <span class="logo-sub">LeadFu · 領先市場兩步</span>
    </a>
    <div class="search-box">
      <input type="text" id="stockSearch" placeholder="輸入代號 / 公司名稱">
      <button id="searchBtn">查詢</button>
    </div>
  </div>
</div>

<nav class="main-nav">
  <div class="container">
    <ul>
      <li><a href="../../index.html">首頁</a></li>
      <li><a href="../stocks.html">股價總覽</a></li>
      <li><a href="../industries.html">產業分類</a></li>
      <li><a href="../risk-radar.html">防錯雷達</a></li>
      <li><a href="../learn.html"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:-2px;margin-right:4px;"><path d="M6 3h14v18H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z"/><path d="M20 17H6a2 2 0 0 0-2 2"/></svg>學習中心</a></li>
      <li><a href="../ai.html">AI 對話</a></li>
    </ul>
  </div>
</nav>

<main class="ind-wrap">
  <div class="article-breadcrumb" style="font-size:13px;color:#888;margin-bottom:10px;">
    <a href="../../index.html" style="color:#1B4332;">首頁</a> ▸
    <a href="../industries.html" style="color:#1B4332;">產業分類</a> ▸
    <span>{escape(cat)}類股</span>
  </div>

  <h1 style="font-size:26px;color:#1B4332;margin:0 0 4px;">「{escape(cat)}」類股一覽</h1>
  <p class="ind-intro">{escape(intro)} 領富 AI 整理「{escape(cat)}」類股共 <strong>{N}</strong> 檔，提供成分股清單與每日風險檢查，協助你快速掌握這個產業的全貌與需注意的個股。</p>

  <div class="ind-stats">
    <div class="ind-stat"><b>{N}</b><span>類股檔數</span></div>
    <div class="ind-stat"><b style="font-size:18px;line-height:1.5;">上市 {listed}<br>上櫃 {otc}・興櫃 {emerg}</b><span>市場別分布</span></div>
    <div class="ind-stat"><b style="font-size:18px;line-height:1.5;">▲ {up}　▼ {down}</b><span>當日漲跌家數（持平 {flat}）</span></div>
    <div class="ind-stat warn"><b>{watch}</b><span>需注意股（中/高風險）</span></div>
  </div>

  <div class="ind-tools">
    <a href="../check.html"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:-2px;margin-right:4px;"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>個股買前檢查</a>
    <a href="../risk-radar.html"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:-2px;margin-right:4px;"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4"/><path d="m15 9 4.5-4.5"/></svg>防錯雷達</a>
    <a href="../learn/warning-stocks.html"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:-2px;margin-right:4px;"><path d="M12 6c-2-1.4-4.8-2-8-2v14c3.2 0 6 .6 8 2 2-1.4 4.8-2 8-2V4c-3.2 0-6 .6-8 2z"/><path d="M12 6v14"/></svg>注意股是什麼</a>
  </div>

  <h2 style="font-size:19px;color:#1B4332;margin:24px 0 10px;">{escape(cat)}成分股清單</h2>
  <div class="ind-src"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:-2px;margin-right:4px;"><rect x="4" y="5" width="16" height="16" rx="2"/><path d="M8 3v4M16 3v4M4 11h16"/></svg>更新日期：{TODAY}　·　資料來源：TWSE 證交所、TPEx 櫃買中心、MOPS 公開資訊觀測站（風險等級為領富 AI 依公開資料整理）</div>
  <table class="ind-table">
    <thead><tr><th>代號</th><th>名稱</th><th class="c">市場</th><th>風險等級</th></tr></thead>
    <tbody>
{rows_html}
    </tbody>
  </table>

  <div class="ind-disc">
    <strong><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:-2px;margin-right:4px;"><path d="M12 16v5"/><path d="M9 3h6l1 7 2 3H6l2-3z"/></svg>免責聲明</strong><br>
    本頁為「{escape(cat)}」類股之公開資料整理，僅供研究參考，<strong>不構成任何個股推薦或買賣建議</strong>。
    風險等級依公開資料以系統化方式整理，非投資評等；個股實際狀況請以證交所、櫃買中心與公開資訊觀測站之公告為準。
    投資有風險，決定前請您自行評估或諮詢合法之證券投資顧問。
  </div>
</main>

<footer class="site-footer">
  <div class="copyright"><div class="container">© 2026 領富 AI. All rights reserved. · 本網站所有資訊僅供參考，不構成投資建議。</div></div>
</footer>

<script src="../../js/main.js?v={JS_V}"></script>
</body>
</html>
"""


def main():
    sd = load("stocks_live.json") or {}
    stocks = sd.get("stocks", [])
    risk = (load("risk_score_live.json") or {}).get("data", {}) or {}

    by = {}
    for s in stocks:
        by.setdefault(s.get("category") or "其他", []).append(s)

    OUT.mkdir(parents=True, exist_ok=True)
    made = []
    for cat, lst in by.items():
        if cat not in INDUSTRY:
            continue
        slug, intro = INDUSTRY[cat]
        (OUT / f"{slug}.html").write_text(render(cat, slug, intro, lst, risk), encoding="utf-8")
        made.append((cat, slug, len(lst)))

    print(f"✅ 產業頁產生 {len(made)} 頁：")
    for cat, slug, n in made:
        print(f"  /pages/industries/{slug}  ←  {cat}（{n} 檔）")

    # 更新 industries.html 的「全部產業」靜態連結區塊（爬蟲不需 JS 即可抓到，內部連結）
    hub = ROOT / "pages" / "industries.html"
    if hub.exists():
        links = "\n".join(
            f'      <a href="industries/{slug}.html" style="background:#eef7f1;color:#1B4332;'
            f'padding:8px 14px;border-radius:999px;text-decoration:none;font-size:14px;font-weight:600;">'
            f'{cat}（{n}）</a>'
            for cat, slug, n in sorted(made, key=lambda x: -x[2])
        )
        html = hub.read_text(encoding="utf-8")
        new = re.sub(
            r"(<!-- IND-LINKS-START -->).*?(<!-- IND-LINKS-END -->)",
            lambda m: f"{m.group(1)}\n{links}\n      {m.group(2)}",
            html, flags=re.S,
        )
        if new != html:
            hub.write_text(new, encoding="utf-8")
            print("  → 已更新 industries.html「全部產業」連結區塊")


if __name__ == "__main__":
    main()
