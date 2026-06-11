"""
一次性回填：TWSE TWT49U 除權息計算結果（年初至今）→ data/dividend_history.json
- 民國日期轉西元；「權值+息值」當每股配發金額；type 取「權/息」欄
- 與既有 history 以 (code, ex_date) 去重合併
- 上市為主（TPEx 之後可再接）；含息報酬以「息」型為主
"""
import json, ssl, sys, urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "dividend_history.json"
_CTX = ssl.create_default_context(); _CTX.check_hostname = False; _CTX.verify_mode = ssl.CERT_NONE

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (LeadFu-AI)"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r: return json.loads(r.read())
    except Exception:
        with urllib.request.urlopen(req, timeout=30, context=_CTX) as r: return json.loads(r.read())

def roc_to_iso(s):
    # "115年01月02日" → "2026-01-02"
    y, rest = s.split("年"); m, d = rest.rstrip("日").split("月")
    return f"{int(y)+1911}-{int(m):02d}-{int(d):02d}"

def main():
    today = datetime.now().strftime("%Y%m%d")
    d = get(f"https://www.twse.com.tw/exchangeReport/TWT49U?response=json&startDate={today[:4]}0101&endDate={today}")
    rows = d.get("data") or []
    hist = {}
    if OUT.exists():
        try: hist = json.loads(OUT.read_text(encoding="utf-8")).get("data", {})
        except Exception: hist = {}
    added = 0
    for r in rows:
        try:
            ex_date = roc_to_iso(r[0]); code = r[1].strip()
            cash = float(str(r[5]).replace(",", "")); typ = r[6].strip()
        except Exception:
            continue
        lst = hist.setdefault(code, [])
        if any(x.get("ex_date") == ex_date for x in lst): continue
        lst.append({"ex_date": ex_date, "cash": cash, "type": typ})
        lst.sort(key=lambda x: x["ex_date"])
        added += 1
    OUT.write_text(json.dumps({"updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M"),
                               "note": "配息歷史累積（fetch_dividend 每日 + TWT49U 年度回填；上市為主）",
                               "data": hist}, ensure_ascii=False), encoding="utf-8")
    print(f"✅ 回填 +{added} 筆 → 共 {sum(len(v) for v in hist.values())} 筆 / {len(hist)} 檔")

if __name__ == "__main__":
    sys.exit(main())
