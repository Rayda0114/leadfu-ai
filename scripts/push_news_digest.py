#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
push_news_digest.py — 領富 AI 每日新聞推播（第一期，LINE Messaging API）

流程：讀 Supabase profiles.news_subs（會員勾選的主題 + active=true）→
比對「今日」news_live.json 中符合主題關鍵字的新聞 → 整理成 LINE 訊息推給該會員 →
回寫 news_subs.last_pushed（同一天不重推）。

第一期＝會員在網站「打勾選主題」即可；不含 AI 對話自動設定那層（第二期）。

原則：
  - 只推給「有 line_user_id」且 news_subs.active=true 且有勾主題的會員。
  - 只推「今日(date==今天)」的新聞；當天無相符新聞就不打擾。
  - 同一天已推過(last_pushed==今天)就跳過，避免重複。
  - 內容為公開新聞整理／通知，不含買賣建議（守投顧法／證交法）。

環境變數（放 GitHub Actions secret，勿寫進 repo）：
  SUPABASE_URL                例：https://lhwxpnyzplylajxunlua.supabase.co
  SUPABASE_SERVICE_ROLE_KEY   service role key（繞過 RLS 讀/寫全體 profiles）
  LINE_CHANNEL_ACCESS_TOKEN   LINE Messaging API channel access token
選用：
  DRY_RUN=1     只印、不推、不回寫（測試用）
  FAKE_SUBS=... JSON 陣列，模擬會員（測試用，不讀 Supabase）
"""
import json
import os
import re
import sys
import time
import datetime
import urllib.request
import urllib.error
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://lhwxpnyzplylajxunlua.supabase.co").rstrip("/")
SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
LINE_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
DRY_RUN = os.environ.get("DRY_RUN") == "1"
FAKE_SUBS = os.environ.get("FAKE_SUBS", "")
SITE = "https://leadfuai.com"
LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"
TODAY = datetime.date.today().isoformat()
MAX_PER_TOPIC = 5          # 每個主題最多列幾則
MAX_TOTAL = 15             # 整則訊息最多幾則（LINE 4900 字上限保險）

# 主題 → 關鍵字（與前端 news.html 訂閱面板的主題一致）。
# 中文用子字串比對；純英文縮寫用詞邊界比對（避免 AI 配到 "available" 之類）。
TOPICS = {
    "半導體":       ["半導體", "晶圓", "晶片", "台積電", "聯電", "封測", "日月光", "聯發科", "記憶體", "IC", "矽智財"],
    "AI 人工智慧":  ["人工智慧", "輝達", "NVIDIA", "算力", "伺服器", "資料中心", "生成式", "大模型", "GPU", "AI"],
    "電動車":       ["電動車", "特斯拉", "Tesla", "電池", "充電樁", "鋰電", "車用", "EV"],
    "蘋果供應鏈":   ["蘋果", "Apple", "iPhone", "鴻海", "大立光", "和碩", "可成", "iPad"],
    "金融":         ["金控", "銀行", "升息", "降息", "央行", "壽險", "利率", "金融股", "Fed"],
    "生技醫療":     ["生技", "醫療", "新藥", "製藥", "疫苗", "醫材", "保健食品", "臨床"],
    "航運":         ["航運", "貨櫃", "長榮", "陽明", "萬海", "散裝", "運價", "海運", "空運", "BDI"],
    "綠能重電":     ["綠能", "重電", "太陽能", "風電", "電網", "儲能", "台電", "光電", "再生能源"],
    "軍工航太":     ["軍工", "國防", "航太", "無人機", "衛星", "低軌"],
    "台股大盤":     ["大盤", "台股", "加權指數", "外資", "盤勢", "成交量", "期貨"],
}


def _is_ascii_kw(kw):
    return bool(re.search(r"[A-Za-z]", kw)) and not re.search(r"[一-鿿]", kw)


def kw_in(hay, kw):
    if _is_ascii_kw(kw):
        return re.search(r"(?<![A-Za-z])" + re.escape(kw) + r"(?![A-Za-z])", hay, re.I) is not None
    return kw in hay


def topic_match(item, topic):
    """該新聞是否屬於此主題：標題/摘要/分類/AI註記/關聯個股 任一含關鍵字。"""
    related = item.get("ai_related") or "[]"
    if isinstance(related, str):
        try:
            related = json.loads(related)
        except Exception:
            related = []
    hay = " ".join(str(x) for x in [
        item.get("title", ""), item.get("summary", ""), item.get("tag", ""),
        item.get("ai_note", ""), " ".join(str(r) for r in (related or [])),
    ])
    return any(kw_in(hay, kw) for kw in TOPICS.get(topic, []))


def load_news():
    try:
        nj = json.loads((DATA_DIR / "news_live.json").read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[error] 讀 news_live.json 失敗: {e}")
        return []
    items = nj.get("news") or nj.get("data") or nj.get("articles") or []
    # 只取今天的新聞（date 形如 2026-06-05）
    today_items = [n for n in items if str(n.get("date", "")).strip() == TODAY]
    return today_items


def build_digest(name, topics, news):
    """回傳 (訊息文字 or None)。為該會員勾選的主題挑今日相符新聞。"""
    blocks, total = [], 0
    for topic in topics:
        if topic not in TOPICS or total >= MAX_TOTAL:
            continue
        hits = [n for n in news if topic_match(n, topic)]
        if not hits:
            continue
        lines = [f"【{topic}】"]
        for n in hits[:MAX_PER_TOPIC]:
            if total >= MAX_TOTAL:
                break
            t = (n.get("title") or "").strip()
            src = (n.get("source") or "").strip()
            tail = f"（{src}）" if src else ""
            lines.append(f"・{t}{tail}")  # 不放原始長連結（Google News RSS 網址過長且醜），改由底部站內連結帶出
            total += 1
        blocks.append("\n".join(lines))
    if not blocks:
        return None
    md = (datetime.date.today().strftime("%-m/%-d") if hasattr(datetime.date.today(), "strftime") else TODAY)
    head = f"📰 領富 AI ・ 你的每日新聞（{md}）\n"
    foot = ("\n\n※ 公開新聞整理，非投資建議。"
            f"\n🔗 更多：{SITE}/pages/news?openExternalBrowser=1"
            "\n如需調整或關閉，請至網站會員中心。")
    return (head + "\n" + "\n\n".join(blocks) + foot)[:4900]


def fetch_members():
    if FAKE_SUBS:
        return json.loads(FAKE_SUBS)
    if not (SUPABASE_URL and SERVICE_KEY):
        print("[error] 缺 SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY，無法讀會員")
        sys.exit(1)
    url = (f"{SUPABASE_URL}/rest/v1/profiles"
           "?select=id,name,line_user_id,news_subs&line_user_id=not.is.null")
    req = urllib.request.Request(url, headers={
        "apikey": SERVICE_KEY,
        "Authorization": f"Bearer {SERVICE_KEY}",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def save_subs(uid, subs):
    if DRY_RUN or FAKE_SUBS:
        return True
    url = f"{SUPABASE_URL}/rest/v1/profiles?id=eq.{uid}"
    body = json.dumps({"news_subs": subs}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="PATCH", headers={
        "apikey": SERVICE_KEY,
        "Authorization": f"Bearer {SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return 200 <= r.status < 300
    except Exception as e:
        print(f"[warn] 回寫 news_subs 失敗 {uid}: {e}")
        return False


def push_message(to, text):
    if DRY_RUN or FAKE_SUBS:
        print(f"[dry-run] → {to}\n{text}\n{'-' * 50}")
        return True
    if not LINE_TOKEN:
        print("[error] 缺 LINE_CHANNEL_ACCESS_TOKEN")
        return False
    body = json.dumps({"to": to, "messages": [{"type": "text", "text": text}]}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(LINE_PUSH_URL, data=body, method="POST", headers={
        "Authorization": f"Bearer {LINE_TOKEN}",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return 200 <= r.status < 300
    except urllib.error.HTTPError as e:
        print(f"[warn] 推播失敗 {to}: HTTP {e.code} {e.read().decode('utf-8', 'ignore')[:160]}")
        return False
    except Exception as e:
        print(f"[warn] 推播失敗 {to}: {e}")
        return False


def main():
    news = load_news()
    print(f"[info] 今日({TODAY})新聞 {len(news)} 則")
    if not news:
        print("[done] 今日無新聞，跳過。")
        return

    members = fetch_members()
    print(f"[info] 有 LINE 的會員 {len(members)} 位")

    sent = 0
    for m in members:
        subs = m.get("news_subs") or {}
        if not isinstance(subs, dict) or not subs.get("active"):
            continue
        topics = [t for t in (subs.get("topics") or []) if t in TOPICS]
        if not topics:
            continue
        if subs.get("last_pushed") == TODAY:
            continue  # 今天已推過
        text = build_digest(m.get("name", ""), topics, news)
        if not text:
            continue  # 今日無相符新聞，不打擾
        if push_message(m["line_user_id"], text):
            sent += 1
            subs["last_pushed"] = TODAY
            save_subs(m["id"], subs)
        time.sleep(0.1)

    print(f"[done] 推播 {sent} 位會員")


if __name__ == "__main__":
    main()
