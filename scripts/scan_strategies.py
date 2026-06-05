#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scan_strategies.py — 領富 AI 每日選股策略自動掃描（LINE Messaging API）

流程：讀 Supabase profiles.scan_strategies（會員存的選股策略中 scan=true 者）→
用與前端 screener.html 同一套篩選邏輯掃今日全市場 → 跟該策略「上次符合清單
(last_codes)」比對 → 把「新進榜」的股票透過 LINE 官方帳號推給該會員 →
回寫 last_codes / last_scan（避免重複通知）。

原則：
  - 只推給「有 line_user_id」且該策略 scan=true 的會員。
  - 第一次啟用（沒有 last_scan 基準）只記錄基準＋告知已啟動，不洗整份清單。
  - 之後每天只通知「新進榜」；掉出榜不打擾。
  - 內容為公開資訊整理／通知，不含買賣建議（守投顧法／證交法）。

環境變數（放 GitHub Actions secret，勿寫進 repo）：
  SUPABASE_URL                例：https://lhwxpnyzplylajxunlua.supabase.co
  SUPABASE_SERVICE_ROLE_KEY   service role key（繞過 RLS 讀/寫全體 profiles）
  LINE_CHANNEL_ACCESS_TOKEN   LINE Messaging API channel access token
選用：
  DRY_RUN=1   只印、不推、不回寫（測試用）
"""
import json
import os
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
SITE = "https://leadfuai.com"
LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"
MAX_PER_STRATEGY = 10
TODAY = datetime.date.today().isoformat()


def load_json(name):
    try:
        return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[warn] 讀 {name} 失敗: {e}")
        return {}


def load_data():
    """載入全市場資料，回傳各種以 code 為 key 的查表。"""
    mgn = load_json("margin_live.json").get("data", {}) or {}
    mgn.update(load_json("margin_tpex_live.json").get("data", {}) or {})
    return dict(
        stocks=load_json("stocks_live.json").get("stocks", []) or [],
        rev=load_json("revenue_live.json").get("revenue", {}) or {},
        fin=load_json("financials_live.json").get("data", {}) or {},
        val=load_json("valuation_live.json").get("data", {}) or {},
        ind=load_json("indicators_live.json").get("data", {}) or {},
        inst=load_json("institutional_live.json").get("data", {}) or {},
        sbl=load_json("sbl_live.json").get("data", {}) or {},
        mgn=mgn,
        fv=load_json("fair_value_live.json").get("data", {}) or {},
        ann=set(str(a.get("code")) for a in load_json("announcements_live.json").get("announcements", []) if a.get("code")),
        att=set(str(c) for c in (load_json("attention_live.json").get("data") or {}).keys()),
        streak=load_json("inst_streak_live.json").get("data") or {},
    )


def num(x):
    return x if isinstance(x, (int, float)) and not isinstance(x, bool) else None


def pct_change(price, change):
    prev = (price or 0) - (change or 0)
    return (change / prev * 100) if prev else 0.0


def fv_class(code, fv):
    x = fv.get(code)
    if not x or num(x.get("position")) is None:
        return None
    p = x["position"]
    return "low" if p <= 0.30 else ("high" if p >= 0.80 else "fair")


def run_filter(f, D):
    """與前端 screener.html runFilter() 同一套邏輯；回傳符合的 stock dict 清單。"""
    out = []
    for s in D["stocks"]:
        c = s.get("code")
        price = s.get("price") or 0
        if f.get("priceMin") is not None and not (price >= f["priceMin"]):
            continue
        if f.get("priceMax") is not None and not (price <= f["priceMax"]):
            continue
        vol = s.get("volume") or 0
        if f.get("volMin") is not None and not (vol >= f["volMin"]):
            continue
        if f.get("volMax") is not None and not (vol <= f["volMax"]):
            continue
        if f.get("exLowVol") and not (vol >= 100):
            continue
        if f.get("status") and s.get("status") not in f["status"]:
            continue
        if f.get("cats") and s.get("category") not in f["cats"]:
            continue
        if f.get("pctMin") is not None or f.get("pctMax") is not None:
            p = pct_change(price, s.get("change") or 0)
            if f.get("pctMin") is not None and p < f["pctMin"]:
                continue
            if f.get("pctMax") is not None and p > f["pctMax"]:
                continue
        # 基本面
        if f.get("revMin") is not None:
            x = D["rev"].get(c)
            if not (x and num(x.get("yoy")) is not None and x["yoy"] >= f["revMin"]):
                continue
        if f.get("momMin") is not None:
            x = D["rev"].get(c)
            if not (x and num(x.get("mom")) is not None and x["mom"] >= f["momMin"]):
                continue
        if f.get("gmMin") is not None:
            x = D["fin"].get(c)
            if not (x and num(x.get("gross_margin")) is not None and x["gross_margin"] >= f["gmMin"]):
                continue
        if f.get("peMax") is not None:
            x = D["val"].get(c)
            if not (x and num(x.get("pe_ratio")) and x["pe_ratio"] > 0 and x["pe_ratio"] <= f["peMax"]):
                continue
        if f.get("yldMin") is not None:
            x = D["val"].get(c)
            if not (x and num(x.get("yield_pct")) is not None and x["yield_pct"] >= f["yldMin"]):
                continue
        if f.get("confMin") is not None:
            x = D["fv"].get(c)
            if not (x and num(x.get("confidence")) is not None and x["confidence"] >= f["confMin"]):
                continue
        if f.get("fvPos") and fv_class(c, D["fv"]) != f["fvPos"]:
            continue
        # 籌碼 / 題材
        if f.get("ma20"):
            x = D["ind"].get(c)
            if not (x and num(x.get("ma20")) and price > x["ma20"]):
                continue
        if f.get("foreign"):
            x = D["inst"].get(c)
            if not (x and num(x.get("foreign_net_lots")) is not None and x["foreign_net_lots"] > 0):
                continue
        if f.get("trust"):
            x = D["inst"].get(c)
            if not (x and num(x.get("trust_net_lots")) is not None and x["trust_net_lots"] > 0):
                continue
        if f.get("opProfit"):
            x = D["fin"].get(c)
            if not (x and num(x.get("op_margin")) is not None and x["op_margin"] > 0):
                continue
        if f.get("sbl"):
            x = D["sbl"].get(c)
            if not (x and num(x.get("sbl_change")) is not None and x["sbl_change"] > 0):
                continue
        if f.get("margin"):
            x = D["mgn"].get(c)
            if not (x and num(x.get("margin_change")) is not None and x["margin_change"] > 0):
                continue
        if f.get("announce") and str(c) not in D["ann"]:
            continue
        if f.get("exAttention") and str(c) in D["att"]:
            continue
        if f.get("instBuyDays"):
            x = D["streak"].get(c)
            if not (x and x.get("dir") == "buy" and x.get("days", 0) >= f["instBuyDays"]):
                continue
        out.append(s)
    return out


def describe(code, D):
    """新進榜股票的一行重點（殖利率/PE/合理區間/營收）。"""
    bits = []
    v = D["val"].get(code) or {}
    if num(v.get("yield_pct")):
        bits.append(f"殖利{v['yield_pct']:.1f}%")
    if num(v.get("pe_ratio")) and v["pe_ratio"] > 0:
        bits.append(f"PE{v['pe_ratio']:.0f}")
    if fv_class(code, D["fv"]) == "low":
        bits.append("合理區間偏低")
    r = D["rev"].get(code) or {}
    if num(r.get("yoy")):
        bits.append(f"營收YoY{r['yoy']:+.0f}%")
    return "・".join(bits[:3])


def fetch_members():
    if not (SUPABASE_URL and SERVICE_KEY):
        print("[error] 缺 SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY，無法讀會員")
        sys.exit(1)
    url = (f"{SUPABASE_URL}/rest/v1/profiles"
           "?select=id,name,line_user_id,scan_strategies&line_user_id=not.is.null")
    req = urllib.request.Request(url, headers={
        "apikey": SERVICE_KEY,
        "Authorization": f"Bearer {SERVICE_KEY}",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def save_strategies(uid, strategies):
    """回寫該會員的 scan_strategies（含更新後的 last_codes / last_scan）。"""
    if DRY_RUN:
        return True
    url = f"{SUPABASE_URL}/rest/v1/profiles?id=eq.{uid}"
    body = json.dumps({"scan_strategies": strategies}, ensure_ascii=False).encode("utf-8")
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
        print(f"[warn] 回寫策略失敗 {uid}: {e}")
        return False


def push_message(to, text):
    if DRY_RUN:
        print(f"[dry-run] → {to}\n{text}\n{'-' * 40}")
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
    D = load_data()
    if not D["stocks"]:
        print("[error] 無 stocks 資料，中止")
        sys.exit(1)
    names = {s["code"]: s.get("name", "") for s in D["stocks"] if s.get("code")}

    members = fetch_members()
    print(f"[info] 有 LINE 的會員 {len(members)} 位；掃描日 {TODAY}")

    sent = scanned_users = 0
    for m in members:
        strategies = m.get("scan_strategies") or []
        if not isinstance(strategies, list):
            continue
        active = [s for s in strategies if isinstance(s, dict) and s.get("scan")]
        if not active:
            continue
        scanned_users += 1
        blocks = []
        changed = False
        for strat in active:
            f = strat.get("filters") or {}
            codes = sorted(s["code"] for s in run_filter(f, D))
            prev = set(strat.get("last_codes") or [])
            had_baseline = bool(strat.get("last_scan"))
            new_codes = [c for c in codes if c not in prev]
            name = strat.get("name", "未命名策略")
            if not had_baseline:
                blocks.append(f"✅ 已開啟「{name}」每日掃描，目前 {len(codes)} 檔符合，之後只通知新進榜。")
            elif new_codes:
                lines = [f"🔍 策略「{name}」新符合 {len(new_codes)} 檔："]
                for c in new_codes[:MAX_PER_STRATEGY]:
                    desc = describe(c, D)
                    lines.append(f"・{c} {names.get(c, '')}" + (f"｜{desc}" if desc else ""))
                if len(new_codes) > MAX_PER_STRATEGY:
                    lines.append(f"…等共 {len(new_codes)} 檔，看完整清單於網站")
                blocks.append("\n".join(lines))
            strat["last_codes"] = codes
            strat["last_scan"] = TODAY
            changed = True
        if blocks:
            text = ("📡 領富 AI ・ 選股雷達\n\n"
                    + "\n\n".join(blocks)
                    + f"\n\n🔗 看完整清單：{SITE}/pages/screener?openExternalBrowser=1"
                    + "\n\n※ 公開資訊整理，非投資建議。可至會員中心關閉。")
            if push_message(m["line_user_id"], text[:4900]):
                sent += 1
            time.sleep(0.1)
        if changed:
            save_strategies(m["id"], strategies)

    print(f"[done] 掃描 {scanned_users} 位有啟用策略的會員；推播 {sent} 位")


if __name__ == "__main__":
    main()
