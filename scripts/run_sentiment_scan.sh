#!/bin/bash
# 領富 AI · 輿情雷達盤後掃描 — 掃完自動 commit+push sentiment_live.json
# 排程（需用戶自行執行一次）：bash scripts/setup_sentiment_schedule.sh
set -e
cd "/Users/rayda/Library/CloudStorage/OneDrive-個人/Microsoft File Share/code/berich"
/opt/homebrew/bin/python3 scripts/fetch_sentiment.py
git pull --rebase origin main
git add data/sentiment_live.json
git diff --cached --quiet || { git commit -m "data(輿情雷達): 盤後自動掃描 $(date +%Y-%m-%d)"; git push origin main; }
