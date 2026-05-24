# 領富 AI / LeadFu — Claude 跨機接手指引

> **這份檔案的用途**：另一台 Claude 透過 OneDrive 拿到專案後，**讀這份就能立刻接手目前進度**。
> 上次更新：2026-05-21（這台 Claude 寫的，請以最新 git log 為準）
> 目前版本：**v3.17.3**（sw.js 內 `VERSION` 常數）

---

## 🔥 你（另一台 Claude）接手前必看

1. **使用者**：Rayda（rayda0114@gmail.com），不寫程式。是這個專案的產品/業務 owner。
2. **正式網址**：https://leadfuai.com（Cloudflare Worker 部署，push 到 main 自動部署）
3. **本地路徑**：`C:\Users\rayda\OneDrive\Microsoft File Share\code\berich\`
4. **GitHub**：https://github.com/Rayda0114/leadfu-ai
5. **目前正在做的事（卡在這）**：**用戶正在申請綠界 ECPay 個人會員**，金流上線後立刻啟用 VIP 變現

---

## 📍 用戶當前狀態（接手最重要）

### 🟡 進行中：綠界 ECPay 個人會員申請
- 已選類別：**專業服務類 → 電腦程式設計/系統工程**
- 商品說明應填：「財經資訊整理訂閱服務（VIP 會員月費）」，**絕對避免「投資/投顧/諮詢/明牌」等字眼**
- 環境照：拍工作桌
- 產品展示間照：截圖 leadfuai.com/pages/vip.html（有 NT$199/NT$499 價目表）
- 審核時間：3-5 個工作天
- 通過後拿到 `MerchantID` / `HashKey` / `HashIV` → 來找 Claude 做技術串接
- **金流通了 → 啟用 FAIR_VALUE_GATE = true → VIP 開始變現**

### ⏸ 已決策但未執行（等金流通）
- **合理區間 freemium gating**：程式已寫好、開關在 `js/main.js` 的 `FAIR_VALUE_GATE = false`
  - 開關 ON 時：首頁 TOP 5 名字鎖住（顯示數據 -88% ⭐⭐⭐⭐⭐ 合理區間，但名字 → 🔒 解鎖看是哪檔）
  - 完整排行頁第 6-10 名免費、TOP 5 鎖 VIP
- **VIP 訂閱**：限時 5 折 NT$199（進階）/ NT$499（旗艦），文案已寫好但 subscribe 按鈕還沒接金流（alert 提示）

---

## 🏗️ 架構速覽

### 部署
- **Cloudflare Worker**（靜態資產 + `/api/ask` AI 後端 + `/api/quote` TWSE MIS 即時報價代理）
- `wrangler.toml` 設定，**不要再用 wrangler.jsonc**（v3.90 不支援）
- GitHub Actions：push main → 自動 wrangler deploy（無需手動）
- GitHub Actions cron：每日 15:00 跑 `scripts/run_all.py` 抓資料 commit（會看到 `data: 每日更新` 提交）

### 資料層
- 全部從 TWSE / TPEx / MOPS 官方 OpenAPI 抓
- `data/stocks_live.json` 是主表（2,297 檔，上市+上櫃+興櫃）
- `data/fair_value_live.json` 是合理區間（演算法在 `scripts/calc_fair_value.py`）
- 其他：`companies_live.json` / `revenue_live.json` / `institutional_live.json` / `margin_live.json` / `sbl_live.json` / `klines.json` / `news_live.json` / `weekly_report.json` / `indicators_live.json` / `ipo_live.json` 等

### AI（重要）
- **主力**：Nvidia NIM `qwen/qwen3-next-80b-a3b-instruct`
- **fallback**：Google Gemini 2.0 Flash（每日 1500 req 免費）
- 兩個 API key 都在 Cloudflare Worker Variables（Secret）
- 系統提示在 `worker.js` 的 `SYSTEM_PROMPT`：
  - 規則 #0：**資料紀律**（沒資料拒答、不准用記憶編價格、結尾附資料來源+時間、即時報價優先）
  - 規則 #1：**合理區間引用規則**（必引用 + 結構化卡片格式 + ⭐ emoji）
  - 嚴禁推介字眼，二次過濾在 `filterCompliance()`
  - **市場摘要場景**：用 `context.isMarketBrief = true` 跳過股票代號偵測（避免「下跌 1143 家」被誤判為股票 1143）

### 前端
- **vanilla HTML + CSS + JS**（沒用框架，直接 fetch JSON 渲染）
- `js/main.js` 是主程式（3000+ 行），`js/auth.js` 是 Supabase 認證
- `window.LeadFu` 命名空間（`L.data.stocks` / `L.data.fairValue` 等）
- `window.LeadFuAuth` Supabase 認證
- `window.LeadFuTTS` 文字朗讀

### Service Worker（v3.17.3）
- CSS / JS / HTML / data JSON 都用 **network-first**（避免用戶卡舊版，bug 修完當下生效）
- 圖示 / manifest 用 stale-while-revalidate
- 升 SW 版本 = 改 `sw.js` 開頭的 `const VERSION = "v3.x.y"`
- **同時要改 `index.html` 內 `?v=3.x.y`**（CSS + main.js cache-bust，這是最後保險）

---

## 🛠️ 重要的可重用工具 / 模式

### 1. `.h-scroll` 工具 class（橫向滑動）
- 在 `css/style.css` 約 4070 行
- 桌面 no-op、手機強制橫向滑動
- 必含 `overscroll-behavior-x: contain` 防 iOS 彈性回彈
- 不用 scroll-snap-type（會被用戶感到「拉回」）
- modifier：`.h-scroll-narrow`（46vw 卡）/ `.h-scroll-wide`（88vw）/ `.h-scroll-mini`（auto）/ `.h-scroll-no-fade`
- 已套：hero 卡 / 合理區間 TOP 5 / 熱門題材 / 學習中心 4 grid / VIP 三大價值 / 競品比較 / 產業分類
- ⚠️ 新聞列表**故意不套**（用戶測試後說橫滑不直觀，已回原列表）

### 2. `?ask=` URL 參數（首頁 AI 對話自動 prefill）
- 任何頁面 `<a href="/?ask=2330+合理嗎">` → 跳首頁 → AI 對話框自動 prefill 並送出
- 邏輯在 index.html 末段 chat init 區
- 用法：「問 AI」按鈕 / 卡片 CTA 都導向此

### 3. `data-stat="stockCount"` 動態股數
- HTML：`<span data-stat="stockCount">2,300+</span>`
- main.js `loadLiveData()` 自動把 stocks_live.json 的真實 stockCount 替換進去
- 用來解決之前 14 個檔案硬編碼 2,310 不一致的問題

### 4. `FAIR_VALUE_GATE` 開關（合理區間 VIP 分級）
- `js/main.js` 頂部 `const FAIR_VALUE_GATE = false;`
- 金流上線那天改 true → TOP 5 名字鎖住、導向 VIP 頁
- CSS 樣式 `.fv-low-card-locked` 等已備好

### 5. 資產版本 cache-bust
- `<link rel="stylesheet" href="css/style.css?v=3.17.3">` 跟 `<script src="js/main.js?v=3.17.3">`
- 每次改 CSS/JS 必須 bump 版本號（連同 sw.js VERSION 一起）

---

## 📚 今日這個 session 做的事（2026-05-20 ~ 21）

### 大型功能 / 改造
1. **SEO 衝刺**（用戶擔心 Google 找不到網站）
   - 首頁加品牌 FAQ + FAQPage schema（搶「領富 AI 是詐騙嗎」品牌查詢）
   - 寫 3 篇高搜尋量 SEO 文章：存股 / 除權息 / 未上市可以買嗎
   - sitemap 更新、用戶已去 Search Console 提交
   - 學習中心現有 14 篇文章
2. **美股專區「即將開放」teaser**（`pages/us-market.html`）
   - 策略：走 freemium（不全鎖 VIP）— 因美股真金礦是 IB 開戶分潤
   - 導航列加「🌎 美股 即將開放」
   - 首頁加金色 teaser banner
3. **修兩個重要 bug**
   - daily brief「代號 1143 誤判」（worker askHandler 把「下跌 1143 家」當股票代號）
   - daily brief「日期 5/18 幻覺」（AI 沒 dataMeta 但被強制附時間 → 編了個 5/18）
   - 修法：傳真實 dataMeta + isMarketBrief 旗標跳過股票偵測
4. **合理區間 freemium gating 程式（開關現在關著）**
   - `FAIR_VALUE_GATE = false` 預設
   - 開啟邏輯都寫好了
5. **手機板 UI 修一輪**
   - 即時行情列 ticker 跟 live-quote-bar 左緣對齊（兩個都用 .container）
   - lq-watchlist 拿掉 margin-left:auto，換行靠左對齊
   - lq-meta 加 margin-left:auto 讓更新時間保持靠右

### 微調 / fix
- 首頁補 canonical + og:url（之前漏了）
- 麥克風在 iOS Chrome 不再隱藏，改成跳引導 modal 教用戶加到主畫面
- 30+ commits，從 v3.13.x → v3.17.3

---

## 🚧 待辦清單（按優先序）

### 🔥 P0：金流 → 立刻變現
1. **用戶申請綠界個人會員**（進行中，3-5 天）
2. 通過後串接綠界到 vip.html 的 subscribe button
3. 串好後啟用 `FAIR_VALUE_GATE = true`
4. 接著做完整排行頁的 6-10 免費 / 1-5 鎖

### 🟡 P1：擴張
5. **美股專區正式開發**（用戶要先開 IB 帳戶拿推薦連結）
   - 100 檔精選（七巨頭 + 半導體 + ETF + 退休族最愛）
   - 用 Finnhub API（60 req/min 免費）
   - 算美股合理區間（calc_fair_value.py 改寫成美股版）
6. **券商開戶分潤頁**（永豐/國泰/玉山 + IB）
   - 詳細已存在 `memory/project_leadfu_monetization_brokerage.md`

### 🟢 P2：留存
7. **LINE Login + 警示推播**（多次提及但未做）
8. **再 2-3 篇 SEO 文章**（ETF 0050 vs 0056、興櫃怎麼買、P/B 河流圖）

### ⚪ 用戶自己要做（不是 Claude 的事）
- 公司登記（NT$ 待查）
- 商標申請（NT$14,000）
- 165 反詐騙申訴（曾被冒用）
- LINE 灰盾（等公司）

---

## ⚠️ 接手雷區（這些別踩）

1. **不要再寫「未上市」當主打**（用戶之前被詐騙集團冒用「未上市飆股」，已把網站定位改成「上市+上櫃+興櫃全市場」，但保留「未上市可以買嗎」防詐文章是 OK 的）
2. **「2,300+」是動態的，別硬編 2,310**（之前犯過）
3. **AI 系統提示已有資料紀律規則**（不能編價格、要附資料源+時間），改 prompt 時別覆蓋這些
4. **scroll-snap 用 mandatory 會讓用戶感到「滑了被拉回」**（手機 UX 雷區），用 none 自由滑動 + `overscroll-behavior-x: contain`
5. **iOS Chrome 沒 SpeechRecognition API**（用 WKWebView），所以麥克風功能只在 Safari / PWA 可用
6. **跨機協作**：另一台 push 過代碼，記得 `git pull --rebase` 再 push（曾發生 rejected）

---

## 📦 Memory 索引（這台 Claude 本機 `.claude/projects` 內，不會同步）

如果你（另一台）也是 Claude Code，建議查的 memory 索引：
- `project_berich_clone.md`（這個專案的基礎設定）
- `project_leadfu_strategy.md`（訂閱策略 + Roadmap）
- `project_leadfu_monetization_brokerage.md`（券商分潤研究）
- `user_business_context.md`（Rayda 的整體業務）
- `reference_ai_shared_memory.md`（Acewin 專案用的跨 AI 協作格式，可參考）

---

## 🎯 接手第一句該問用戶的話（如果你不確定）

> 「我看了 LEADFU_HANDOFF.md，目前狀態是『綠界個人會員申請中、等過件做金流串接』。你現在想做的是：(A) 等綠界、(B) 同時開美股專區、(C) 別的？」

---

**最後更新者：** Claude（這台機器，session 約 100+ 輪對話完成上面所有事）
**最新 commit hash**：請 `git log -1` 查
**v3.17.3 對應 commit**：c97a291 `feat: 合理區間 VIP 分級程式 + 開關（現在關著）`
