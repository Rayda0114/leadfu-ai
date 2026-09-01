#!/usr/bin/env python3
"""每日為個股頁生成「常青深度問答」內容。

為什麼要有這支
--------------
原本的每日發文靠一支本機排程（leadfu-daily-xuanti-brief）：早上 08:04 在
Rayda 的 Mac 上跑 xuanti 選題、做網路研究、再 POST 進後台。實測 2026-06-22
建立以來 51 個交易日只產出 5 篇草稿（產出率 10%）——因為它要求筆電開著、
Claude Code 在跑、能上網、讀得到金鑰，任一條不成立當天就沒稿。而那 5 篇裡
又有 2 篇被把關擋下，因為「今日熱門題材／族群輪動」這種內容天然帶推介語氣，
跟安全閘在設計上就是衝突的。

這支改成三件事都不一樣：
  1. 跑在 GitHub Actions（每交易日 07:00 UTC，跟本機無關，穩定）
  2. 只用站上既有的結構化資料，不做外部新聞研究 → 不會產生推介語氣
  3. 不開新網址，內容掛在既有的 /stock/{code} 上

為什麼不開新頁
--------------
GSC 實測：2,551 個個股頁只有 286 頁（11%）拿到搜尋曝光。剩下 2,265 頁不是
沒有需求——「{股名}目標價／合理價」405 個查詢佔全站 24% 點擊——是頁面內容
太薄排不上去。所以要做的是把既有頁面做厚，不是再加一批新的薄頁面
（2026-08-30 才花一整天在清 2.5 萬個垃圾網址，不該再製造）。

輸出
----
  data/stock_insight.json   { code: {sections:[{h,body}], generated_at, model} }

安全
----
  沿用 worker.js 的 L1 禁用詞（擋「行為」不是擋「詞彙」，見該檔註解），
  生成後逐段檢查，違規就整檔跳過不寫入——寧可少一檔，不可寫出推介語氣。
"""

import json
import os
import re
import ssl
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _guard import guard_count, notify_owner   # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = DATA / "stock_insight.json"
ASK_URL = os.environ.get("ASK_URL", "https://leadfuai.com/api/ask")
PER_RUN = int(os.environ.get("INSIGHT_PER_RUN", "3"))   # 每次跑幾檔
_CTX = ssl.create_default_context()

# 與 worker.js 的 INSIGHT_L1_PATTERNS 對齊：擋「行為」不擋「詞彙」。
# 這裡是最後一道，生成後逐段檢查。
L1 = [
    (re.compile(r"目標價[^。；\n]{0,14}?\d+(\.\d+)?\s*元"), "印出具體目標價"),
    (re.compile(r"(上看|喊到|挑戰至|直指)\s*\d+(\.\d+)?\s*元"), "喊出價位"),
    (re.compile(r"(保證獲利|穩賺不賠|穩賺|包賺|報酬保證|保證賺錢|保證賺|必賺)"), "報酬承諾"),
    (re.compile(r"(建議買進|建議賣出|建議加碼|建議減碼|買進訊號|賣出訊號|可以買進|可以賣出)"), "買賣建議"),
    (re.compile(r"(逢低布局|逢低承接|進場時機|出場時機|大膽買|勇敢買|閉著眼睛買|All ?in)", re.I), "進出場指示"),
    (re.compile(r"(值得買|不妨留意|建議關注)"), "變相推介"),
    (re.compile(r"(飆股|噴出|起漲點|主力吃貨|內線|明牌|報明牌)"), "炒作用語"),
    (re.compile(r"(一定會漲|一定會跌|必漲|必跌|穩漲|鐵定)"), "絕對化預測"),
    # 以下比 worker.js 的 L1 更嚴：那邊的稿子還有 L3 與站長把關，這裡是全自動
    # 直接上線，沒有人看過，所以評價性用語要在這一關就擋掉。
    # 實例：第一次試跑產出「本益比 9.54 屬於相對低估」「殖利率 6.66% 對尋求
    # 現金流的投資人具吸引力」——都不是明講買賣，但已經是在替讀者下判斷。
    (re.compile(r"(具|有|富)吸引力|很吸引人"), "評價性用語（吸引力）"),
    (re.compile(r"(相對|明顯|嚴重|偏)低估|物超所值|很划算|價格便宜"), "評價性用語（低估）"),
    (re.compile(r"(適合|推薦給)[^。；\n]{0,10}(投資人|存股|新手)"), "替讀者選標的"),
]


def l1_check(text):
    return [f"{label}（「{m.group(0)}」）" for rx, label in L1 for m in [rx.search(text or "")] if m]


def load(name, key=None):
    try:
        d = json.loads((DATA / name).read_text(encoding="utf-8"))
    except Exception:
        return {}
    if key:
        return d.get(key) or {}
    return d.get("data", d) or {}


def ask(prompt, max_tokens=2000, retries=3):
    # mode:"article" → worker 換成不含聊天排版的系統提示詞（合規護欄不變）。
    # 沒有這個的話，聊天人設會把「💎 領富 AI 合理區間 / 訊號強度 ⭐⭐⭐」卡片
    # 直接塞進正文（實測 1101 就是這樣）。
    body = json.dumps({"question": prompt, "mode": "article",
                       "max_tokens": max_tokens, "stream": False}).encode("utf-8")
    for i in range(retries):
        try:
            req = urllib.request.Request(ASK_URL, data=body, method="POST", headers={
                "Content-Type": "application/json",
                "User-Agent": "LeadFuStockInsight/1.0",
            })
            with urllib.request.urlopen(req, timeout=150, context=_CTX) as r:
                d = json.loads(r.read().decode("utf-8"))
            a = (d.get("answer") or d.get("text") or "").strip()
            if a:
                return a
        except Exception as e:
            print(f"    ask 失敗（{i + 1}/{retries}）：{str(e)[:90]}")
        time.sleep(4 * (i + 1))
    return ""


def build_facts(code, S):
    """把站上既有的結構化資料整理成「只能用這些」的事實清單。
    模型只准根據這裡的數字寫，不准自己補——這是防捏造的關鍵。"""
    s = S["stocks"].get(code) or {}
    co = S["companies"].get(code) or {}
    fv = S["fv"].get(code) or {}
    rk = S["risk"].get(code) or S["risk_all"].get(code) or {}
    rev = S["rev"].get(code) or {}
    val = S["val"].get(code) or {}
    att = S["att"].get(code)

    f = [f"股票代號：{code}", f"公司簡稱：{s.get('name', '')}"]
    if co.get("name"):
        f.append(f"公司全名：{co['name']}")
    if s.get("status"):
        f.append(f"交易市場：{s['status']}")
    if s.get("category"):
        f.append(f"產業類別：{s['category']}")
    if co.get("founded"):
        f.append(f"成立日期：{co['founded']}")
    if co.get("capital"):
        f.append(f"實收資本額：{co['capital']}")
    if co.get("chairman"):
        f.append(f"董事長：{co['chairman']}")
    if s.get("price") is not None:
        f.append(f"參考股價（每日更新，非即時）：{s['price']} 元")
    if fv.get("low") is not None and fv.get("high") is not None:
        f.append(f"領富 AI 合理股價區間：{fv['low']}–{fv['high']} 元（依公開財報推算，非目標價）")
        if fv.get("label"):
            f.append(f"目前價位相對合理區間：{fv['label']}")
    if rk.get("score") is not None:
        f.append(f"領富 AI 風險分數：{rk['score']}/100（等級「{rk.get('level', '')}」，分數越高風險越高）")
    if rk.get("reasons"):
        f.append("風險觀察項目：" + "、".join(rk["reasons"][:4]))
    f.append("注意股／處置股狀態：" + ("目前列入" if att else "目前未列入"))
    if val.get("pe_ratio"):
        f.append(f"本益比：{val['pe_ratio']}")
    if val.get("yield_pct"):
        f.append(f"殖利率：{val['yield_pct']}%")
    if val.get("pb_ratio"):
        f.append(f"股價淨值比：{val['pb_ratio']}")
    if rev.get("period"):
        f.append(f"最新月營收期間：{rev['period']}")
    if rev.get("monthRevenueFmt"):
        f.append(f"當月營收：{rev['monthRevenueFmt']}")
    if isinstance(rev.get("yoy"), (int, float)):
        f.append(f"月營收年增率：{rev['yoy']}%")
    if isinstance(rev.get("mom"), (int, float)):
        f.append(f"月營收月增率：{rev['mom']}%")
    return f


PROMPT = """你是台灣財經資料整理員，任務是把「公開資料」整理成一般散戶看得懂的說明。

【本檔的核心事實】
{facts}

（註：系統可能另外提供本站的其他公開欄位，例如集保股權分散、股利紀錄等，
那些也可以用；但除此之外不得引用任何站外資訊，也不得自行推估或預測。）

【硬性規則，違反就是失敗】
1. 不做任何買賣建議、不推介、不預測股價。
2. 不寫出任何具體目標價價位。可以說明「本站不喊目標價、改用合理區間」。
3. 只能用系統提供的本站公開資料。不得引用站外資訊、不得自行推估或預測數字。
4. 不用「值得買、建議關注、不妨留意、飆股、起漲點、逢低、保證、一定會」這類字眼。
5. **不要替讀者下價值判斷**。可以說「本益比 9.5 代表每賺 1 元需要 9.5 元股價」，
   不可以說「屬於相對低估」「具吸引力」「適合存股族」——解釋數字的意思，
   不評價好壞，好壞由讀者自己判斷。
6. 語氣中性、面向 45-75 歲不熟股市的讀者，把專有名詞用白話解釋。
7. 不要加免責聲明、不要寫資料時間——頁面本身已經有了，重複會很冗。

【要寫的四段，每段用這個格式】
### 標題
內文（150-260 字）

四段的標題固定為：
### 這家公司在做什麼
### 這些數字怎麼看
### 買之前該留意什麼
### 為什麼我們不給目標價

「這些數字怎麼看」要挑清單裡真的有的欄位講，並解釋那個數字代表什麼意思
（例如本益比高低代表什麼），不要只是把數字念一遍。
「買之前該留意什麼」要根據風險項目與注意股狀態具體說明，沒有風險項目就
說明「目前未觸發警示」代表什麼、不代表什麼。
「為什麼我們不給目標價」要說明目標價常因人而異、時常失準，本站改用依公開
財報推算的合理區間，並提醒合理區間也只是參考、不是預測。

只輸出這四段，不要開場白、不要結語、不要免責聲明（頁面另有）。"""


def parse_sections(text):
    """把模型輸出切成 [{h, body}]。格式不對就回空 → 視為失敗，不寫入。"""
    out = []
    for blk in re.split(r"\n(?=###\s)", text or ""):
        m = re.match(r"###\s*(.+?)\n(.+)", blk.strip(), re.S)
        if not m:
            continue
        h = m.group(1).strip()
        body = re.sub(r"\n{2,}", "\n", m.group(2).strip())
        # 模型常無視「不要加免責聲明」的指示自己補一段（頁面本身已有，會重複）。
        # 提示詞管不住的東西就用後處理砍掉，比再加一句指示可靠。
        body = re.sub(r"\s*(資料時間|更新時間)[：:][^\n]*", "", body)
        body = re.sub(r"\s*[※*]\s*(以上|本文|本頁)[^\n]*", "", body)
        body = re.sub(r"\s*（?本(文|頁|內容)[^）\n]{0,40}(投資建議|參考)[^\n]*", "", body).strip()
        # 生成被 max_tokens 截斷時，最後一段會斷在句子中間（實測 1101 收在
        # 「區間僅基於歷」）。與其整檔重試，不如切回最後一個完整句子——
        # 前面的內容本來就是好的，沒必要丟掉重花一次 API。
        if body and body[-1] not in "。！？」）":
            cut = max(body.rfind(c) for c in "。！？")
            body = body[:cut + 1] if cut > 40 else ""
        if len(body) >= 60:
            out.append({"h": h, "body": body})
    return out


def main():
    print(f"[{datetime.now():%H:%M:%S}] 生成個股常青內容（每次 {PER_RUN} 檔）")
    stocks_raw = json.loads((DATA / "stocks_live.json").read_text(encoding="utf-8")).get("stocks", [])
    S = {
        "stocks": {s["code"]: s for s in stocks_raw if s.get("code")},
        "companies": load("companies_live.json", "companies"),
        "fv": load("fair_value_live.json"),
        "risk": load("risk_score_live.json"),
        "risk_all": load("risk_score_all.json"),
        "rev": load("revenue_live.json", "revenue"),
        "val": load("valuation_live.json"),
        "att": load("attention_live.json"),
    }
    try:
        existing = json.loads(OUT.read_text(encoding="utf-8"))
        done = existing.get("data", {})
    except Exception:
        existing, done = {}, {}
    print(f"  已有內容：{len(done)} 檔")

    # 挑選：還沒做過、且資料夠厚（至少要有合理區間，否則寫不出「這些數字怎麼看」）。
    # 依資料完整度排序，先做能寫得最紮實的——那些也最可能排得上去。
    def richness(code):
        return sum([
            2 if S["fv"].get(code) else 0,
            1 if (S["risk"].get(code) or S["risk_all"].get(code)) else 0,
            1 if S["rev"].get(code) else 0,
            1 if S["val"].get(code) else 0,
            1 if S["companies"].get(code) else 0,
        ])

    pool = [c for c in S["stocks"] if c not in done and S["fv"].get(c)]
    pool.sort(key=lambda c: (-richness(c), c))
    if not pool:
        print("  沒有待處理的個股（可能全部做完了）")
        return
    print(f"  待處理池：{len(pool)} 檔，目標產出 {PER_RUN} 檔")

    def try_one(code):
        """單檔生成。失敗時把「違規了什麼」回饋給模型再試一次——
        第一版沒有重試，實測成功率只有 1/3（模型常無視提示詞寫出評價性用語、
        或少寫一段），那撐不起「每天穩定產出」。把具體違規講給它聽通常一次就對。"""
        facts = "\n".join(f"- {x}" for x in build_facts(code, S))
        feedback = ""
        for attempt in (1, 2):
            text = ask(PROMPT.format(facts=facts) + feedback)
            if not text:
                return None, "AI 無回應"
            secs = parse_sections(text)
            if len(secs) < 3:
                feedback = (f"\n\n【上一次你只寫了 {len(secs)} 段，格式不對】"
                            "請務必輸出四段，每段開頭是「### 」加上指定標題，"
                            "標題和內文之間要換行，內文至少 150 字。")
                print(f"    ↻ 第 {attempt} 次格式不符（{len(secs)} 段），回饋後重試")
                continue
            hits = l1_check("\n".join(x["h"] + x["body"] for x in secs))
            if hits:
                feedback = ("\n\n【上一次違規，請重寫】你寫了：" + "、".join(hits) +
                            "。這是在替讀者下價值判斷。請只解釋數字代表什麼意思，"
                            "不要評價好壞、不要說適合誰。")
                print(f"    ↻ 第 {attempt} 次 L1 擋下（{'、'.join(hits)}），回饋後重試")
                continue
            return secs, None
        return None, "重試兩次仍未通過"

    # 失敗就換下一檔，直到湊滿 PER_RUN——不然一檔失敗當天就少一篇，談不上「穩定」。
    added, skipped = {}, []
    budget = PER_RUN * 3     # 最多嘗試幾檔，避免上游壞掉時空轉
    for code in pool[:budget]:
        if len(added) >= PER_RUN:
            break
        name = (S["stocks"].get(code) or {}).get("name", code)
        print(f"\n  ── {code} {name} ──")
        secs, why = try_one(code)
        if why:
            skipped.append((code, why)); print(f"    ✗ {why}"); continue
        added[code] = {
            "sections": secs,
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        }
        print(f"    ✓ {len(secs)} 段、共 {sum(x['body'].__len__() for x in secs)} 字")

    if skipped:
        print("\n  跳過：")
        for c, why in skipped:
            print(f"    {c}  {why}")

    if not added:
        msg = f"個股常青內容：嘗試 {len(skipped)} 檔全部失敗，未寫入。" + \
              ("；".join(f"{c}={w}" for c, w in skipped[:3]))
        print(f"\n⚠ {msg}")
        notify_owner(f"【領富 AI】個股內容生成失敗\n\n{msg}\n\n站上內容不受影響（沿用既有）。")
        sys.exit(1)

    done.update(added)
    # 守門：只會越寫越多，總數變少代表讀檔或合併出錯
    guard_count("stock_insight.json", len(done), floor=max(1, len(existing.get("data", {}))),
                what="個股常青內容", drop_ratio=0.01)
    OUT.write_text(json.dumps({
        "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "note": "個股常青深度內容；依站上公開資料生成，經 L1 禁用詞檢查。渲染於 /stock/{code}",
        "count": len(done),
        "data": done,
    }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"\n✅ 新增 {len(added)} 檔，累計 {len(done)} 檔 → {OUT.name}")


if __name__ == "__main__":
    main()
