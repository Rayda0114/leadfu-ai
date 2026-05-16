"""
領富 AI · 大股東名單抓取
資料來源：MOPS 公開資訊觀測站 t187ap02（公司主要股東）

端點：
  上市：https://mopsfin.twse.com.tw/opendata/t187ap02_L.csv
  上櫃：https://mopsfin.twse.com.tw/opendata/t187ap02_O.csv

每檔個股紀錄：
  shareholders: [大股東 1, 大股東 2, ...]（多筆，照原檔順序）
  count:        股東數

注意：MOPS 的 t187ap02 只給「公司主要股東名單」（持股 ≥ 10% 法人或實質受益人），
      不含個人董監持股數量。台股缺少完整 daily 內部人持股 OpenAPI，
      故此處以「大股東名單」呈現，已是目前最容易取得的內部人指標。
"""

import csv
import io
import json
import ssl
import sys
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36"

_INSECURE_CTX = ssl.create_default_context()
_INSECURE_CTX.check_hostname = False
_INSECURE_CTX.verify_mode = ssl.CERT_NONE

ENDPOINTS = [
    ("上市", "https://mopsfin.twse.com.tw/opendata/t187ap02_L.csv"),
    ("上櫃", "https://mopsfin.twse.com.tw/opendata/t187ap02_O.csv"),
]


def fetch_csv(url):
    req = Request(url, headers={"User-Agent": UA})
    try:
        with urlopen(req, timeout=30) as r:
            return r.read().decode("utf-8-sig", errors="ignore")
    except (URLError, ssl.SSLError):
        with urlopen(req, timeout=30, context=_INSECURE_CTX) as r:
            return r.read().decode("utf-8-sig", errors="ignore")


def parse_csv(text, market):
    """
    Headers: 出表日期, 公司代號, 公司名稱, 大股東名稱
    一檔公司會有多列（每位大股東一列），需要 groupby。
    """
    out = {}
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        code = (row.get("公司代號") or "").strip()
        name = (row.get("公司名稱") or "").strip()
        sh = (row.get("大股東名稱") or "").strip()
        if not code or not sh:
            continue
        if code not in out:
            out[code] = {
                "code": code,
                "name": name,
                "shareholders": [],
                "market": market,
            }
        if sh not in out[code]["shareholders"]:
            out[code]["shareholders"].append(sh)
    # 加上 count
    for v in out.values():
        v["count"] = len(v["shareholders"])
    return out


def main():
    print("=" * 60)
    print(f"大股東名單抓取 ・ {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 60)

    combined = {}
    for market, url in ENDPOINTS:
        try:
            print(f"\n▶ {market}: {url.rsplit('/', 1)[-1]}")
            text = fetch_csv(url)
            data = parse_csv(text, market)
            print(f"  ✅ {len(data)} 檔公司")
            combined.update(data)
        except Exception as e:
            print(f"  ❌ {e}")

    if not combined:
        print("\n❌ 未取得任何資料")
        sys.exit(1)

    payload = {
        "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source": "MOPS 公開資訊觀測站 t187ap02（主要股東名單）",
        "count": len(combined),
        "data": combined,
    }
    out = DATA_DIR / "insider_live.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 已輸出：{out.relative_to(ROOT)} ({len(combined)} 檔)")

    # 範例：股東最多的前 3 檔
    top = sorted(combined.values(), key=lambda x: x["count"], reverse=True)[:5]
    print("\n--- 大股東數最多前 5 ---")
    for s in top:
        print(f"  {s['code']} {s['name']:<12} {s['count']} 位股東")
        for sh in s["shareholders"][:3]:
            print(f"    · {sh}")


if __name__ == "__main__":
    main()
