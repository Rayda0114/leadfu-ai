#!/usr/bin/env python3
"""
產生「美股精選 100 全清單」靜態內部連結，填進 pages/us-market.html 的 US-INDEX 標記之間。
目的：給爬蟲一份非 JS 的 /us/{ticker} 連結索引（卡片是 JS 動態產生、爬蟲較難吃到），加速收錄。
用法：python3 scripts/gen_us_index.py   （改了 us_stocks_meta.json 的 100 檔名單後重跑即可）
"""
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
META = ROOT / "data" / "us_stocks_meta.json"
PAGE = ROOT / "pages" / "us-market.html"
START, END = "<!-- US-INDEX:start -->", "<!-- US-INDEX:end -->"


def esc(s):
    return (str(s or "")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def main():
    meta = json.loads(META.read_text(encoding="utf-8"))
    data = meta.get("data", {})
    # ticker -> entry（容錯 dict / list 兩種格式）
    entries = list(data.values()) if isinstance(data, dict) else list(data)
    # 分類順序：用 meta.categories；沒列到的歸「其他」
    cats = meta.get("categories") or []
    by_cat = {c: [] for c in cats}
    for e in entries:
        if not e or not e.get("ticker"):
            continue
        c = e.get("category") or "其他"
        by_cat.setdefault(c, []).append(e)

    blocks, total = [], 0
    for c, items in by_cat.items():
        if not items:
            continue
        items.sort(key=lambda x: x.get("ticker", ""))
        links = "".join(
            f'<a href="/us/{esc(e["ticker"])}"><b>{esc(e["ticker"])}</b> {esc(e.get("name_zh") or "")}</a>'
            for e in items
        )
        total += len(items)
        blocks.append(f'<div class="us-idx-group"><h3>{esc(c)}（{len(items)}）</h3><div class="us-idx-links">{links}</div></div>')

    inner = "\n    " + "\n    ".join(blocks) + "\n    "
    html = PAGE.read_text(encoding="utf-8")
    new = re.sub(
        re.escape(START) + r".*?" + re.escape(END),
        START + inner + END,
        html,
        flags=re.S,
    )
    if new == html and START not in html:
        raise SystemExit(f"找不到標記 {START} … {END}，請先在 us-market.html 加上標記")
    PAGE.write_text(new, encoding="utf-8")
    print(f"✅ 已產生美股全清單 {total} 檔（{len([k for k,v in by_cat.items() if v])} 分類）→ {PAGE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
