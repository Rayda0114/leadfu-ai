# 領富 AI / LeadFu — Claude 跨機接手指引

> **這份檔案的用途**：另一台 Claude 透過 OneDrive 拿到專案後,**讀這份就能立刻接手目前進度**。
> 上次更新：2026-06-02（這台 Claude 寫的，請以最新 git log 為準）
> 目前版本：**v3.19.0**（sw.js 內 `VERSION` 常數）

---

## 🔥 你（另一台 Claude）接手前必看

1. **使用者**：Rayda（rayda0114@gmail.com），不寫程式。是這個專案的產品/業務 owner。
2. **正式網址**：https://leadfuai.com（Cloudflare Worker 部署，push 到 main 自動部署）
3. **本地路徑**：
   - macOS：`/Users/rayda/Library/CloudStorage/OneDrive-個人/Microsoft File Share/code/berich/`
   - Windows（不再用）：`C:\Users\rayda\OneDrive\Microsoft File Share\code\berich\`
4. **GitHub**：https://github.com/Rayda0114/leadfu-ai
5. **目前主要卡點**：**綠界 ECPay 個人會員被拒**（AI 內容政策），用戶在打藍新/PayUni 金流電話找替代

---

## 📍 用戶當前狀態（接手最重要）

### 🔴 綠界 ECPay 被拒（2026-05-24）
- 用戶申請「專業服務類 → 電腦程式設計」、商品說明寫「財經資訊整理訂閱服務」都沒用
- **被拒原因**：「自 115/3/16 起 AI 相關內容需申請特約賣家」（個人會員不收）
- 特約賣家 = 需公司資格 → 1-3 個月（公司登記 + 申請）
- **替代金流方案**（用戶在打電話）：
  - 藍新金流 NewebPay（02-2786-3655，個人可申請，免年費）
  - PAYUNi 統一金流（完全免年費免設定費，最低風險）
  - MYPAY（主打定期定額扣款）
  - PayPal / Patreon（短期手動方案）
  - Stripe（需美國 LLC，長期）
- **同時保險策略**：vip.html subscribe 按鈕之後可以暫改成「LINE 客服私訊開通」(尚未做)，先驗證需求

### 🟡 IB / Firstrade Affiliate（用戶要動手）
- 美股變現的真金礦不是訂閱、是 IB 開戶分潤
- 用戶要先開 IB 個人帳戶 → 拿 referral 連結
- 同時申請 Firstrade Affiliate（透過聯盟網 Affiliates.One）
- 連結拿到後填到 `pages/us-market.html` 內的 broker CTA 按鈕（目前是 disabled placeholder）

### ⏸ 已寫好程式但等金流的東西
- `FAIR_VALUE_GATE = false`（js/main.js 頂部）— 金流通改 true 啟用 VIP 鎖名單
- vip.html subscribe 按鈕還是 alert（沒接金流）

---

## 🏗️ 架構速覽

### 部署
- **Cloudflare Worker**（靜態資產 + `/api/ask` AI 後端 + `/api/quote` TWSE MIS 即時報價代理）
- `wrangler.toml` 設定（**不要再用 wrangler.jsonc**，v3.90 不支援）
- GitHub Actions：push main → 自動 wrangler deploy（無需手動）
- GitHub Actions cron：
  - `daily-data-update.yml`：每天 UTC 07:00（台北 15:00）抓台股資料
  - `weekly-report.yml`：每週生產業週報
  - `us-data-update.yml` ⭐ **新增 2026-06-02**：每天 UTC 21:30（台北 05:30）抓美股 100 檔 yfinance 報價

### 資料層
**台股**（從 TWSE / TPEx / MOPS 官方 OpenAPI 抓）
- `data/stocks_live.json` — 主表（2,300+ 檔，上市+上櫃+興櫃）
- `data/fair_value_live.json` — 合理區間（演算法 `scripts/calc_fair_value.py`）
- 其他：companies / revenue / institutional / margin / sbl / klines / news / weekly_report / indicators / ipo

**美股** ⭐ **新增 2026-06-02**（從 Yahoo Finance via yfinance 抓）
- `data/us_stocks_meta.json` — 手寫 metadata（100 檔精選：七巨頭 7 / 半導體 10 / 大盤 ETF 8 / 配息 ETF 12 / 行業 ETF 10 / 道瓊藍籌 15 / 配息個股 12 / 中概 ADR 6 / 加密 5 / 退休防禦 8 / 其他熱門 7）
- `data/us_stocks_live.json` — yfinance 抓的 live 快照（price / change_pct / pe_ratio / yield_pct / market_cap / 52w_high/low / sector）
- `scripts/fetch_us_snapshot.py` — 抓取腳本，每天 cron 自動跑
- 本地跑：`.venv/bin/python scripts/fetch_us_snapshot.py`（macOS 用 venv 隔離，`.venv/` 已加 .gitignore）

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

### Service Worker（v3.19.0）
- CSS / JS / HTML / data JSON 都用 **network-first**（避免用戶卡舊版，bug 修完當下生效）
- 圖示 / manifest 用 stale-while-revalidate
- 升 SW 版本 = 改 `sw.js` 開頭的 `const VERSION = "v3.x.y"`
- **同時要改 `index.html` 跟 `pages/us-market.html` 內 `?v=3.x.y`**（CSS + main.js + 動態 fetch 的 cache-bust）

---

## 🛠️ 重要的可重用工具 / 模式

### 1. `.h-scroll` 工具 class（橫向滑動）
- 在 `css/style.css` 約 4070 行
- 桌面 no-op、手機強制橫向滑動
- 必含 `overscroll-behavior-x: contain` 防 iOS 彈性回彈
- 不用 scroll-snap-type（會被用戶感到「拉回」）
- modifier：`.h-scroll-narrow`（46vw 卡）/ `.h-scroll-wide`（88vw）/ `.h-scroll-mini`（auto）/ `.h-scroll-no-fade`
- ⚠️ 新聞列表**故意不套**（用戶測試後說橫滑不直觀，已回原列表）

### 2. `?ask=` URL 參數（首頁 AI 對話自動 prefill）
- 任何頁面 `<a href="/?ask=2330+合理嗎">` → 跳首頁 → AI 對話框自動 prefill 並送出
- 邏輯在 index.html 末段 chat init 區

### 3. `data-stat="stockCount"` 動態股數
- HTML：`<span data-stat="stockCount">2,300+</span>`
- main.js `loadLiveData()` 自動把 stocks_live.json 的真實 stockCount 替換進去

### 4. `FAIR_VALUE_GATE` 開關（合理區間 VIP 分級）
- `js/main.js` 頂部 `const FAIR_VALUE_GATE = false;`
- 金流上線那天改 true → TOP 5 名字鎖住、導向 VIP 頁
- CSS 樣式 `.fv-low-card-locked` 等已備好

### 5. 資產版本 cache-bust
- `<link rel="stylesheet" href="css/style.css?v=3.x.y">` 跟 `<script src="js/main.js?v=3.x.y">`
- 每次改 CSS/JS 必須 bump 版本號（連同 sw.js VERSION 一起）
- ⚠️ us-market.html 內也有 `?v=` 引用 fetch metadata JSON、要同步 bump

### 6. ⭐ 首頁 hero「ChatGPT vs 領富 AI」對比區塊動態化（新 2026-06-02）
- 之前 2330 合理區間數字 hardcode 在 index.html line 308-320，過期了
- 現在：5 個 DOM 加 id (`fvDemoMarker / fvDemoLow / fvDemoHigh / fvDemoMeta / fvDemoNote`)
- index.html 行末 inline script 等 `window.LeadFu.ready` 後從 `LeadFu.data.fairValue["2330"]` 動態覆蓋
- 失敗保留 HTML fallback（不破畫面）
- 每天 cron 跑完，這個 demo 也自動跟著最新

### 7. ⭐ 美股 P1+P2 stack（新 2026-06-02）
- `pages/us-market.html` 不再是 teaser，是 100 檔卡片網格
- 11 個分類 tab + ticker/中英文/產業搜尋 + 5 種排序 dropdown（預設/市值/殖利率/漲幅/PE）
- 每張卡片：Clearbit logo + ticker + 中英文 + 分類 + 一句話描述 + price/漲跌%/PE/yield + Yahoo Finance 外連
- **美股慣例 #16A34A 綠漲 / #EF4444 紅跌**（跟台股相反！別搞錯）
- IB / Firstrade Affiliate banner 是 disabled placeholder（等用戶拿到連結填入）
- Logo fallback 用「同時 render img + 隱藏 div、onerror 切換 display」模式（**不要用 outerHTML inline 替換、會 HTML injection 切斷 attribute、之前踩過 → v3.18.1 修**）

### 8. 行尾統一 (LF)
- 整 repo CRLF/LF 已治標 — 本機跑 `git config core.autocrlf input`
- 未來如果同步 OneDrive 又灌 CRLF 進來：`git checkout -- .` 重簽出
- 根治：建 `.gitattributes` 強制 `* text=auto eol=lf` + `git add --renormalize .` + commit（沒做，等需要再做）

---

## 📚 今晚這個 session 做的事（2026-06-02，~12 commits）

### 環境 / 工具設定
1. **跨機 memory 整合** — 從 OneDrive backup 載入 3 個 LeadFu memory 檔，避開 user_business_context.md（內容是 Acewin 業務脈絡、會污染 LeadFu pool）
2. **CRLF/LF 假改動修法** — OneDrive 從 Windows 同步過來的 CRLF 讓 macOS git 顯示 60 個檔有「改動」（其實沒）。設 `core.autocrlf input` + `git checkout -- .` 全清掉
3. **gh CLI 裝設** — `brew install gh` + `gh auth login`（device flow + 選 Rayda0114 帳號）
   - ⚠️ **雷區**：這台 macOS 有兩個 GH 帳號（Rayda0114 + getcrosslingo），gh 預設 active = getcrosslingo（沒 leadfu-ai 權限）→ push 失敗。修法：`gh auth switch --user Rayda0114`
4. **git author 改 gmail** — `git config user.email rayda0114@gmail.com` + `git commit --amend --reset-author --no-edit`（避免 commit 顯示 `rayda@raydas-MacBook-Pro.local`）

### 功能改動
5. **美股 P1**（commit `581f37a` v3.18.0）：us-market.html 從 teaser 換成 100 檔卡片網格 + 11 分類 tab + 搜尋
6. **fix HTML injection bug**（commit `21ea5a7` v3.18.1）：onerror inline handler 內塞含雙引號 HTML 字串 → 切斷 attribute → 卡片 layout 爆掉。修法：dual-element 切換顯示
7. **about/contact 公司聯絡資訊**（commit `dd2e316`）：「公司資訊」改「公司信箱」`leadwealthai.ai@gmail.com`（Google 帳號 2026-05-30 救回了，原 handoff memory 寫的「已被暫停」需更新）；辦公地址補「台北市樂群三路 289 號」
8. **首頁 hero 對比區塊動態化**（commit `34b4bef`）：2330 數字不再 hardcode 過期
9. **美股 P2**（commit `3f7980f` v3.19.0）：接 yfinance 即時報價、4 種排序、美股顏色、updated time 標記
10. **美股 cron 自動化**（commits `53ac432` + `6807b3b`）：`.github/workflows/us-data-update.yml`，每天 UTC 21:30 跑、首次手動觸發 52 秒 100/100 成功、Yahoo Finance 在 GitHub Actions 沒擋 ⭐

### 觀察 / 不修
- **6/1 cron failure 根因** = TPEx server 1-2 分鐘抽風（IncompleteRead + HTTP 520），不是我們 bug。建議不修，下次 cron 自動恢復
- 一般週末（六、日）cron 不跑是設計（cron `0 7 * * 1-5`），不是 bug

---

## 🚧 待辦清單（按優先序）

### 🔥 P0：金流 → 立刻變現
1. 用戶打藍新 / PayUni 電話確認個人會員是否收 AI/訂閱財經內容（進行中）
2. 通過後串接金流到 vip.html subscribe button
3. 串好後啟用 `FAIR_VALUE_GATE = true`
4. 接著做完整排行頁的 6-10 免費 / 1-5 鎖
5. **暫時方案**（金流還沒通的這 1-3 週）：vip.html subscribe 改「LINE 私訊客服開通」，先驗證需求
6. **長期**（1-3 個月）：成立公司 → 申請綠界/藍新「特約會員」

### 🟡 P1：擴張變現
7. **用戶開 IB / Firstrade Affiliate**（你幫不上，提醒用戶）
8. 拿到推薦連結 → us-market.html 的 broker CTA 啟用 + 在文章頁 / partners.html 也鋪
9. **partners.html** 寫出來（通路王 + 永豐/國泰/玉山券商比較頁）
10. **美股 P3**（進行中）：
    - **(A) AI 對話支援美股** — worker.js 加 `usStocks` context、SYSTEM_PROMPT 加美股段落
    - **(B) 警示推播** — LINE Login + 警示推播（多次提及但未做）
    - **(C) 持股健診** — 美股 + 台股一起算配置/集中度/匯率曝險

### 🟢 P2：留存
11. **再 2-3 篇 SEO 文章**（ETF 0050 vs 0056、興櫃怎麼買、P/B 河流圖）
12. **美股 P4**（更遠）：美股版合理區間演算法（歷史 P/E 分位數 + 5 個信號移植 + ETF 殖利率分位）

### ⚪ 用戶自己要做（不是 Claude 的事）
- 公司登記
- 商標申請（NT$14,000）
- 165 反詐騙申訴（曾被冒用）
- LINE 灰盾（等公司）

---

## ⚠️ 接手雷區（這些別踩）

1. **不要再寫「未上市」當主打**（用戶之前被詐騙集團冒用「未上市飆股」，網站定位已改成「上市+上櫃+興櫃全市場」，但保留「未上市可以買嗎」防詐文章是 OK 的）
2. **「2,300+」是動態的，別硬編 2,310**（之前犯過）
3. **AI 系統提示已有資料紀律規則**（不能編價格、要附資料源+時間），改 prompt 時別覆蓋這些
4. **scroll-snap 用 mandatory 會讓用戶感到「滑了被拉回」**（手機 UX 雷區），用 none 自由滑動 + `overscroll-behavior-x: contain`
5. **iOS Chrome 沒 SpeechRecognition API**（用 WKWebView），所以麥克風功能只在 Safari / PWA 可用
6. **跨機協作**：先 `git pull --rebase` 再 push（bot 每天自動 push data 更新 commit）
7. ⭐ **gh CLI 雙帳號**（這台 macOS）：active 預設可能是 getcrosslingo，沒 leadfu-ai 權限 → push 403。修法：`gh auth switch --user Rayda0114`
8. ⭐ **CRLF/LF 假改動**：OneDrive 從 Windows 同步檔案會塞 CRLF 進來、macOS git 看成「全部改動」。修法：`git config core.autocrlf input` + `git checkout -- .`
9. ⭐ **inline onerror handler 內不要塞含 HTML 引號的字串**（會切斷 attribute、之前美股卡片爆掉）— 改用 dual-element 切換顯示
10. ⭐ **美股慣例綠漲紅跌**（`#16A34A` 漲 / `#EF4444` 跌），跟台股相反，不要搞錯
11. ⭐ **`leadwealthai.ai@gmail.com` 已在 2026-05-30 救回**，可用作對外公司信箱（about.html 已填）。原 handoff memory 寫的「已被 Google 暫停」需要更新

---

## 📦 Memory 索引（這台 Claude 本機 `.claude/projects` 內，不會同步）

如果你（另一台）也是 Claude Code，建議查的 memory 索引：
- `project_berich_clone.md`（這個專案的基礎設定）
- `project_leadfu_strategy.md`（訂閱策略 + Roadmap）
- `project_leadfu_monetization_brokerage.md`（券商分潤研究）
- `user_business_context.md`（**這個檔是 Acewin 業務脈絡、不要載入 LeadFu pool，避免污染**）

---

## 🎯 接手第一句該問用戶的話（如果你不確定）

> 「我看了 LEADFU_HANDOFF.md，目前狀態是『綠界被拒、用戶在打藍新/PayUni 電話找替代金流；美股 P1+P2 已上線、cron 自動每天更新；P3 (AI 對話支援美股 / 警示推播 / 健診) 待開動』。你想做的是：(A) 等金流 + 等用戶 IB 開戶、(B) P3 繼續推進、(C) 寫 SEO 文章、(D) 別的？」

---

**最後更新者：** Claude（macOS、session 約 30+ 輪對話完成 12 commits、v3.17.3 → v3.19.0）
**最新 commit hash**：請 `git log -1` 查
**v3.19.0 對應 commit**：`3f7980f` `feat: 美股專區 P2 — 接 yfinance 即時報價 + 排序 + 100 檔快照 (v3.19.0)`
**美股 P2 cron 首次成功**：`6807b3b` `data: 美股 100 檔報價更新 (2026-06-02)`
