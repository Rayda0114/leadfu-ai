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

# 同目錄模組：自選股「今日異動」警示偵測（直接執行 python scripts/xxx.py 時
# scripts/ 會在 sys.path[0]，故可直接 import）
from watchlist_alerts import load_alert_data, alerts_for_codes

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
           "?select=id,name,watchlist,line_user_id,push_optin"
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


def build_digest(codes, code2name, anns_today, news, alerts):
    """為單一會員組出推播文字；沒有相關內容回 None。
    alerts: {code: [警示字串,...]}，只含該會員自選股中有今日異動的股。"""
    codeset = set(codes)
    names = [code2name.get(c, "") for c in codes if code2name.get(c)]

    my_ann = [a for a in anns_today if a.get("code") in codeset][:MAX_ANN]
    my_news = [n for n in news
               if any(nm and nm in n.get("title", "") for nm in names)][:MAX_NEWS]

    if not alerts and not my_ann and not my_news:
        return None

    lines = ["📊 領富 AI ・ 今日自選股快訊", ""]
    if alerts:
        lines.append("⚠️ 今日異動")
        for c in codes:  # 依會員自選股原順序列出
            if c in alerts:
                nm = code2name.get(c, "")
                for a in alerts[c]:
                    lines.append(f"・{c} {nm}｜{a}")
        lines.append("")
    if my_ann:
        lines.append("📢 公司公告")
        for a in my_ann:
            title = a.get("title", "").replace("\r", " ").replace("\n", " ").strip()[:40]
            lines.append(f"・{a.get('code')} {a.get('name', '')}：{title}")
        lines.append("")
    if my_news:
        lines.append("📰 相關新聞")
        for n in my_news:
            lines.append(f"・{n.get('title', '').strip()[:42]}")
        lines.append("")
    # openExternalBrowser=1：讓 LINE 用手機預設瀏覽器開（跳出 LINE 內建瀏覽器，
    # 才帶得到登入 session、看得到雲端自選股；否則 LINE webview 未登入會顯示空清單）
    lines.append(f"🔗 我的自選股：{SITE}/pages/watchlist?openExternalBrowser=1")
    lines.append("")
    lines.append("※ 以上為公開資訊整理，非投資建議。")
    lines.append("如不想再收到，可至領富 AI 會員中心關閉推播通知。")
    return "\n".join(lines)[:4900]  # LINE 單則文字上限約 5000 字


def main():
    anns = load_json("announcements_live.json").get("announcements", [])
    news = load_json("news_live.json").get("news", [])
    stocks = load_json("stocks_live.json").get("stocks", [])
    code2name = {s["code"]: s.get("name", "") for s in stocks if s.get("code")}

    # 只取最新一天的公告（避免推到舊公告）
    latest = max((a.get("date", "") for a in anns), default="")
    anns_today = [a for a in anns if a.get("date") == latest] if latest else anns
    print(f"[info] 公告基準日 {latest}，當日公告 {len(anns_today)} 筆；新聞 {len(news)} 則")

    # 自選股「今日異動」警示資料（klines/指標/法人），整批只載一次
    alert_data = load_alert_data()
    print(f"[info] 警示資料：klines {len(alert_data['kl'])}、指標 {len(alert_data['ind'])}、法人 {len(alert_data['inst'])}")

    members = fetch_members()
    print(f"[info] 可推播會員 {len(members)} 位（已登入 LINE + 未退訂）")

    sent = skipped = 0
    for m in members:
        codes = m.get("watchlist") or []
        if not codes:
            skipped += 1
            continue
        alerts = alerts_for_codes(codes, alert_data)
        text = build_digest(codes, code2name, anns_today, news, alerts)
        if not text:
            skipped += 1
            continue
        if push_message(m["line_user_id"], text):
            sent += 1
        time.sleep(0.1)  # 輕微節流

    print(f"[done] 推播 {sent} 位；無相關內容/無自選股略過 {skipped} 位")


if __name__ == "__main__":
    main()
