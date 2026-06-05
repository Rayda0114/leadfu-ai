#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyze_news.py — 用 AI 幫每則新聞標「判斷」，把轉貼新聞變成「整理過的新聞」。

每則新聞加上：
  ai_sentiment  利多 / 利空 / 中性
  ai_horizon    短期 / 長期 / 不明
  ai_related    影響的上市櫃個股代號陣列（公司名 → 代號，對不到就空）
  ai_note       一句話解讀（中立、非投資建議）
寫回 data/news_live.json。

跑在每日資料更新「之後」（新聞抓好後）。呼叫 Cloudflare Worker /api/ask
（共用既有 Nvidia 配置，無需另設 secret）。純 stdlib。
"""
import json
import os
import re
import ssl
import time
import urllib.request
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
ASK_URL = os.environ.get("ASK_URL", "https://leadfuai.com/api/ask")
CHUNK = 10                    # 每批分析幾則
_CTX = ssl.create_default_context()


def call_ai(prompt, max_tokens=2500, retries=3):
    body = json.dumps({"question": prompt, "max_tokens": max_tokens, "stream": False}).encode("utf-8")
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(ASK_URL, data=body, method="POST", headers={
                "Content-Type": "application/json", "User-Agent": "leadfu-news/1.0"})
            with urllib.request.urlopen(req, timeout=120, context=_CTX) as r:
                data = json.loads(r.read().decode("utf-8"))
            if isinstance(data, dict):
                if data.get("error"):
                    raise RuntimeError(data["error"])
                return data.get("answer", "")
            return ""
        except Exception as e:
            print(f"  ⚠ AI 第 {attempt} 次失敗：{e}")
            time.sleep(4 * attempt)
    return ""


def build_name_index(stocks):
    """name -> code。"""
    idx = {}
    for s in stocks:
        nm = (s.get("name") or "").strip()
        code = s.get("code")
        if nm and code:
            idx[nm] = code
    return idx


GENERIC = {"上市公司", "上櫃公司", "上市櫃公司", "台股", "大盤", "公司", "證交所", "櫃買中心", "金管會"}


def map_companies(companies, name_idx):
    """AI 給的公司名 → 股票代號（保守對應，避免誤配）。"""
    codes = []
    for c in companies or []:
        c = (c or "").strip()
        if not c or c in GENERIC:
            continue
        if c in name_idx:                       # 完全相符
            codes.append(name_idx[c])
            continue
        # 股票簡稱是公司全名的子字串（如「豐技」⊂「豐技生技」）
        cand = [(nm, code) for nm, code in name_idx.items() if len(nm) >= 2 and nm in c]
        if cand:
            cand.sort(key=lambda x: -len(x[0]))  # 取最長（最具體）
            codes.append(cand[0][1])
    seen, out = set(), []
    for x in codes:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def analyze_chunk(titles):
    prompt = (
        "你是台股新聞分析助理。以下幾則今日財經新聞標題，請逐則判斷。\n"
        "只輸出 JSON 陣列（第 i 個物件對應第 i 則），每個物件格式：\n"
        '{"sentiment":"利多/利空/中性","horizon":"短期/長期/不明",'
        '"companies":["標題明確提到的『具體』上市櫃公司名，沒有或只是泛稱就給空陣列"],'
        '"note":"一句話解讀(≤30字,中立、非投資建議)"}\n'
        "規則：companies 只放具體公司名（不要寫『上市公司』這種泛稱）；"
        "指數/總經/政策/個人故事類 companies 給空陣列。\n"
        "只輸出 JSON 陣列，不要任何其他文字、不要 markdown、不要解釋。\n\n新聞：\n"
    )
    for i, t in enumerate(titles, 1):
        prompt += f"{i}. {t}\n"
    ans = call_ai(prompt)
    if not ans:
        return []
    a, b = ans.find("["), ans.rfind("]")
    if a < 0 or b < 0:
        return []
    try:
        arr = json.loads(ans[a:b + 1])
        return arr if isinstance(arr, list) else []
    except Exception as e:
        print(f"  ⚠ JSON 解析失敗：{e}")
        return []


def main():
    nd = json.loads((DATA_DIR / "news_live.json").read_text(encoding="utf-8"))
    news = nd.get("news", [])
    stocks = json.loads((DATA_DIR / "stocks_live.json").read_text(encoding="utf-8")).get("stocks", [])
    name_idx = build_name_index(stocks)
    print(f"[info] {len(news)} 則新聞，每批 {CHUNK} 則分析")

    done = 0
    for i in range(0, len(news), CHUNK):
        chunk = news[i:i + CHUNK]
        arr = analyze_chunk([n.get("title", "") for n in chunk])
        for n, a in zip(chunk, arr):
            if not isinstance(a, dict):
                continue
            n["ai_sentiment"] = (a.get("sentiment") or "中性").strip()
            n["ai_horizon"] = (a.get("horizon") or "不明").strip()
            n["ai_related"] = map_companies(a.get("companies"), name_idx)
            n["ai_note"] = (a.get("note") or "").strip()[:60]
            done += 1
        print(f"[info] {min(i + CHUNK, len(news))}/{len(news)} 完成")
        time.sleep(1)

    nd["news"] = news
    (DATA_DIR / "news_live.json").write_text(
        json.dumps(nd, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[done] {done}/{len(news)} 則已 AI 標註，寫回 news_live.json")


if __name__ == "__main__":
    main()
