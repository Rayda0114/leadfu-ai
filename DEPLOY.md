# 領富 AI · 部署與自動更新指南

## 🏗️ 目前部署狀態

- **網址**：https://leadfuai.com
- **部署方式**：Netlify Drop（手動拖 zip）
- **資料更新**：手動跑 `python scripts/run_all.py` 後重新打包

## 🚀 升級到 GitHub + Netlify 自動部署

完成這 4 步後，每天台灣時間 15:00 GitHub Actions 會自動：
1. 跑全部 4 個爬蟲腳本
2. 把更新的 `data/*.json` commit 回 GitHub
3. Netlify 偵測到 push 自動重新部署
4. 你的網站每天自動有最新資料，完全免人工

### 步驟 1：把專案推到 GitHub

```powershell
# 在 berich 目錄
cd "C:\Users\rayda\OneDrive\Microsoft File Share\code\berich"

# 初始化 git（若尚未）
git init
git add .
git commit -m "initial: 領富 AI 上線"

# 建立 GitHub repo（用 gh CLI 或網頁建好）
# 假設 repo 名稱為 leadfu-ai：
git branch -M main
git remote add origin https://github.com/<你的 username>/leadfu-ai.git
git push -u origin main
```

如果還沒裝 gh CLI：到 https://github.com/new 用網頁建 repo（**private 或 public 都行**），複製 git remote 指令。

### 步驟 2：在 Netlify 連接 GitHub repo

1. 進 https://app.netlify.com/projects/friendly-mousse-33de3d
2. 左側選 **Project configuration** → **Build & deploy**
3. 找 **Build settings** → **Link to repository**
4. 選 GitHub → 授權 → 選擇 `leadfu-ai` repo
5. Branch 選 `main`
6. Build command 留空（靜態網站）
7. Publish directory 填 `.`（根目錄）
8. 點 **Save**

完成後每次 `git push` 都會自動部署，不用再拖 zip。

### 步驟 3：驗證 GitHub Actions 已啟用

1. 進你的 GitHub repo → **Actions** 頁籤
2. 應該看到「領富 AI · 每日資料更新」workflow
3. 點 **Run workflow** 手動跑一次測試

如果 Actions 沒有自動執行的權限：
- Settings → Actions → General
- Workflow permissions → 選 **Read and write permissions**
- 勾選 **Allow GitHub Actions to create and approve pull requests**
- Save

### 步驟 4：監控自動更新

- GitHub Actions 每日 UTC 07:00（台灣 15:00）週一至五自動跑
- 每次跑完會看到一個 commit 「data: 每日更新 (YYYY-MM-DD)」
- Netlify 收到 push 後約 30 秒部署完成
- 網站 console 會印「✅ XXX 檔 TPEx 即時報價 (日期)」

## 📦 手動更新流程（沒有 GitHub 時）

```powershell
cd "C:\Users\rayda\OneDrive\Microsoft File Share\code\berich"
python scripts/run_all.py   # 跑全部 4 個爬蟲
# 然後重新打包，拖到 Netlify
```

## 🔧 維護注意事項

| 問題 | 解法 |
|---|---|
| TPEx API 改版 | 改 `scripts/fetch_*.py` 對應的端點和欄位名 |
| 想加新資料源 | 寫新的 `fetch_xxx.py`，加進 `run_all.py` 的 SCRIPTS 列表 |
| Action 跑失敗 | 看 Actions 頁面的 log，通常是 TPEx 暫時不通，明天會自動再試 |
| 資料變太大 | 各 fetch 腳本都有上限保護（新聞 30 則、公告 60 筆、K 線 30 天） |

## 📂 資料檔案結構

```
data/
├── stocks_live.json          # 興櫃 ~340 檔即時報價
├── news_live.json            # 30 則最新財經新聞
├── announcements_live.json   # 60 筆重大訊息/警示
├── klines.json               # K 線歷史（每天累積）
└── _raw_tpex_YYYY-MM-DD.json # 原始 TPEx 備份（不用上傳）
```

`.gitignore` 建議排除 `data/_raw_*.json`（備份檔太大且不需要部署）。
