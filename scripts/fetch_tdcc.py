"""
領富 AI · 集保股權分散表（TDCC 開放資料，每週五資料、週六發布）
千張大戶持股比率 = 持股分級 15（1,000,001 股以上）之占比。
累積近 8 週歷史 → 週變化、連續增減週數（守門訊號：大戶連 N 週減持）。
資料已是同日期則跳過（可每日排程、實際每週更新一次）。
輸出：data/tdcc_live.json
"""
import csv, io, json, subprocess, sys, urllib.request
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "tdcc_live.json"
URL = "https://opendata.tdcc.com.tw/getOD.ashx?id=1-5"
KEEP_WEEKS = 8

def main():
    # TDCC 憑證缺 SKI 擴展，Python 3.14 嚴格驗證會擋 → 用 curl（驗證正常）
    raw = subprocess.run(["curl", "-s", "--max-time", "120", "-A", "Mozilla/5.0", URL],
                         capture_output=True, check=True).stdout.decode("utf-8-sig", "ignore")
    rows = list(csv.reader(io.StringIO(raw)))
    if len(rows) < 100:
        print("❌ 資料異常（太少），不更新"); return 1
    date = rows[1][0].strip()
    old = {}
    if OUT.exists():
        try: old = json.loads(OUT.read_text(encoding="utf-8"))
        except Exception: old = {}
    if old.get("date") == date:
        print(f"資料日期 {date} 未變，跳過"); return 0

    cur = {}   # code -> {big_ratio, big_holders, holders}
    for r in rows[1:]:
        if len(r) < 6: continue
        code = r[1].strip()
        lvl = r[2].strip()
        if lvl == "15":
            try:
                cur.setdefault(code, {})["big_ratio"] = round(float(r[5]), 2)
                cur[code]["big_holders"] = int(r[3])
            except Exception: pass
        elif lvl == "17":
            try: cur.setdefault(code, {})["holders"] = int(r[3])
            except Exception: pass

    old_data = old.get("data", {})
    data = {}
    for code, v in cur.items():
        if "big_ratio" not in v: continue
        weeks = [w for w in (old_data.get(code, {}).get("weeks") or []) if w[0] != date]
        weeks.append([date, v["big_ratio"]])
        weeks = weeks[-KEEP_WEEKS:]
        wow = round(weeks[-1][1] - weeks[-2][1], 2) if len(weeks) >= 2 else None
        # 連續增/減週數
        streak, sdir = 0, 0
        for i in range(len(weeks) - 1, 0, -1):
            d = weeks[i][1] - weeks[i-1][1]
            sg = 1 if d > 0 else (-1 if d < 0 else 0)
            if sg == 0: break
            if sdir == 0: sdir = sg
            if sg != sdir: break
            streak += 1
        data[code] = {"big_ratio": v["big_ratio"], "big_holders": v.get("big_holders"),
                      "holders": v.get("holders"), "wow": wow,
                      "streak": streak * sdir, "weeks": weeks}
    out = {"updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M"), "date": date,
           "source": "TDCC 集保結算所開放資料（股權分散表，每週更新）", "count": len(data), "data": data}
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"✅ tdcc_live.json：{len(data)} 檔（資料日 {date}）")
    return 0

if __name__ == "__main__":
    sys.exit(main())
