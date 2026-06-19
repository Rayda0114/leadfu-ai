#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
領富 AI · 選題引擎 → 領富 內容橋（push 端）

把一份「選題 brief」（xuanti/MiroFish 產出的 markdown 或結構化 JSON）POST 到
領富 Worker 的 /api/mirofish-ingest，存成 Supabase 草稿（status=draft）。

⚠️ YMYL 財經內容：本腳本只負責「送方向到主編桌上」。
   - 端點伺服器端會強制 status='draft'，本腳本無法、也不該自動發佈。
   - 真正出稿由主編在審核 UI 用真實來源重寫 article_md、人工按發佈。

設計取捨：brief 已由選題引擎做過合規過濾，所以這裡的安全過濾「從簡」——
   只保留 defense-in-depth 的最後一道（砍目標價/報酬承諾、標待查證數字），
   真正的硬閘門在「人工審核」那關。端點本身也會再防呆一次。

用法：
   # 1) 先把 owner 的 Supabase access token 放進環境變數（在瀏覽器登入站長帳號後可從
   #    DevTools 主控台執行 (await window.LeadFuAuth.client.auth.getSession()).data.session.access_token 取得）
   export LEADFU_OWNER_JWT="eyJhbGciOi..."

   # 2) 送一份 markdown brief（會把整份 md 一併存進 source_meta.brief_md 供主編參考）
   python3 scripts/push_brief_to_leadfu.py /Users/rayda/code/xuanti/samples/swarm_brief_20260619.md

   # 2') 或送一份結構化 JSON brief（欄位直接對應資料表）
   python3 scripts/push_brief_to_leadfu.py brief.json

   # 先看會送出什麼、不真的送（強烈建議第一次先 dry-run）
   python3 scripts/push_brief_to_leadfu.py swarm_brief.md --dry-run

選項：
   --token <jwt>       owner JWT（預設讀環境變數 LEADFU_OWNER_JWT）
   --endpoint <url>    端點（預設 https://leadfuai.com/api/mirofish-ingest，可用 LEADFU_INGEST_URL 覆蓋）
   --dry-run           只印出 payload，不 POST
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request

DEFAULT_ENDPOINT = os.environ.get(
    "LEADFU_INGEST_URL", "https://leadfuai.com/api/mirofish-ingest"
)

# 股票代號樣式：台股 4 碼、美股 1-5 英文字母（粗略，僅供 sectors 萃取參考，仍標待查證）
_TICKER_RE = re.compile(r"\b\d{4}\b|\b[A-Z]{1,5}\b")
# 具體大數字（≥3 位數，含千分位/小數/百分比），用來標「未引用數字需查證」
_BIG_NUM_RE = re.compile(r"\d{1,3}(?:,\d{3})+|\d{3,}(?:\.\d+)?|\d+(?:\.\d+)?\s*[%％億兆]")


# ───────────────────────── 安全過濾（defense-in-depth，與 worker 端一致的保守版）─────────────────────────
def strip_stock_calls(text):
    """砍掉最不該出現、移除也不傷語意的：帶數字的目標價、報酬保證。"""
    if not text:
        return text
    text = re.sub(r"目標價\s*[:：]?\s*[0-9][0-9.,]*\s*元?", "（目標價已移除）", text)
    text = re.sub(
        r"(保證獲利|穩賺不賠|穩賺|包賺|報酬保證|保證賺錢|保證賺|必賺)",
        "（報酬承諾已移除）",
        text,
    )
    return text


def quality_gate(brief, raw_md):
    """產出 quality_flags（供主編參考）並回傳 (flags, hard_fail, reasons)。
    硬擋條件刻意保守：brief 已過濾，這裡只擋「明顯不能送」的（缺必填、近乎空白）。"""
    flags = {}
    reasons = []

    title = (brief.get("title_hint") or "").strip()
    thesis = (brief.get("thesis") or "").strip()
    if not title:
        reasons.append("缺 title_hint")
    if not thesis:
        reasons.append("缺 thesis")

    body = raw_md or (thesis + "\n" + json.dumps(brief, ensure_ascii=False))
    if len((body or "").strip()) < 80:
        reasons.append("內容過短（疑似空 brief）")

    # 免責聲明
    flags["has_disclaimer"] = bool(
        re.search(r"免責|disclaimer|非投資建議|不構成.*建議", body, re.I)
    )
    # 待查證標記（needs_verify / 待查證）數量
    flags["needs_verify_markers"] = len(
        re.findall(r"needs[_ ]?verify|待查證", body, re.I)
    )
    # 未明確標待查證、卻出現的具體大數字數量（提醒主編逐一核對來源）
    flags["unsourced_numbers"] = len(_BIG_NUM_RE.findall(body))
    # 殘留喊單字樣偵測（送出前應為 0；>0 代表上游過濾沒生效，主編要特別注意）
    flags["stock_call_hits"] = len(
        re.findall(r"目標價\s*\d|保證獲利|穩賺|包賺|必漲|全壓", body)
    )

    hard_fail = len(reasons) > 0
    return flags, hard_fail, reasons


# ───────────────────────── markdown brief → 結構化 ─────────────────────────
def _section(md, *titles):
    """抓某個 ## / ### 標題底下到下一個同/更高層標題或 --- 之間的文字。"""
    for title in titles:
        m = re.search(
            r"^#{1,4}\s*[^\n]*"
            + re.escape(title)
            + r"[^\n]*\n(.*?)(?=^\s*#{1,4}\s|\n---|\Z)",
            md,
            re.S | re.M,
        )
        if m:
            return m.group(1).strip()
    return ""


def _first_heading(md):
    m = re.search(r"^#\s+(.+)$", md, re.M)
    if not m:
        return ""
    t = m.group(1).strip()
    # 去掉常見前綴 "領富選題 Brief｜" / "...Brief|"
    t = re.sub(r"^.*?Brief\s*[｜|]\s*", "", t)
    return t.strip()


def _bullets(text):
    """把一段文字裡的清單項（- / 1. / 數字）抽成陣列，去掉粗體標記。"""
    items = []
    for line in (text or "").splitlines():
        m = re.match(r"^\s*(?:[-*]|\d+[.)、])\s+(.*)$", line)
        if m:
            s = re.sub(r"\*\*", "", m.group(1)).strip()
            if s:
                items.append(s[:500])
    return items


def _parse_sector_tables(md):
    """抓含 sample_tickers / 環節 欄位的 markdown 表，轉成 [{sector, sample_tickers}]。"""
    sectors = []
    # 逐個表格區塊（連續以 | 開頭的行）
    for block in re.findall(r"(?:^\|.*\|\s*$\n?)+", md, re.M):
        rows = [r for r in block.splitlines() if r.strip().startswith("|")]
        if len(rows) < 2:
            continue
        header = [c.strip() for c in rows[0].strip().strip("|").split("|")]
        if not any(("環節" in h or "sample_tickers" in h or "ticker" in h.lower()) for h in header):
            continue
        # 跳過表頭 + 分隔線（---）
        for r in rows[2:]:
            cells = [c.strip() for c in r.strip().strip("|").split("|")]
            if not cells or not cells[0] or set(cells[0]) <= set("-: "):
                continue
            sector = re.sub(r"\*\*", "", cells[0]).strip()
            tickers = []
            joined = " ".join(cells[1:2]) if len(cells) > 1 else ""
            for t in _TICKER_RE.findall(joined):
                if t not in tickers:
                    tickers.append(t)
            sectors.append({"sector": sector, "sample_tickers": tickers, "needs_verify": True})
    return sectors


def _extract_keywords(md):
    """從含「關鍵字」的行 best-effort 切出幾個詞（仍以主編判斷為準）。"""
    kws = []
    for line in md.splitlines():
        if "關鍵字" in line or "SEO" in line:
            for tok in re.split(r"[／/、，,（）()→\s]+", line):
                tok = re.sub(r"[^0-9A-Za-z一-鿿ＤＫ→]+", "", tok).strip()
                if 2 <= len(tok) <= 16 and tok not in kws and "關鍵字" not in tok:
                    kws.append(tok)
    return kws[:12]


def brief_from_markdown(md, src_path):
    title = _first_heading(md) or os.path.basename(src_path)
    thesis = _section(md, "一句話定位", "一句話總結", "核心命題")
    if not thesis:
        # fallback：標題與日期之後的第一段
        body = re.sub(r"^#.+$", "", md, count=1, flags=re.M)
        body = re.sub(r"^日期[:：].*$", "", body, flags=re.M)
        para = next((p.strip() for p in re.split(r"\n\s*\n", body) if p.strip() and not p.strip().startswith("#")), "")
        thesis = para
    risk_notes = _bullets(_section(md, "contrarian_angle", "反方", "風險"))
    date_m = re.search(r"日期[:：]\s*([0-9/\-]+)", md)
    brief = {
        "title_hint": title.strip()[:300],
        "thesis": thesis.strip(),
        "points": [],  # 主編以全文 brief_md 為準；不從 md 硬拆論點避免失真
        "seo_keywords": _extract_keywords(md),
        "sectors": _parse_sector_tables(md),
        "risk_notes": risk_notes,
        "source_meta": {
            "source": "xuanti/選題引擎",
            "brief_file": os.path.basename(src_path),
            "brief_date": (date_m.group(1) if date_m else None),
            "brief_md": md,  # 完整原始 brief，供主編在審核 UI 對照查證
        },
    }
    return brief


# ───────────────────────── 主流程 ─────────────────────────
def load_brief(path):
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    if path.lower().endswith(".json"):
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("JSON brief 必須是物件 {}")
        data.setdefault("source_meta", {})
        if isinstance(data["source_meta"], dict):
            data["source_meta"].setdefault("brief_file", os.path.basename(path))
            data["source_meta"].setdefault("brief_md", raw)
        return data, raw
    # 預設當 markdown 處理
    return brief_from_markdown(raw, path), raw


def main():
    ap = argparse.ArgumentParser(description="把選題 brief POST 成領富草稿（owner-only）")
    ap.add_argument("brief", help="brief 檔（.md 或 .json）")
    ap.add_argument("--token", default=os.environ.get("LEADFU_OWNER_JWT", ""),
                    help="owner Supabase access token（預設讀 $LEADFU_OWNER_JWT）")
    ap.add_argument("--ingest-key", default=os.environ.get("LEADFU_INGEST_KEY", ""),
                    help="機器人密鑰（排程無人送稿用；預設讀 $LEADFU_INGEST_KEY）。給了就走機器人路徑，不需 owner JWT")
    ap.add_argument("--endpoint", default=DEFAULT_ENDPOINT, help="ingest 端點 URL")
    ap.add_argument("--no-verify", action="store_true", help="略過 L3 查證清單（預設會自動產生並附上）")
    ap.add_argument("--data-dir", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"),
                    help="L3 查證比對用的 data/ 目錄")
    ap.add_argument("--dry-run", action="store_true", help="只印 payload，不 POST")
    args = ap.parse_args()

    if not os.path.exists(args.brief):
        print(f"找不到檔案：{args.brief}", file=sys.stderr)
        sys.exit(1)

    brief, raw_md = load_brief(args.brief)

    # 安全過濾（最後一道，保守版）
    brief["title_hint"] = strip_stock_calls(brief.get("title_hint", ""))
    brief["thesis"] = strip_stock_calls(brief.get("thesis", ""))

    # 品質閘門
    flags, hard_fail, reasons = quality_gate(brief, raw_md)
    brief["quality_flags"] = flags
    if hard_fail:
        print("✗ 品質閘門擋下，未送出：", "；".join(reasons), file=sys.stderr)
        print(json.dumps(flags, ensure_ascii=False, indent=2), file=sys.stderr)
        sys.exit(2)

    # L3 AI 查證清單（比對 data/ 官方資料；失敗不擋送稿，只記錯誤供主編知道）
    if not args.no_verify:
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import verify_brief
            rep = verify_brief.build_verify_report(brief, data_dir=args.data_dir)
            brief["verify_report"] = rep
            c = rep.get("ticker_summary", {})
            print(f"  L3 查證：核對 {rep.get('ticker_total',0)} 檔代號"
                  f"（配錯 {c.get('mismatch',0)}、查無 {c.get('not_found',0)}）、"
                  f"具體數字 {rep.get('numbers',{}).get('count',0)} 處待人工核對")
            if c.get("mismatch") or c.get("not_found"):
                print("  ⚠ 有代號配錯/查無，主編務必在審核頁逐條確認。")
        except Exception as e:
            brief["verify_report"] = {"error": "verify skipped: " + str(e)}
            print(f"  ⚠ L3 查證略過（{e}）")

    # 端點不接受 article_md / status；本地先移除以免誤會
    brief.pop("article_md", None)
    brief.pop("status", None)

    payload = json.dumps(brief, ensure_ascii=False)

    print("── 即將送出的 brief 摘要 ──")
    print(f"  標題建議：{brief.get('title_hint','')}")
    print(f"  主軸：{(brief.get('thesis','') or '')[:80]}…")
    print(f"  族群數：{len(brief.get('sectors') or [])}　風險點：{len(brief.get('risk_notes') or [])}"
          f"　關鍵字：{len(brief.get('seo_keywords') or [])}")
    print(f"  品質旗標：{json.dumps(flags, ensure_ascii=False)}")
    if not flags.get("has_disclaimer"):
        print("  ⚠ 提醒：brief 未偵測到免責聲明字樣（主編務必在文末補上）。")
    if flags.get("stock_call_hits"):
        print(f"  ⚠ 提醒：偵測到 {flags['stock_call_hits']} 處疑似喊單字樣，主編請特別查核。")

    if args.dry_run:
        print("\n── DRY RUN：payload（未送出）──")
        print(json.dumps(brief, ensure_ascii=False, indent=2))
        return

    headers = {"Content-Type": "application/json"}
    if args.ingest_key:
        headers["X-Ingest-Key"] = args.ingest_key          # 機器人路徑（排程用）
    elif args.token:
        headers["Authorization"] = "Bearer " + args.token   # owner 登入路徑
    else:
        print("\n✗ 缺憑證：請設 $LEADFU_OWNER_JWT（owner）或 $LEADFU_INGEST_KEY（機器人）。", file=sys.stderr)
        sys.exit(1)

    req = urllib.request.Request(
        args.endpoint,
        data=payload.encode("utf-8"),
        method="POST",
        headers=headers,
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            out = resp.read().decode("utf-8", "replace")
            print(f"\n✓ 已送出（HTTP {resp.status}）。回傳新草稿：")
            try:
                rows = json.loads(out)
                row = rows[0] if isinstance(rows, list) and rows else rows
                print(f"  id={row.get('id')}　status={row.get('status')}（應為 draft）")
                print("  → 到審核 UI（/pages/insights-admin）用真實來源重寫、人工發佈。")
            except Exception:
                print(out[:500])
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        print(f"\n✗ 送出失敗 HTTP {e.code}：{body[:400]}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"\n✗ 連線失敗：{e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
