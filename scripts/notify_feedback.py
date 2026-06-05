#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
notify_feedback.py — 有新「意見回饋」就推播到站長 LINE（領富 AI）

流程：讀 Supabase `feedback` 表裡 notified=false 的列 → 逐筆推到站長的
LINE（Messaging API）→ 推成功就把該列標記 notified=true（避免重複推）。

為什麼這樣做：
  - 全站「💬 回饋」浮動鈕 + VIP 訂閱意願都寫進 `feedback` 表，但沒有任何
    通知 → 站長得手動開 Supabase 才看得到，容易漏（例如 VIP 訂閱申請）。
  - 用既有的 LINE 推播 + GitHub Actions（與 push_watchlist_digest 同一套），
    每 ~15 分鐘檢查一次，有新回饋就主動通知。

需要環境變數（GitHub Actions secret，勿寫進 repo）：
  SUPABASE_URL                例：https://lhwxpnyzplylajxunlua.supabase.co
  SUPABASE_SERVICE_ROLE_KEY   service role key（後端讀寫 feedback、繞過 RLS）
  LINE_CHANNEL_ACCESS_TOKEN   LINE Messaging API 長期 channel access token
  OWNER_LINE_USER_ID          站長自己的 LINE userId（U+32hex；要先加官方帳號好友）
選用：
  DRY_RUN=1   只印、不實際推、不標記 notified（測試用）

前置（一次性）：feedback 表需有 boolean 欄位 notified（default false）。
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://lhwxpnyzplylajxunlua.supabase.co").rstrip("/")
SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
LINE_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
OWNER_ID = os.environ.get("OWNER_LINE_USER_ID", "")
DRY_RUN = os.environ.get("DRY_RUN") == "1"

LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"
SITE = "https://leadfuai.com"
MAX_PER_RUN = 20   # 單次最多推幾筆（防雪崩）


def fetch_unnotified():
    """讀 feedback 表 notified=false 的列（service role，繞過 RLS）。"""
    if not (SUPABASE_URL and SERVICE_KEY):
        print("[error] 缺 SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY")
        sys.exit(1)
    url = (f"{SUPABASE_URL}/rest/v1/feedback"
           "?select=id,category,rating,message,email,page_url"
           "&notified=eq.false&order=id.asc&limit=" + str(MAX_PER_RUN))
    req = urllib.request.Request(url, headers={
        "apikey": SERVICE_KEY,
        "Authorization": f"Bearer {SERVICE_KEY}",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def mark_notified(fid):
    """把某列標記 notified=true。"""
    if DRY_RUN:
        return True
    url = f"{SUPABASE_URL}/rest/v1/feedback?id=eq.{fid}"
    body = json.dumps({"notified": True}).encode("utf-8")
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
        print(f"[warn] 標記 notified 失敗 id={fid}: {e}")
        return False


def push(text):
    """推一則文字給站長 LINE。回傳 True/False。"""
    if DRY_RUN:
        print(f"[dry-run] → {OWNER_ID}\n{text}\n{'-' * 40}")
        return True
    if not (LINE_TOKEN and OWNER_ID):
        print("[error] 缺 LINE_CHANNEL_ACCESS_TOKEN / OWNER_LINE_USER_ID")
        return False
    body = json.dumps({"to": OWNER_ID, "messages": [{"type": "text", "text": text}]}).encode("utf-8")
    req = urllib.request.Request(LINE_PUSH_URL, data=body, method="POST", headers={
        "Authorization": f"Bearer {LINE_TOKEN}",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return 200 <= r.status < 300
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "ignore")[:200]
        # 403：站長還沒加官方帳號好友 → 無法推播
        print(f"[warn] 推播失敗 HTTP {e.code} {detail}")
        return False
    except Exception as e:
        print(f"[warn] 推播失敗: {e}")
        return False


def build_text(row):
    cat = (row.get("category") or "其他").strip()
    rating = row.get("rating")
    stars = ("★" * int(rating) + "☆" * (5 - int(rating))) if rating else ""
    msg = (row.get("message") or "").strip() or "（無文字內容）"
    email = (row.get("email") or "").strip() or "未留"
    page = (row.get("page_url") or "").strip()
    # VIP 訂閱申請 / 付費意願 → 標重要（這是潛在客戶，別漏）
    is_lead = any(k in cat for k in ("VIP", "訂閱", "付費"))
    head = "💰 領富 AI・新訂閱意願" if is_lead else "🔔 領富 AI・新回饋"
    lines = [f"{head} #{row.get('id')}", f"分類：{cat}" + (f"  {stars}" if stars else "")]
    lines.append(f"內容：{msg[:300]}")
    lines.append(f"Email：{email}")
    if page:
        lines.append(f"頁面：{page}")
    lines.append("")
    lines.append(f"🔗 後台查看：{SITE}（Supabase feedback 表）")
    return "\n".join(lines)[:4900]


def main():
    rows = fetch_unnotified()
    print(f"[info] 未通知回饋 {len(rows)} 筆")
    sent = 0
    for row in rows:
        if push(build_text(row)):
            if mark_notified(row["id"]):
                sent += 1
        time.sleep(0.1)
    print(f"[done] 已推播 {sent} 筆"+("（DRY_RUN，未實際推/未標記）" if DRY_RUN else ""))


if __name__ == "__main__":
    main()
