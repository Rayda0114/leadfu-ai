#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
push_watchlist_digest.py — 領富 AI 每日自選股推播（LINE Messaging API）

流程：讀 Supabase profiles 的會員自選股 → 比對「當日公告 + 相關新聞」→ 透過
LINE 官方帳號（領富 AI / @130tqckv，Messaging API）推播給該會員。

原則：
  - 只推給「已用 LINE 登入（line_user_id 有值）且未退訂（push_optin=true）」的會員。
  - 沒有相關內容就「不推」（不擾民）。
  - 內容僅為「公開資訊整理／通知」，不含買賣建議（守投顧法／證交法）。

需要環境變數（放 GitHub Actions secret 或執行環境 env，勿寫進 repo）：
  SUPABASE_URL                例：https://lhwxpnyzplylajxunlua.supabase.co
  SUPABASE_SERVICE_ROLE_KEY   service role key（後端用，繞過 RLS 讀全體 profiles）
  LINE_CHANNEL_ACCESS_TOKEN   LINE Messaging API 長期 channel access token
選用：
  DRY_RUN=1   只印出訊息、不實際呼叫 LINE（測試用）

用法：
  SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... LINE_CHANNEL_ACCESS_TOKEN=... \
      python3 scripts/push_watchlist_digest.py
  DRY_RUN=1 python3 scripts/push_watchlist_digest.py   # 不推、只印
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://lhwxpnyzplylajxunlua.supabase.co").rstrip("/")
SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
LINE_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
DRY_RUN = os.environ.get("DRY_RUN") == "1"
SITE = "https://leadfuai.com"

MAX_ANN = 6     # 每位會員最多列幾筆公告
MAX_NEWS = 5    # 每位會員最多列幾則新聞
LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"


def load_json(name):
    try:
        return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[warn] 讀 {name} 失敗: {e}")
        return {}


def fetch_members():
    """從 Supabase REST 讀可推播的會員（service role，繞過 RLS）。"""
    if not (SUPABASE_URL and SERVICE_KEY):
        print("[error] 缺 SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY，無法讀會員")
        sys.exit(1)
    url = (f"{SUPABASE_URL}/rest/v1/profiles"
           "?select=id,name,watchlist,holdings,line_user_id,push_optin"
           "&line_user_id=not.is.null&push_optin=eq.true")
    req = urllib.request.Request(url, headers={
        "apikey": SERVICE_KEY,
        "Authorization": f"Bearer {SERVICE_KEY}",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def push_message(to, text):
    """推播一則文字訊息給某位 LINE userId。回傳 True/False。"""
    if DRY_RUN:
        print(f"[dry-run] → {to}\n{text}\n{'-' * 40}")
        return True
    if not LINE_TOKEN:
        print("[error] 缺 LINE_CHANNEL_ACCESS_TOKEN")
        return False
    body = json.dumps({"to": to, "messages": [{"type": "text", "text": text}]}).encode("utf-8")
    req = urllib.request.Request(LINE_PUSH_URL, data=body, method="POST", headers={
        "Authorization": f"Bearer {LINE_TOKEN}",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return 200 <= r.status < 300
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "ignore")[:200]
        # 403/400 常見原因：該會員尚未加官方帳號好友 → 無法推播（正常，略過）
        print(f"[warn] 推播失敗 {to}: HTTP {e.code} {detail}")
        return False
    except Exception as e:
        print(f"[warn] 推播失敗 {to}: {e}")
        return False


def _names(codes, c2n, k=3):
    """把代碼列表轉成『2330 台積電、…』最多 k 檔，多的用『等N檔』。"""
    show = "、".join(f"{c} {c2n.get(c, '')}".strip() for c in codes[:k])
    return show + (f" 等{len(codes)}檔" if len(codes) > k else "")


def build_digest(codes, code2name, cat_of, anns_today, news, alerts, risk, attention, streak, revenue, fairvalue):
    """為單一會員組「每日我的風險摘要」；沒風險也沒公告/新聞回 None（不擾民）。
    codes: 該會員 自選∪持股 代碼；cat_of: code→產業；risk/attention/streak/revenue: 各風險資料。"""
    if not codes:
        return None
    codeset = set(codes)
    names = [code2name.get(c, "") for c in codes if code2name.get(c)]
    risk, attention, streak, revenue = risk or {}, attention or {}, streak or {}, revenue or {}

    # 各類風險訊號（該會員的股之中）
    notice = [c for c in codes if c in attention]
    sell = [c for c in codes if (streak.get(c) or {}).get("dir") == "sell" and (streak.get(c) or {}).get("days", 0) >= 2]
    revdrop = [c for c in codes if isinstance((revenue.get(c) or {}).get("yoy"), (int, float)) and revenue[c]["yoy"] <= -50]
    risky = sorted([(c, risk[c]) for c in codes if c in risk], key=lambda x: -x[1].get("score", 0))
    high = [c for c, r in risky if r.get("score", 0) >= 50]
    fairvalue = fairvalue or {}
    fvbreak = [c for c in codes
               if isinstance((fairvalue.get(c) or {}).get("low"), (int, float))
               and isinstance((fairvalue.get(c) or {}).get("price"), (int, float))
               and fairvalue[c]["price"] < fairvalue[c]["low"]]
    flagged = set(notice) | set(sell) | set(revdrop) | set(high) | set(fvbreak)

    # 產業集中度（以檔數計）
    cats = {}
    for c in codes:
        cat = cat_of.get(c)
        if cat:
            cats[cat] = cats.get(cat, 0) + 1
    top_cat, top_n = (max(cats.items(), key=lambda x: x[1]) if cats else ("", 0))
    conc = round(top_n / len(codes) * 100) if codes else 0

    my_ann = [a for a in anns_today if a.get("code") in codeset][:3]
    my_news = [n for n in news if any(nm and nm in n.get("title", "") for nm in names)][:2]

    # 完全沒風險、也沒公告/新聞 → 不推（避免天天報平安洗版）
    # 📅 未來 7 天除權息事件（提前算：只有事件也值得推）
    evs = []
    try:
        from datetime import datetime as _dtm, timedelta as _td
        _divd = (load_json("dividend_live.json") or {}).get("data", {})
        _today = _dtm.now().date()
        for _c in codes:
            _v = _divd.get(_c)
            if not _v or not _v.get("ex_date"):
                continue
            try:
                _ed = _dtm.strptime(_v["ex_date"], "%Y-%m-%d").date()
            except Exception:
                continue
            if _today <= _ed <= _today + _td(days=7):
                _cash = f"（每股 {_v['cash']} 元）" if _v.get("cash") else ""
                evs.append((_ed, f"・{_ed.month}/{_ed.day} {_c} {code2name.get(_c, '')} 除{_v.get('type', '息')}{_cash}"))
        evs.sort()
    except Exception:
        evs = []

    if not flagged and not my_ann and not my_news and not evs:
        return None

    lines = ["📋 領富 AI ・ 你的每日風險摘要", ""]
    lines.append(f"你追蹤的 {len(codes)} 檔，今天有 {len(flagged)} 檔出現風險訊號：")
    if fvbreak:
        lines.append(f"🔴 {len(fvbreak)} 檔跌破合理區間下緣：{_names(fvbreak, code2name)}")
    if notice:
        lines.append(f"⚠️ {len(notice)} 檔列注意/處置股：{_names(notice, code2name)}")
    if sell:
        lines.append(f"👥 {len(sell)} 檔外資連賣：{_names(sell, code2name)}")
    if revdrop:
        lines.append(f"📉 {len(revdrop)} 檔月營收年減 >50%：{_names(revdrop, code2name)}")
    if high:
        lines.append(f"🚨 {len(high)} 檔風險分數偏高(≥50)：{_names(high, code2name)}")
    if not flagged:
        lines.append("✓ 今天沒有明顯風險訊號。")

    if evs:
        lines.append("")
        lines.append("📅 未來 7 天：")
        for _, _s in evs:
            lines.append(_s)
    lines.append("")

    if top_cat and conc >= 40 and len(codes) >= 3:
        warn = "，集中度偏高、留意產業齊跌風險" if conc >= 50 else ""
        lines.append(f"🏭 你的部位集中在「{top_cat}」約 {conc}%{warn}。")
        lines.append("")

    if risky:
        top3 = "、".join(f"{c} {code2name.get(c, '')}".strip() for c, _ in risky[:3])
        lines.append(f"🔎 本週請優先檢查：{top3}")
        lines.append("（風險分數最高，建議重新確認當初的持有理由，非買賣建議）")
        lines.append("")

    if my_ann:
        lines.append("📢 相關公告：" + "；".join(f"{a.get('code')} {a.get('name', '')}".strip() for a in my_ann))
    if my_news:
        lines.append("📰 " + my_news[0].get("title", "").strip()[:38])
    if my_ann or my_news:
        lines.append("")

    # openExternalBrowser=1：用手機預設瀏覽器開（跳出 LINE webview，帶得到登入 session）
    lines.append(f"🔗 看完整風險：{SITE}/pages/risk-radar?openExternalBrowser=1")
    lines.append("※ 公開資料整理，非投資建議。可至會員中心關閉推播。")
    return "\n".join(lines)[:4900]


def main():
    anns = load_json("announcements_live.json").get("announcements", [])
    news = load_json("news_live.json").get("news", [])
    stocks = load_json("stocks_live.json").get("stocks", [])
    risk = load_json("risk_score_live.json").get("data", {})
    attention = load_json("attention_live.json").get("data", {})
    streak = load_json("inst_streak_live.json").get("data", {})
    revenue = load_json("revenue_live.json").get("revenue", {})
    fairvalue = load_json("fair_value_live.json").get("data", {})
    code2name = {s["code"]: s.get("name", "") for s in stocks if s.get("code")}
    cat_of = {s["code"]: s.get("category", "") for s in stocks if s.get("code")}

    # 只取最新一天的公告（避免推到舊公告）
    latest = max((a.get("date", "") for a in anns), default="")
    anns_today = [a for a in anns if a.get("date") == latest] if latest else anns
    print(f"[info] 公告基準日 {latest}，當日公告 {len(anns_today)} 筆；新聞 {len(news)} 則")
    print(f"[info] 風險 {len(risk)}、注意/處置 {len(attention)}、法人連買賣 {len(streak)} 筆")

    members = fetch_members()
    print(f"[info] 可推播會員 {len(members)} 位（已登入 LINE + 未退訂）")

    sent = skipped = 0
    for m in members:
        wl = m.get("watchlist") or []
        hold = list((m.get("holdings") or {}).keys())
        codes = list(dict.fromkeys(wl + hold))   # 自選 ∪ 持股，去重保序
        if not codes:
            skipped += 1
            continue
        text = build_digest(codes, code2name, cat_of, anns_today, news, None, risk, attention, streak, revenue, fairvalue)
        if not text:
            skipped += 1
            continue
        if push_message(m["line_user_id"], text):
            sent += 1
        time.sleep(0.1)  # 輕微節流

    print(f"[done] 推播 {sent} 位；無相關內容/無自選股略過 {skipped} 位")


if __name__ == "__main__":
    main()
