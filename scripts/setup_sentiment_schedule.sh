#!/bin/bash
# 一鍵安裝/移除 輿情雷達盤後排程（launchd，每日 15:40）
# ⚠ launchd 被 macOS TCC 擋住讀 OneDrive(CloudStorage) → 排程跑「本機 runner clone」：
#   ~/.hermes/leadfu-runner（git clone 本 repo）+ ~/.hermes/run_sentiment_scan.sh（pull→掃→push）
# 安裝：bash scripts/setup_sentiment_schedule.sh
# 移除：bash scripts/setup_sentiment_schedule.sh --uninstall
PLIST=~/Library/LaunchAgents/com.lingfu.sentiment-scan.plist
if [ "$1" = "--uninstall" ]; then
  launchctl unload "$PLIST" 2>/dev/null; rm -f "$PLIST"; echo "已移除排程"; exit 0
fi
mkdir -p ~/.hermes/logs
cat > "$PLIST" <<'PL'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.lingfu.sentiment-scan</string>
  <key>ProgramArguments</key><array>
    <string>/bin/bash</string>
    <string>/Users/rayda/.hermes/run_sentiment_scan.sh</string>
  </array>
  <key>StartCalendarInterval</key><dict><key>Hour</key><integer>15</integer><key>Minute</key><integer>40</integer></dict>
  <key>StandardOutPath</key><string>/Users/rayda/.hermes/logs/sentiment-scan.log</string>
  <key>StandardErrorPath</key><string>/Users/rayda/.hermes/logs/sentiment-scan.err.log</string>
</dict></plist>
PL
launchctl unload "$PLIST" 2>/dev/null
launchctl load "$PLIST" && echo "✅ 排程已啟用：每日 15:40 盤後掃描＋自動部署"
