#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
push_market_risk.py — 大盤風險 LINE 提醒（v2）

讀 taifex_live.json，當「台指期夜盤大跌」或「明日大盤波動風險=高」時，
推播 LINE 提醒給有綁定 LINE 且開啟推播的會員。

定位：風險雷達，不是交易訊號 —— 只提醒「波動風險」，不給買賣點、不喊多空。
觸發：夜盤 pct <= -1.0%  或  風險等級 = 高
去重：同一交易日(asof)只推一次（data/_taifex_alert.json 記錄）。

環境變數：SUPABASE_SERVICE_ROLE_KEY、LINE_CHANNEL_ACCESS_TOKEN
  DRY_RUN=1 或 FAKE_SUBS=[...] 可本機測試不真推。
建議排程：每交易日早上約 07:00（夜盤結束後、開盤前）。
"""
import os
import sys
import json
import datetime
import urllib.request
import urllib.error
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
TAIFEX = DATA_DIR / "taifex_live.json"
STATE = DATA_DIR / "_taifex_alert.json"
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://lhwxpnyzplylajxunlua.supabase.co").rstrip("/")
SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
LINE_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
DRY_RUN = os.environ.get("DRY_RUN") == "1"
FAKE_SUBS = os.environ.get("FAKE_SUBS", "")
LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"
NIGHT_DROP = -1.0   # 夜盤跌幅觸發門檻(%)


def fetch_members():
    if FAKE_SUBS:
        return json.loads(FAKE_SUBS)
    if not (SUPABASE_URL and SERVICE_KEY):
        print("[error] 缺 SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY")
        sys.exit(1)
    url = f"{SUPABASE_URL}/rest/v1/profiles?select=id,line_user_id,push_optin&line_user_id=not.is.null"
    req = urllib.request.Request(url, headers={"apikey": SERVICE_KEY, "Authorization": f"Bearer {SERVICE_KEY}", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def push_message(to, text):
    if DRY_RUN or FAKE_SUBS:
        print(f"[dry-run] → {to}\n{text}\n{'-' * 50}")
        return True
    if not LINE_TOKEN:
        print("[error] 缺 LINE_CHANNEL_ACCESS_TOKEN")
        return False
    body = json.dumps({"to": to, "messages": [{"type": "text", "text": text}]}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(LINE_PUSH_URL, data=body, method="POST",
                                 headers={"Authorization": f"Bearer {LINE_TOKEN}", "Content-Type": "application/json"})
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
    if not TAIFEX.exists():
        print("[done] 無 taifex_live.json，跳過。")
        return
    d = json.loads(TAIFEX.read_text(encoding="utf-8"))
    risk = d.get("risk") or {}
    night = d.get("txNight") or {}
    asof = d.get("asof") or d.get("updatedAt") or ""
    night_pct = night.get("pct")
    level = risk.get("level")

    trigger = (isinstance(night_pct, (int, float)) and night_pct <= NIGHT_DROP) or (level == "高")
    if not trigger:
        print(f"[done] 風險【{level}】夜盤 {night_pct}%，未達提醒門檻，不推播。")
        return

    # 去重：同一交易日只推一次
    state = {}
    if STATE.exists():
        try:
            state = json.loads(STATE.read_text(encoding="utf-8"))
        except Exception:
            state = {}
    if state.get("lastAlert") == asof and not (DRY_RUN or FAKE_SUBS):
        print(f"[done] {asof} 已推播過，跳過。")
        return

    # 訊息（合規：波動風險、非預測、非投資建議）
    reasons = "\n".join(f"・{r}" for r in (risk.get("reasons") or [])[:4])
    nseg = (f"今晨台指期夜盤下跌 {night_pct:.2f}%，" if isinstance(night_pct, (int, float)) and night_pct <= NIGHT_DROP else "")
    msg = (f"🌡️ 大盤風險提醒（領富 AI）\n\n"
           f"{nseg}明日大盤波動風險偏【{level}】。\n\n"
           f"{reasons}\n\n"
           f"🛡️ 高波動個股、槓桿／反向 ETF（正2、反1）擺盪可能加大，請留意部位與風險承受度；持股穩健者通常無需因單日波動進出。\n\n"
           f"※ 資訊整理、非漲跌預測、非投資建議。\n"
           f"查看大盤風險溫度計 → https://leadfuai.com/pages/market-risk")

    members = fetch_members()
    targets = [m for m in members if m.get("line_user_id") and m.get("push_optin") is not False]
    print(f"[info] 風險【{level}】夜盤 {night_pct}% → 觸發提醒；推播對象 {len(targets)} 人")

    sent = 0
    for m in targets:
        if push_message(m["line_user_id"], msg):
            sent += 1
    print(f"✅ 大盤風險提醒推播完成：{sent}/{len(targets)}")

    if not (DRY_RUN or FAKE_SUBS):
        STATE.write_text(json.dumps({"lastAlert": asof, "level": level, "at": datetime.datetime.now().isoformat()}, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
