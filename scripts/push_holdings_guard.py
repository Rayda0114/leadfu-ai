#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
push_holdings_guard.py — 領富 AI 持股風險守門員 · LINE 主動提醒（買進理由追蹤）

流程：讀 Supabase profiles.holdings（每檔持股的 reasons = 當初買進理由）→
用今日資料逐條複查每個理由是否仍成立（與前端 main.js evalBuyReason 同邏輯）→
只在理由「新轉弱」（上次非 weak、這次 weak）時推 LINE，避免每天重複洗 →
回寫每檔的 guard 狀態（holdings[code].guard）。

理由 → 訊號：
  穩定配息   → valuation.yield_pct
  營收成長   → revenue.yoy
  估值偏低   → fair_value.position
  產業長期看好 → 注意股/處置警示 + risk_score

環境變數（GitHub Actions secret）：
  SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY / LINE_CHANNEL_ACCESS_TOKEN
選用：
  DRY_RUN=1          只印、不推、不回寫
  FAKE_HOLDINGS=...  JSON 陣列模擬會員（測試用，不讀 Supabase）
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
FAKE_HOLDINGS = os.environ.get("FAKE_HOLDINGS", "")
SITE = "https://leadfuai.com"
LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"
REASONS = ["穩定配息", "營收成長", "估值偏低", "產業長期看好"]


def load_json(name):
    try:
        return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[warn] 讀 {name} 失敗: {e}")
        return {}


def load_data():
    return dict(
        names={s["code"]: s.get("name", "") for s in load_json("stocks_live.json").get("stocks", []) if s.get("code")},
        val=load_json("valuation_live.json").get("data", {}) or {},
        rev=load_json("revenue_live.json").get("revenue", {}) or {},
        fv=load_json("fair_value_live.json").get("data", {}) or {},
        att=load_json("attention_live.json").get("data", {}) or {},
        rk=load_json("risk_score_live.json").get("data", {}) or {},
    )


def _num(x):
    return x if isinstance(x, (int, float)) and not isinstance(x, bool) else None


def eval_reason(code, reason, D):
    """與前端 main.js evalBuyReason 同邏輯，回傳 (status, text)。"""
    v = D["val"].get(code) or {}
    r = D["rev"].get(code) or {}
    fv = D["fv"].get(code) or {}
    att = D["att"].get(code)
    rk = D["rk"].get(code) or {}
    if reason == "穩定配息":
        y = _num(v.get("yield_pct"))
        if y is None:
            return ("watch", "查無殖利率資料")
        if y >= 3:
            return ("ok", f"殖利率約 {y:.1f}%，配息理由維持")
        if y >= 2:
            return ("watch", f"殖利率約 {y:.1f}%，略低於常見存股門檻")
        return ("weak", f"殖利率僅約 {y:.1f}%，「穩定配息」理由明顯減弱")
    if reason == "營收成長":
        yoy = _num(r.get("yoy"))
        if yoy is None:
            return ("watch", "查無最新月營收資料")
        if yoy >= 0:
            return ("ok", f"最新月營收年增 +{yoy:.1f}%，成長維持")
        if yoy > -10:
            return ("watch", f"最新月營收年增 {yoy:.1f}%，成長轉弱")
        return ("weak", f"最新月營收年增 {yoy:.1f}%，年增明顯轉負")
    if reason == "估值偏低":
        p = _num(fv.get("position"))
        if p is None:
            return ("watch", "查無合理區間資料")
        if p <= 0.4:
            return ("ok", f"現價仍接近合理區間下緣（位置 {p:.2f}）")
        if p < 0.8:
            return ("watch", f"現價已回到合理區間中段（位置 {p:.2f}）")
        return ("weak", f"現價已達／超過合理區間上緣（位置 {p:.2f}），「估值偏低」理由已不成立")
    if reason == "產業長期看好":
        if att:
            return ("weak", f"出現主管機關警示（{att.get('type', '注意/處置')}），建議重新檢視長期持有理由")
        sc = _num(rk.get("score"))
        if sc is not None and sc >= 60:
            return ("watch", f"風險分數偏高（{sc}），長期持有仍建議定期複查")
        return ("ok", "未出現重大警示，維持長期觀點")
    return ("watch", "")


def fetch_members():
    if FAKE_HOLDINGS:
        return json.loads(FAKE_HOLDINGS)
    if not (SUPABASE_URL and SERVICE_KEY):
        print("[error] 缺 SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY")
        sys.exit(1)
    url = f"{SUPABASE_URL}/rest/v1/profiles?select=id,name,line_user_id,holdings&line_user_id=not.is.null"
    req = urllib.request.Request(url, headers={
        "apikey": SERVICE_KEY, "Authorization": f"Bearer {SERVICE_KEY}", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def save_holdings(uid, holdings):
    if DRY_RUN or FAKE_HOLDINGS:
        return True
    url = f"{SUPABASE_URL}/rest/v1/profiles?id=eq.{uid}"
    body = json.dumps({"holdings": holdings}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="PATCH", headers={
        "apikey": SERVICE_KEY, "Authorization": f"Bearer {SERVICE_KEY}",
        "Content-Type": "application/json", "Prefer": "return=minimal"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return 200 <= r.status < 300
    except Exception as e:
        print(f"[warn] 回寫 holdings 失敗 {uid}: {e}")
        return False


def push_message(to, text):
    if DRY_RUN or FAKE_HOLDINGS:
        print(f"[dry-run] → {to}\n{text}\n{'-' * 50}")
        return True
    if not LINE_TOKEN:
        print("[error] 缺 LINE_CHANNEL_ACCESS_TOKEN")
        return False
    body = json.dumps({"to": to, "messages": [{"type": "text", "text": text}]}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(LINE_PUSH_URL, data=body, method="POST", headers={
        "Authorization": f"Bearer {LINE_TOKEN}", "Content-Type": "application/json"})
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
    D = load_data()
    members = fetch_members()
    print(f"[info] 有 LINE 的會員 {len(members)} 位")

    sent = 0
    for m in members:
        holdings = m.get("holdings") or {}
        if not isinstance(holdings, dict):
            continue
        changed = False
        blocks = []
        for code, h in holdings.items():
            if not isinstance(h, dict):
                continue
            reasons = [r for r in (h.get("reasons") or []) if r in REASONS]
            if not reasons:
                continue
            guard = h.get("guard") or {}
            newly_weak = []
            for rn in reasons:
                status, text = eval_reason(code, rn, D)
                if status == "weak" and guard.get(rn) != "weak":
                    newly_weak.append((rn, text))   # 新轉弱才提醒
                guard[rn] = status
            h["guard"] = guard
            changed = True
            if newly_weak:
                lines = [f"📉 {code} {D['names'].get(code, '')}"]
                for rn, text in newly_weak:
                    lines.append(f"・「{rn}」理由轉弱：{text}")
                blocks.append("\n".join(lines))
        if blocks:
            msg = ("🛡️ 領富 AI ・ 持股守門員提醒\n\n"
                   "你當初買進的理由出現變化：\n\n"
                   + "\n\n".join(blocks)
                   + f"\n\n建議重新檢視這些持股的買進理由。\n🔗 看完整健診：{SITE}/pages/portfolio-health?openExternalBrowser=1"
                   + "\n\n※ 公開資料整理，非投資建議。")
            if push_message(m["line_user_id"], msg[:4900]):
                sent += 1
            time.sleep(0.1)
        if changed:
            save_holdings(m["id"], holdings)

    print(f"[done] 推播 {sent} 位會員")


if __name__ == "__main__":
    main()
