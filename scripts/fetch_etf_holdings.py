#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_etf_holdings.py — ETF 成分股（官方源：各投信每日 PCF API）

ETF 成分股無單一官方總表，法定公告人為「發行投信」。本腳本逐投信串接其 PCF API。
v1 已接：元大投信（YuantaETFs，ticker 直查，涵蓋 0050/0056/00940/00713/00850… 全元大系列）。
其他投信（國泰/富邦/復華/群益/中信…）端點各異，後續擴充（見 ADAPTERS）。

路由：依 stocks_live.json 的 ETF 名稱前綴判斷發行投信。
輸出 etf_holdings_live.json：{code:{asof, top:[{code,name,weight}], count}}

無需環境變數；由 run_all.py 每日盤後執行。
注意：投信 API 可能擋國外機房 IP；GitHub Actions 若抓不到，資料維持前次快照。
"""
import json
import time
import datetime
import ssl
import urllib.request
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
OUT = DATA_DIR / "etf_holdings_live.json"
TOP_N = 15        # 每檔最多存前 N 大成分
SLEEP = 0.3
_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (LeadFu-AI)", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.loads(r.read().decode("utf-8", "ignore"))
    except Exception:
        with urllib.request.urlopen(req, timeout=25, context=_CTX) as r:
            return json.loads(r.read().decode("utf-8", "ignore"))


# ── 元大投信 adapter ──
def yuanta(code, date):
    u = ("https://etfapi.yuantaetfs.com/ectranslation/api/bridge?APIType=ETFAPI"
         "&CompanyName=YUANTAFUNDS&FuncId=PCF/Daily&AppName=ETF&Device=3&Platform=ETF"
         f"&ticker={code}&date={date}&DeviceId=leadfu-ai")
    d = get_json(u)
    sw = ((d.get("FundWeights") or {}).get("StockWeights")) or []
    out = []
    for x in sw:
        nm = (x.get("name") or "").strip()
        w = x.get("weights")
        if not nm:
            continue
        out.append({"code": (x.get("code") or "").strip(), "name": nm,
                    "weight": round(w, 2) if isinstance(w, (int, float)) else None})
    return out


# 發行投信路由：ETF 名稱前綴 → adapter
ADAPTERS = [("元大", yuanta)]   # 後續加 ("國泰", cathay), ("富邦", fubon)…


def resolve_date():
    """找最近一個有 PCF 的交易日（用 0050 試 today..-6）。"""
    today = datetime.date.today()
    for back in range(0, 7):
        dt = today - datetime.timedelta(days=back)
        ds = dt.strftime("%Y%m%d")
        try:
            if yuanta("0050", ds):
                return ds
        except Exception:
            pass
        time.sleep(SLEEP)
    return None


def main():
    stocks = json.loads((DATA_DIR / "stocks_live.json").read_text(encoding="utf-8")).get("stocks", [])
    etfs = [s for s in stocks if s.get("category") == "ETF"]

    date = resolve_date()
    if not date:
        print("[error] 找不到有效 PCF 交易日（元大 API 可能擋 IP 或休市），維持前次資料")
        return
    print(f"[info] PCF 基準日 {date}；ETF {len(etfs)} 檔")

    prev = {}
    if OUT.exists():
        try:
            prev = json.loads(OUT.read_text(encoding="utf-8")).get("data", {})
        except Exception:
            prev = {}

    data = dict(prev)
    ok = 0
    for s in etfs:
        code, name = s.get("code"), s.get("name", "")
        adapter = next((fn for pre, fn in ADAPTERS if name.startswith(pre)), None)
        if not adapter:
            continue   # 該投信 adapter 尚未接（保留前次資料若有）
        try:
            hold = adapter(code, date)
            if hold:
                data[code] = {"asof": f"{date[:4]}-{date[4:6]}-{date[6:]}",
                              "top": hold[:TOP_N], "count": len(hold)}
                ok += 1
        except Exception as e:
            print(f"  [warn] {code} {name}: {e}")
        time.sleep(SLEEP)

    OUT.write_text(json.dumps({"updatedAt": datetime.date.today().isoformat(),
                               "asof": f"{date[:4]}-{date[4:6]}-{date[6:]}",
                               "source": "各投信每日 PCF（v1：元大投信）",
                               "count": len(data), "data": data}, ensure_ascii=False), encoding="utf-8")
    print(f"✅ ETF 成分股：本次更新 {ok} 檔（元大），累積 {len(data)} 檔 → etf_holdings_live.json")


if __name__ == "__main__":
    main()
