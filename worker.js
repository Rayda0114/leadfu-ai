/**
 * 領富 AI · Cloudflare Worker（自訂 API + 靜態資源）
 *
 * 路由：
 *   /api/ask     → AI 問答（Nvidia API）
 *   /api/health  → 健康檢查
 *   其他         → 靜態資源（ASSETS binding）
 *
 * 環境變數（在 Cloudflare Dashboard → Settings → Variables and Secrets 設）：
 *   NVIDIA_API_KEY  (Secret)              主力 AI（Nvidia NIM）
 *   NVIDIA_MODEL    (Plain Text，可選)     預設 qwen3-next-80b-a3b-instruct
 *   GEMINI_API_KEY  (Secret)              備援 AI（Google AI Studio Gemini，免費 1500 req/day）
 *
 * AI 呼叫策略：先打 Nvidia，撞 429/5xx 時自動 fallback 到 Gemini，
 * 兩家都失敗才回錯誤訊息給用戶。前端可從 response header
 * X-LeadFu-Backend 看到是 "nvidia" 還是 "gemini-fallback"。
 */

// 完整模型測試紀錄（2026-05-16 第二輪掃完 Nvidia NIM 完整名單）：
//   ⭐ qwen/qwen3-next-80b-a3b-instruct        → 9.4s, 中文最自然（台式繁中舉例），MoE 80B/3B【目前主力】
//   ⚡ nvidia/nemotron-3-nano-30b-a3b          → 3.5s, 167 t/s 速度王，中文 OK（備援極速版）
//   ⚡ openai/gpt-oss-20b                      → 4.7s, 168 t/s, 結構好
//   ✓ minimaxai/minimax-m2.7                   → 12.9s, 中文好
//   ✓ meta/llama-3.3-70b-instruct              → 13s, 穩定備援
//   ✘ mistralai/mixtral-8x7b-instruct          → 答案有錯（混淆月增/年增）
//   ✘ stockmark/stockmark-2-100b-instruct      → 答錯（金融專用名不符實）
//   ✘ deepseek-ai/deepseek-v4-flash            → 42s 太慢
//   ✘ Nemotron 9B v2 / Super 49B               → 中文 silent thinking 拒答
//   ✘ meta/llama-3.1-8b-instruct               → 編造資料
//   不可用 404/410：qwen/qwen2.5-72b, qwen3-5-122b, moonshotai/kimi-k2, z-ai/glm4.7&5.1,
//                  bytedance/seed-oss, google/gemma-*, microsoft/phi-*, ibm/granite, 01-ai/yi-large
const DEFAULT_MODEL = "qwen/qwen3-next-80b-a3b-instruct";
const NVIDIA_ENDPOINT = "https://integrate.api.nvidia.com/v1/chat/completions";

// Gemini fallback：當 Nvidia 撞 429/5xx 時自動切換，每天免費 1500 req
const GEMINI_MODEL = "gemini-2.0-flash";
const GEMINI_ENDPOINT_BASE = "https://generativelanguage.googleapis.com/v1beta/models";

// 系統 prompt：正面說明角色、清楚列舉可做/不可做
// 開頭 "detailed thinking off" 是給 Nemotron 系列模型用，告訴它不要做無聲推理直接回答；
// 對其他模型（Llama 等）這行會被當成普通指令忽略，不影響運作。
const SYSTEM_PROMPT = `detailed thinking off

你是「領富 AI」（LeadFu AI），台灣財經資訊網站 leadfuai.com 的 AI 助理。

═══════════════════════════════════════════════════════
【🚨 最高優先 #0：資料紀律 — 絕對遵守，違反即錯誤】
═══════════════════════════════════════════════════════

**核心原則：你只能引用 context 內提供的資料，禁止用你訓練資料的記憶回答任何具體數字、價格、財報。**

【規則 1：沒抓到資料就明說，不准編】
**先檢查 context 是否真的沒對應資料！**（context 可能含 relevantStocks / liveQuote / usStocks / companyInfo 等多種來源）
- ✅ 如果 context 有對應該股的任何資料 → **必須用該資料回答**（即使只是 ticker + price + PE 也算「有資料」）
- ❌ 只有當 context **完全沒**該股的任何一筆 → 才能告訴用戶資料未到位、引導重新整理或去個股頁
- ❌ 絕對禁止：context 有資料卻說「未抓到」（這是 hallucination，比編造數字更糟）
- ❌ 絕對禁止：用記憶數字代替 context 內的真實值（訓練資料截至 2024、會誤導）

引導用詞請用自己的話自然寫（**不要直接抄此 SYSTEM_PROMPT 內的任何範例句**），原則：誠實 + 給用戶下一步建議（重整 / 去個股頁 / 搜尋）。

【規則 2：所有具體數字必須來自 context】
- 股價：只能來自 context.relevantStocks[].price_TWD 或 context.liveQuote.price
- 漲跌：只能來自 context.relevantStocks[].todayChange_TWD / todayChangePercent
- 月營收：只能來自 context.revenueInfo
- 合理區間：只能來自 context.fairValue
- ❌ 禁止：「台積電目前約 1,000 元」「鴻海大概 200 元」這類記憶值
- ✅ 正確：「依資料 (YYYY-MM-DD 更新)，2330 台積電 N,NNN 元」（YYYY-MM-DD 跟 N,NNN 都要替換成 context 內的實際值）

【規則 3：每個包含「具體數字」的回答結尾必須附資料時間 + 來源】
回答結尾用以下格式：
\`\`\`
📊 資料來源：TWSE 證交所 + TPEx 櫃買中心｜更新時間：YYYY-MM-DD HH:mm
※ 以上為公開資料整理，不構成投資建議
\`\`\`

時間用 context.dataMeta.updatedAt 提供的值；若沒有就寫「資料時間：請參考頁面標示」。

【規則 4：即時報價優先】
若 context 同時有 \`relevantStocks\` 和 \`liveQuote\`：
- liveQuote 是 5 秒延遲即時報價（來自 TWSE MIS API），更新鮮
- relevantStocks 是當日盤後資料（stocks_live.json）
- 優先用 liveQuote 的價格，附註「(即時 5 秒延遲)」
- 如果兩個價格差距 >2%，提醒用戶「即時 vs 盤後價格差異較大，可能正在盤中波動」

【規則 5：被問「現在多少錢」「現在合理嗎」這類「即時感」問題時】
即使 context 有當日資料，仍要明確標示：
- 「依 YYYY-MM-DD HH:mm 資料」（盤後；YYYY-MM-DD HH:mm 換成 context.dataMeta.updatedAt 實際值）
- 或「即時 5 秒延遲報價」（如果用了 liveQuote）
讓用戶知道數字的時間維度。

═══════════════════════════════════════════════════════
【🚨 最高優先 #1：合理區間引用規則 — 絕對遵守】
═══════════════════════════════════════════════════════

當 context 含「fairValue」或「watchlistFairValue」欄位時，**必須在回應中明確引用**這份資料。這是「**領富 AI 合理區間（LeadFu Fair Value Range™）**」資料整理結果，**不是投資建議**，是我們網站算給用戶看的「客觀數據點」。

**何時必須引用**：
- 用戶問「現在貴嗎」「現在便宜嗎」「合理價」「該不該進場」「位置」「值不值得」
- 用戶問某檔股票任何狀況時，**只要 context 有 fairValue 也要主動帶到**

**回答時必須用以下結構化格式（**完全照抄這個格式**）**：

💎 **領富 AI 合理區間**

**合理區間**：NT$ {low} ~ NT$ {high}
**目前位置**：{label} （區間 {position*100:.0f}% 位置）
**訊號強度**：⭐⭐⭐⭐⭐  （依據 confidence 值：5=⭐⭐⭐⭐⭐、4=⭐⭐⭐⭐、3=⭐⭐⭐、2=⭐⭐、1=⭐）

接著用 1-2 句白話解讀目前位置代表什麼。

**範例正確回答**（confidence=5 時）：

💎 **領富 AI 合理區間**

**合理區間**：NT$1,930 ~ NT$2,655
**目前位置**：合理區間中 （區間 46% 位置）
**訊號強度**：⭐⭐⭐⭐⭐

目前股價 2,265 元落在我們計算的中性配置區間內，非偏低也非偏高。

**⚠ 絕對不要用「5 顆星」這種文字**，必須輸出**真實的 ⭐ emoji 字元**對應 confidence 數值。

**禁止**：因為「不能給投資建議」就省略合理區間資料 — 合理區間是「資料整理」，不是「建議」，必須提供給用戶。

【可說 / 不可說】
✔ 可說：「合理區間 NT$X ~ NT$Y」「目前位於合理偏低/中/高」「訊號強度 X 顆星」
✘ 不可說：「目前股價低於合理區間，建議買進」（去掉「建議」即可）

═══════════════════════════════════════════════════════

【你的工作】
- 用清楚易懂的繁體中文，幫使用者解答關於股票、市場、財報、公司的問題
- 解釋金融概念（例如：月營收年增率、本益比、興櫃市場、IPO）
- 整理使用者提供的公開資料（個股報價、公司基本資料、月營收等）
- 用淺白語言寫，目標讀者是 45-75 歲台灣投資人，避免複雜術語
- 簡短分段，必要時用條列，但不用 markdown 表格

【免責規則 — 友善版：給資料、不給建議】
你只整理公開資料，不做個股買賣建議。但要用「給用戶有用資訊」的方式呈現，不要冷冰冰拒絕。

✔ 可以說：「該股目前股價 X 元」「月營收年增 Y%」「資本額 Z 億」「成立於 19XX 年」
✔ 可以說：「今日成交量前 N 名是...」「依漲幅排序前 N 名」「目前資料顯示...」
✘ 絕對不說：「建議買進」「建議賣出」「值得買」「會漲」「目標價是」「我看好」「我推薦」「好推薦」「值得關注」

【特別處理：被問「推薦／該不該買／會不會漲／有什麼好的／值不值得」】

**先檢查條件**：如果用戶問的是「某個特定股票」（含股號或單一公司名稱），
且 context 已有該股的 fairValue，**直接用合理區間回答，不要使用三段式**。

只有當用戶問「**整個市場**有什麼推薦的」「**有沒有好的標的**」「我**該買什麼**」這類
「未指定股票的開放性推薦問題」時，才用以下三段式結構回答（用自己的話自然寫）：

第一段（告知限制）：簡短說明你不能推薦個股，但可以幫忙整理客觀數據作參考。
例如：「我不能推薦個股給您（這需要投顧執照），不過我可以幫您整理客觀數據作參考。」

第二段（給有用資料）：根據 context 提供的個股，列出 3-5 檔今日熱門/活躍股，**只描述客觀數字**（價格、漲跌、成交量、產業、市場）。不可加「值得看」「表現好」「推薦關注」等評價詞。
例如：
「以下是今日上市股票中**成交量前 5 名**（純成交數據，非推薦）：
1. 2330 台積電（半導體）股價 1,050 元，今日 +1.5%，量 25,000 張
2. 2317 鴻海（電子）股價 245 元，今日 -0.4%，量 73,000 張
..."

第三段（提醒自評）：請使用者依自身狀況判斷或諮詢合法投顧。
例如：「實際買賣決定請您依自身風險承受度與投資目標評估，或諮詢合法的證券投資顧問。」

關鍵：第二段一定要給「成交量最大」「漲幅最高」這類**純客觀分類**，不要說「以下是值得看的股票」。

回答最後請加一行：
※ 以上為公開資料整理，不構成投資建議，亦非投顧服務。

【資料來源】
使用者訊息中可能含這些 context 欄位，請優先使用：
- relevantStocks（個股報價）/ companyInfo / revenueInfo / industryStats
- fairValue（領富 AI 合理區間，含 low/high/position/label/confidence）
- watchlistStocks（使用者自選股即時報價）
- watchlistCompanies（自選股公司基本資料）
- watchlistRevenue（自選股月營收）
- watchlistNews（自選股近期相關新聞）
- watchlistAnnouncements（自選股重大公告 / 注意股）
- watchlistFairValue（自選股合理區間集合）
- watchlistIsEmpty: true（使用者還沒加任何自選股）

【💎 領富 AI 合理區間（LeadFu Fair Value Range™）使用規則】
若 context 含 fairValue 欄位（單檔）或 watchlistFairValue（自選股集合），
回答「現在貴不貴」「合理價多少」「該不該進場」這類問題時，務必引用這個資料：
- 「目前位置：{label}（區間 {position*100}% 位置）」
- 「合理區間 NT$ {low} ~ NT$ {high}」
- 「訊號強度：{confidence} 顆星」
但絕對 NOT 講「演算法用了什麼」「怎麼算出來的」— 這是領富 AI 專有演算法，
對外只露結果。被問演算法時友善回答「這是領富 AI 專有演算法，整合多項公開資料計算」。

【被問自選股時】
- 如 watchlistIsEmpty=true：友善告訴使用者「您還沒加任何自選股，先到個股頁面按『＋自選』加入幾檔，下次就能直接問我了」
- 如有自選股資料：根據使用者問題，**整合多源資料**回答。例如：
  - 「我的自選股今天怎樣」→ 列出每檔的代號名稱、價格、漲跌（元+%）、所屬市場
  - 「我自選股有什麼新聞」→ 用 watchlistNews 整理近期新聞要點（含日期）
  - 「我自選股月營收」→ 用 watchlistRevenue 整理每檔的最新月營收 + 年增率
  - 「我自選股有沒有公告」→ 用 watchlistAnnouncements 提醒注意股或處置股
  - 「自選股全部一次幫我看」→ 跨資料源綜合整理（股價 + 新聞 + 重大訊息）

═══════════════════════════════════════════════════════
【🌎 美股題型 — 美股精選 100 庫】
═══════════════════════════════════════════════════════

當 context 含 \`usStocks\` 欄位 → 用戶在問美股（領富 AI 美股精選 100 內的標的）。
資料結構：每個 entry 含 ticker / name_en / name_zh / category / industry / description（meta）
+ price / change_pct / pe_ratio / yield_pct / market_cap / w52_high / w52_low / sector / _liveUpdatedAt（live）

【美股 vs 台股關鍵差異】
- 價格單位 **USD**（不是 NT$），寫成「$306.31」「$2,768」（萬位以上加千分位）
- 美股慣例「綠漲紅跌」（跟台股相反，但文字只要正負號就 OK）
- 資料來源：**Yahoo Finance via yfinance**（不是 TWSE/TPEx）
- 資料時間：用 \`_liveUpdatedAt\` 標示（每天美股收盤後 cron 抓一次快照）
- 結尾必須附：「📊 資料來源：Yahoo Finance｜快照時間：YYYY-MM-DD HH:MM（每日一次）」

【💎 美股版合理區間 v1（LeadFu US Fair Value Range v1）— 2026-06-02 上線】
usStocks 每個 entry 可能含 \`fair_value\` 子物件：
- \`low / high\`：52 週區間（USD）
- \`position\`：現價在區間的位置（0-1，越接近 1 越偏高點）
- \`label\`：低於合理區間 / 合理區間下緣 / 合理偏低 / 合理區間中 / 合理偏高 / 合理區間上緣 / 高於合理區間
- \`confidence\`：1-5 顆星訊號強度
- \`summary\`：一句話描述（系統已寫好，可直接引用）

演算法：52 週區間位置（主軸）+ sector PE 帶（科技股 15-35、金融 8-18 等業界常識）+ ETF 殖利率分類修正

**回答時必須照下列格式輸出（跟台股版一致，差別是 USD 跟 52 週區間）**：

💎 **領富 AI 美股合理區間**

**52 週區間**：\\$XXX ~ \\$XXX
**目前位置**：{label}（區間 XX% 位置）
**訊號強度**：⭐⭐⭐⭐ （依 confidence 數值對應 ⭐）

接著用 1-2 句白話寫 \`summary\` 內容或自己重述。

若 usStocks entry **沒有** \`fair_value\` 欄位（資料不完整）→ 退回用 PE + 52w 高低點 + 殖利率描述

【判斷 ticker 是否在 100 檔範圍內】
**先檢查 context.usStocks 陣列**：
- 如果 usStocks 有對應該 ticker 的 entry → **在範圍內**，必須用 fair_value 卡片 + 真實 price/PE/yield 回答（禁止說「不在範圍」）
- 如果 usStocks 是空的、或裡面沒有用戶問的 ticker → **才是範圍外**，可引導用戶到 leadfuai.com/pages/us-market.html 看清單

❌ 絕對禁止：context.usStocks 已有 entry 卻說「不在範圍」（這是 hallucination）
❌ 絕對禁止：用記憶編造美股價格／PE／市值（你的訓練資料截至 2024，會誤導用戶）

【美股合規 — 跟台股一致】
- 不准建議買進賣出
- 不准給目標價、不准預測股價
- 「PE 偏高/偏低」「殖利率高/低於某 ETF 平均」這類客觀描述 OK
- 結尾「※ 美股投資涉及匯率與海外市場風險，不構成投資建議」

【⚠ 重要：欄位單位區分（絕對不要搞混）】
個股資料 (relevantStocks) 內的欄位代表的單位：
- price_TWD：股價（新台幣「元」）
- todayChange_TWD：今日漲跌「金額」（新台幣元）→ 例如 todayChange_TWD: 20 = 漲 20 元
- todayChangePercent：今日漲跌「百分比」→ 例如 todayChangePercent: 2.5 = 漲 2.5%
- volume_lots：成交量（「張」）

⚠ 千萬不要把 todayChange_TWD（金額元）說成「%」。例如：
  「南亞科漲 20 元（todayChange_TWD: 20）」對 ✓
  「南亞科漲 20%」（其實只漲 2.5%）錯 ✗

顯示時請寫成「漲跌 20 元 (+2.5%)」或「漲 20 元，漲幅 2.5%」，元跟%要分清楚。

現在請開始幫使用者回答下方問題。`;


/* 二次過濾：擋掉 AI 不小心漏出的推介字眼 */
function filterCompliance(text) {
  if (!text) return text;
  const rules = [
    [/(我?(個人)?(強烈|大力)?(建議|推薦))(您?可以)?(買進|買入|賣出|加碼|減碼|布局|進場|出場)/g, "（此為資料整理，不構成買賣建議）"],
    [/(建議|推薦)(您?買進|您?買入|您?賣出)/g, "（此為資料整理，不構成買賣建議）"],
    [/可以買進|可以買入|可以賣出/g, "可參考數據"],
    [/(強力|積極)?買進評等|加碼評等|減碼評等/g, "資料整理"],
    [/目標價(?:上看|看至|為|是)?\s*\$?[\d,]+\.?\d*\s*元?/g, "（不提供目標價）"],
    [/我看好|我不看好|本站看好/g, "目前數據顯示"],
    [/(短期|中期|長期)?上看[\d,]+元/g, "（不預測股價）"]
  ];
  let out = text;
  for (const [pattern, replacement] of rules) out = out.replace(pattern, replacement);

  // 自動掛免責（若 AI 漏掉就補）
  if (!/不構成投資建議/.test(out)) {
    out += "\n\n※ 以上為公開資料整理，不構成投資建議，亦非證券投資顧問服務。";
  }
  return out;
}


/* 美股快照時間修正（P3-A）：
 * Qwen / Gemini 等 LLM 看到 2026 日期會「修正」回訓練資料截止年（如 2024-06），
 * 不管 prompt 多強調都會搞錯快照時間。後處理直接 regex 找「快照時間：YYYY-MM-DD ...」
 * 強制替換成 context.usStocks 內的真實 _liveUpdatedAt。
 */
function fixUsSnapshotDate(text, usStocks) {
  if (!text || !usStocks || !usStocks.length) return text;
  const liveAt = usStocks[0]?._liveUpdatedAt;
  if (!liveAt) return text;
  return text.replace(
    /(快照時間[：:]\s*)\d{4}[-/]\d{1,2}[-/]\d{1,2}(?:[\s,]+\d{1,2}[:：]\d{2}(?::\d{2})?)?/g,
    `$1${liveAt}`
  );
}

/* 美股合理區間數字修正（P4 v1）：
 * Qwen 會把 2026 真實價格「修正」回 2024/2025 訓練資料記憶值（AAPL $306→$198 等）
 * 後處理用 regex 強制替換 AI 輸出內的：
 *   - 「52 週區間：$X ~ $Y」→ 真實 fair_value.low/high
 *   - 「目前位置：{label}（區間 X% 位置）」→ 真實 fair_value.label / position
 * 注意：只替換用戶詢問的第一檔（usStocks[0]），多檔對應暫不處理（v2 再做）
 */
function fixUsFairValue(text, usStocks) {
  if (!text || !usStocks || !usStocks.length) return text;
  const fv = usStocks[0]?.fair_value;
  if (!fv) return text;

  // 1. 52 週區間：$X ~ $Y — 用 callback 避免 $1$XX 被誤判
  if (fv.low != null && fv.high != null) {
    text = text.replace(
      /(\*{0,2}52\s*週區間\*{0,2}[：:]\s*)\$[\d,.]+\s*~\s*\$[\d,.]+/g,
      (_m, g1) => `${g1}$${fv.low} ~ $${fv.high}`
    );
  }

  // 2. 目前位置：{label}（區間 X% 位置）
  if (fv.label && fv.position != null) {
    const pct = Math.round(fv.position * 100);
    text = text.replace(
      /(\*{0,2}目前位置\*{0,2}[：:]\s*)[^\n（(]*?\s*[（(]\s*區間\s*\d+\s*%\s*位置\s*[)）]/g,
      (_m, g1) => `${g1}${fv.label}（區間 ${pct}% 位置）`
    );
  }

  // 3. 訊號強度：⭐ × N（依 confidence）
  if (fv.confidence != null) {
    const stars = "⭐".repeat(Math.max(1, Math.min(5, Math.round(fv.confidence))));
    text = text.replace(
      /(\*{0,2}訊號強度\*{0,2}[：:]\s*)⭐+\s*/g,
      (_m, g1) => `${g1}${stars} `
    );
  }

  return text;
}


/* CORS / preflight */
function corsHeaders() {
  return {
    "Access-Control-Allow-Origin": "https://leadfuai.com",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "86400"
  };
}


/* ============================================================
 * Gemini fallback helpers
 * 當 Nvidia 撞 rate limit 或 5xx 時自動切換，保證網站不斷線。
 * Gemini 2.0 Flash 免費 1,500 req/day，中文品質很好。
 * ============================================================ */

/** 把 OpenAI 格式的 messages 轉成 Gemini 格式 */
function toGeminiContents(messages) {
  // OpenAI: [{role:"system",...}, {role:"user",...}, {role:"assistant",...}]
  // Gemini: contents=[{role:"user",parts:[{text}]}, {role:"model",parts:[{text}]}]
  //         systemInstruction={parts:[{text}]}
  let systemText = "";
  const contents = [];
  for (const m of messages) {
    if (!m || !m.content) continue;
    if (m.role === "system") {
      systemText += (systemText ? "\n\n" : "") + m.content;
    } else if (m.role === "user") {
      contents.push({ role: "user", parts: [{ text: String(m.content) }] });
    } else if (m.role === "assistant") {
      contents.push({ role: "model", parts: [{ text: String(m.content) }] });
    }
  }
  // Gemini 第一條必須是 user
  if (!contents.length || contents[0].role !== "user") {
    contents.unshift({ role: "user", parts: [{ text: "請開始" }] });
  }
  return { contents, systemText };
}

/** 呼叫 Gemini（非串流） */
async function callGemini(env, finalMessages, maxTokens) {
  if (!env.GEMINI_API_KEY) {
    return { ok: false, status: 0, error: "GEMINI_API_KEY not configured" };
  }
  const { contents, systemText } = toGeminiContents(finalMessages);
  const body = {
    contents,
    generationConfig: {
      temperature: 0.4,
      topP: 0.9,
      maxOutputTokens: maxTokens
    }
  };
  if (systemText) {
    body.systemInstruction = { parts: [{ text: systemText }] };
  }
  const url = `${GEMINI_ENDPOINT_BASE}/${GEMINI_MODEL}:generateContent?key=${env.GEMINI_API_KEY}`;
  try {
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
    if (!resp.ok) {
      const errText = await resp.text().catch(() => "");
      return { ok: false, status: resp.status, error: errText.slice(0, 300) };
    }
    const data = await resp.json();
    const answer = data?.candidates?.[0]?.content?.parts?.[0]?.text || "";
    const usage = data?.usageMetadata ? {
      prompt_tokens: data.usageMetadata.promptTokenCount,
      completion_tokens: data.usageMetadata.candidatesTokenCount,
      total_tokens: data.usageMetadata.totalTokenCount
    } : null;
    return { ok: true, answer, usage, model: GEMINI_MODEL };
  } catch (err) {
    return { ok: false, status: 0, error: String(err) };
  }
}

/** 把 Gemini 非串流回應包成 OpenAI-style SSE 一次性吐出（給 stream 模式 fallback） */
function geminiToSSE(answer, model) {
  const enc = new TextEncoder();
  const stream = new ReadableStream({
    start(controller) {
      // 模擬 OpenAI streaming chunks：先 chunk 整段 content，再送 [DONE]
      const chunk = {
        choices: [{
          delta: { content: answer },
          index: 0,
          finish_reason: null
        }],
        model
      };
      controller.enqueue(enc.encode(`data: ${JSON.stringify(chunk)}\n\n`));
      const done = {
        choices: [{ delta: {}, index: 0, finish_reason: "stop" }],
        model
      };
      controller.enqueue(enc.encode(`data: ${JSON.stringify(done)}\n\n`));
      controller.enqueue(enc.encode(`data: [DONE]\n\n`));
      controller.close();
    }
  });
  return stream;
}


/* ============================================================
 * 美股資料抓取（P3-A）：用 env.ASSETS.fetch 從 same-origin static
 * assets 拿 us_stocks_meta + us_stocks_live，找到對應 ticker 後
 * 合併欄位回傳。完全後端、客戶端零侵入。
 * ============================================================ */

// 排除常見英文單字（避免「I / IS / NO / OK」等被誤判 ticker）
const US_TICKER_BLOCKLIST = new Set([
  "I","A","AM","AN","AS","AT","BE","BY","DO","GO","IF","IN","IS","IT","NO",
  "OF","ON","OR","OK","SO","TO","UP","US","WE","MY","ME","HE","UK",
  "AND","ARE","BUT","CAN","FOR","GET","HAS","HAD","HER","HIM","HIS","HOW",
  "ITS","NOT","NOW","OUR","OUT","SHE","THE","WAS","WHO","WHY","YES","YOU",
  "WAY","WHO","DID","TWO","ONE","ALL","ANY","NEW","OLD","SEE","SAY","USE",
  "AI","API","CEO","CFO","CTO","COO","IPO","PE","ETF","NYC","USA","USD",
  "URL","FAQ","SOP","SDK","SQL","XML","JSON","HTTP","HTTPS"
]);

// 提取訊息內可能的美股 ticker（1-5 個大寫字母 + 可選 -X 後綴如 BRK-B）
function extractUsTickerCandidates(text) {
  if (!text) return [];
  const matches = text.match(/\b[A-Z]{1,5}(?:-[A-Z])?\b/g) || [];
  return [...new Set(matches.filter(t => !US_TICKER_BLOCKLIST.has(t)))];
}

// 從 ASSETS binding 抓美股 meta + live + (可選) fair_value，合併並過濾 candidates
// 採 split try/catch：fair_value fetch 失敗不影響 meta+live 主流程
async function getUsStockData(env, candidates) {
  if (!env.ASSETS || !candidates || !candidates.length) return null;
  try {
    // 必要：meta + live
    const [metaRes, liveRes] = await Promise.all([
      env.ASSETS.fetch(new Request("https://placeholder/data/us_stocks_meta.json")),
      env.ASSETS.fetch(new Request("https://placeholder/data/us_stocks_live.json"))
    ]);
    if (!metaRes.ok) return null;
    const meta = await metaRes.json();
    const metaData = meta?.data || {};
    let liveData = {};
    let liveUpdatedAt = null;
    if (liveRes && liveRes.ok) {
      const live = await liveRes.json();
      liveData = live?.data || {};
      liveUpdatedAt = live?.updatedAt || null;
    }
    // 可選：fair_value（fail 不影響整體）
    let fvData = {};
    try {
      const fvRes = await env.ASSETS.fetch(new Request("https://placeholder/data/us_fair_value_live.json"));
      if (fvRes && fvRes.ok) {
        const fv = await fvRes.json();
        fvData = fv?.data || {};
      }
    } catch (_fvErr) { /* 沒 fair_value 也能正常運作 */ }

    const result = [];
    for (const ticker of candidates) {
      if (!metaData[ticker]) continue;   // 不在 100 檔精選庫就 skip
      const fairValue = fvData[ticker];
      result.push({
        ...metaData[ticker],
        ...(liveData[ticker] || {}),
        _liveUpdatedAt: liveUpdatedAt,
        ...(fairValue ? {
          fair_value: {
            low: fairValue.low,
            high: fairValue.high,
            position: fairValue.position,
            label: fairValue.label,
            confidence: fairValue.confidence,
            summary: fairValue.summary
          }
        } : {})
      });
    }
    return result.length ? result : null;
  } catch (e) {
    return null;
  }
}


/* /api/ask 處理 */
async function handleAsk(request, env) {
  if (request.method === "OPTIONS") {
    return new Response(null, { status: 204, headers: corsHeaders() });
  }
  if (request.method !== "POST") {
    return new Response(JSON.stringify({ error: "Method not allowed" }), {
      status: 405,
      headers: { "Content-Type": "application/json", ...corsHeaders() }
    });
  }
  if (!env.NVIDIA_API_KEY) {
    return new Response(JSON.stringify({ error: "AI service not configured (missing NVIDIA_API_KEY)" }), {
      status: 503,
      headers: { "Content-Type": "application/json", ...corsHeaders() }
    });
  }

  let body;
  try {
    body = await request.json();
  } catch (e) {
    return new Response(JSON.stringify({ error: "Invalid JSON body" }), {
      status: 400,
      headers: { "Content-Type": "application/json", ...corsHeaders() }
    });
  }

  // 支援兩種模式：
  //   1. 單輪：{ question, context } - 舊版相容
  //   2. 多輪聊天：{ messages: [{role, content}, ...], context, stream?: true }
  const question = (body.question || "").toString().slice(0, 1500);
  const context = body.context || {};
  const incomingMessages = Array.isArray(body.messages) ? body.messages : null;
  const wantStream = body.stream === true;

  if (!question.trim() && (!incomingMessages || incomingMessages.length === 0)) {
    return new Response(JSON.stringify({ error: "No question provided" }), {
      status: 400,
      headers: { "Content-Type": "application/json", ...corsHeaders() }
    });
  }

  // 構建最後一條 user message（含 context 注入）
  // 多輪模式：把 context 接到最後一條 user message 上
  let lastUserContent = question;
  if (incomingMessages && incomingMessages.length) {
    const lastUser = [...incomingMessages].reverse().find(m => m.role === "user");
    if (lastUser) lastUserContent = lastUser.content;
  }

  const hasContext =
    (context.relevantStocks && context.relevantStocks.length) ||
    context.companyInfo || context.revenueInfo || context.industryStats ||
    context.liveQuote || context.dataMeta ||
    (context.usStocks && context.usStocks.length);

  let augmentedLast = lastUserContent;

  // 🚨 資料紀律：偵測用戶問了股票（4 位代號）但 context 沒抓到資料
  // → 注入「資料未到位」訊息，阻止 AI 用記憶編造價格
  // ⚠ 市場摘要 / 盤後整理（isMarketBrief）跳過此檢查 —
  //   避免「下跌 1143 家」這類數字被誤判為股票代號 1143
  const stockIntent = /合理|貴|便宜|股價|現在|怎樣|怎麼樣|分析|該不該|位置|值不值|本益比|殖利率|市值|目標價|這檔|這支|買|賣/;
  const askedStockCode = (lastUserContent || "").match(/\b(\d{4})\b/);
  if (askedStockCode && !context.isMarketBrief && stockIntent.test(lastUserContent || "")) {
    const code = askedStockCode[1];
    const hasStockInContext =
      (context.relevantStocks || []).some(s => s.code === code) ||
      (context.liveQuote && context.liveQuote.code === code) ||
      (context.companyInfo && context.companyInfo.code === code);
    if (!hasStockInContext) {
      augmentedLast += `\n\n---\n⚠ 系統提示：用戶詢問代號 ${code}，但目前 context 中沒有該股的即時資料。\n**請依資料紀律規則 1 回答**：誠實告訴用戶資料未到位，引導去個股頁查看或重新整理，**絕對禁止**用訓練資料的記憶編造價格／本益比／市值等具體數字。`;
    }
  }

  // 🌎 美股偵測（P3-A）：抓 1-5 大寫字母（含 BRK-B 那種 -X 後綴）
  //   排除常見英文後若仍有 candidate → 用 env.ASSETS 從 us_stocks_meta/live 抓對應資料
  //   注入 context.usStocks 給後續 augmentedLast 階段用
  if (!context.usStocks || !context.usStocks.length) {
    const usTickerCandidates = extractUsTickerCandidates(lastUserContent || "");
    if (usTickerCandidates.length && !context.isMarketBrief) {
      const usData = await getUsStockData(env, usTickerCandidates);
      if (usData && usData.length) {
        context.usStocks = usData;
      }
    }
  }

  const hasWatchlistContext = context.watchlistStocks
    || context.watchlistNews
    || context.watchlistAnnouncements
    || context.watchlistCompanies
    || context.watchlistRevenue
    || (context.watchlistIsEmpty === true);

  if (hasContext || hasWatchlistContext) {
    augmentedLast += `\n\n---\n以下是領富 AI 網站提供給你的相關公開資料，請優先依此回答：`;
    // 📊 資料時間／來源 — AI 必須在回答結尾引用
    if (context.dataMeta) {
      augmentedLast += `\n\n### 📊 資料元資訊（回答結尾必須引用）\n\`\`\`json\n${JSON.stringify(context.dataMeta)}\n\`\`\`\n回答最後必須加：「📊 資料來源：${context.dataMeta.source || "TWSE+TPEx+MOPS"}｜更新時間：${context.dataMeta.updatedAt || "請參考頁面"}」`;
    }
    // ⚡ 即時報價優先（如有）
    if (context.liveQuote) {
      augmentedLast += `\n\n### ⚡ 即時報價（5 秒延遲，優先採用）\n\`\`\`json\n${JSON.stringify(context.liveQuote)}\n\`\`\`\n⚠ 此為 TWSE MIS API 即時報價，比 relevantStocks 的盤後資料新；回答時優先引用此價格並標註「(即時 5 秒延遲)」。`;
    }
    // 💎 合理區間資料優先放最前面（system prompt 強制要求引用）
    if (context.fairValue) {
      augmentedLast += `\n\n### 💎 領富 AI 合理區間（必須在回答中引用！）\n\`\`\`json\n${JSON.stringify(context.fairValue)}\n\`\`\`\n⚠ 上述「合理區間」資料**必須引用到回答中**，包含：低-高範圍、目前位置標籤、訊號強度。`;
    }
    if (context.fairValueMap) {
      augmentedLast += `\n\n### 💎 多檔合理區間集合（必須引用）\n\`\`\`json\n${JSON.stringify(context.fairValueMap).slice(0, 4000)}\n\`\`\``;
    }
    if (context.watchlistFairValue) {
      augmentedLast += `\n\n### 💎 自選股合理區間（必須引用）\n\`\`\`json\n${JSON.stringify(context.watchlistFairValue).slice(0, 4000)}\n\`\`\``;
    }
    if (context.relevantStocks && context.relevantStocks.length) {
      augmentedLast += `\n\n### 相關個股\n\`\`\`json\n${JSON.stringify(context.relevantStocks).slice(0, 8000)}\n\`\`\``;
    }
    if (context.companyInfo) {
      augmentedLast += `\n\n### 公司基本資料\n\`\`\`json\n${JSON.stringify(context.companyInfo).slice(0, 3000)}\n\`\`\``;
    }
    if (context.revenueInfo) {
      augmentedLast += `\n\n### 月營收\n\`\`\`json\n${JSON.stringify(context.revenueInfo).slice(0, 2000)}\n\`\`\``;
    }
    if (context.industryStats) {
      augmentedLast += `\n\n### 產業統計\n\`\`\`json\n${JSON.stringify(context.industryStats).slice(0, 2000)}\n\`\`\``;
    }

    // === 自選股 5 層資料 ===
    if (context.watchlistIsEmpty) {
      augmentedLast += `\n\n### 使用者自選股\n（目前是空的，請建議使用者先去個股頁面按「＋自選」加入幾檔）`;
    }
    if (context.watchlistStocks && context.watchlistStocks.length) {
      augmentedLast += `\n\n### 使用者的自選股 即時報價\n\`\`\`json\n${JSON.stringify(context.watchlistStocks).slice(0, 8000)}\n\`\`\``;
    }
    if (context.watchlistCompanies) {
      augmentedLast += `\n\n### 使用者自選股 公司基本資料\n\`\`\`json\n${JSON.stringify(context.watchlistCompanies).slice(0, 6000)}\n\`\`\``;
    }
    if (context.watchlistRevenue) {
      augmentedLast += `\n\n### 使用者自選股 月營收\n\`\`\`json\n${JSON.stringify(context.watchlistRevenue).slice(0, 5000)}\n\`\`\``;
    }
    if (context.watchlistNews && context.watchlistNews.length) {
      augmentedLast += `\n\n### 使用者自選股 相關新聞（近期）\n\`\`\`json\n${JSON.stringify(context.watchlistNews).slice(0, 5000)}\n\`\`\``;
    }
    if (context.watchlistAnnouncements && context.watchlistAnnouncements.length) {
      augmentedLast += `\n\n### 使用者自選股 重大公告 / 注意股\n\`\`\`json\n${JSON.stringify(context.watchlistAnnouncements).slice(0, 5000)}\n\`\`\``;
    }
    // 🌎 美股精選 100（P3-A + P4 v1）— 用戶在問美股 ticker
    if (context.usStocks && context.usStocks.length) {
      const liveAt = context.usStocks[0]?._liveUpdatedAt || "請參考 us_stocks_live.json";
      augmentedLast += `\n\n### 🌎 美股精選 100 — 用戶詢問的標的（資料來源：Yahoo Finance + LeadFu US Fair Value v1）\n\`\`\`json\n${JSON.stringify(context.usStocks).slice(0, 4500)}\n\`\`\`\n⚠ 美股回答規則：\n- usStocks 已有對應 ticker，**這就是「在 100 檔範圍內」的證據** — 必須用上述資料回答、禁止說「不在範圍」\n- 價格單位 **USD**（\\$xxx.xx，禁止 NT$）\n- 每個 entry 的 \`fair_value\` 子物件：\`low/high\` 直接用、\`position\` ×100 寫成 %、\`label\` 直接抄；**禁止用記憶值替換 \`low/high\`**\n- 結尾必須照抄：「📊 資料來源：Yahoo Finance｜快照時間：${liveAt}（每日一次）」\n- 結尾加：「※ 美股投資涉及匯率與海外市場風險，不構成投資建議」`;
    }
  }

  // 組裝最終 messages 陣列
  const finalMessages = [{ role: "system", content: SYSTEM_PROMPT }];
  if (incomingMessages && incomingMessages.length) {
    // 多輪模式：保留歷史（除最後一條），最後一條用 augmented 版本
    // 限制歷史到最近 10 條訊息控制 token 用量
    const trimmedHistory = incomingMessages.slice(-10);
    // 取出除最後一條外的所有訊息
    for (let i = 0; i < trimmedHistory.length - 1; i++) {
      const m = trimmedHistory[i];
      if (m && (m.role === "user" || m.role === "assistant") && m.content) {
        finalMessages.push({ role: m.role, content: String(m.content).slice(0, 4000) });
      }
    }
    finalMessages.push({ role: "user", content: augmentedLast });
  } else {
    // 單輪模式（舊版相容）
    finalMessages.push({ role: "user", content: augmentedLast });
  }

  // 允許 body.model 覆寫（給開發測試用，前端不會送這個參數）
  const model = (typeof body.model === "string" && body.model.length < 200)
    ? body.model
    : (env.NVIDIA_MODEL || DEFAULT_MODEL);

  // body.max_tokens 覆寫（給後端腳本用，例如產業週報需要 4000 tokens；
  // 前端聊天保持預設 800 避免單次回覆過長）
  const maxTokens = (typeof body.max_tokens === "number"
                    && body.max_tokens > 0
                    && body.max_tokens <= 4096)
    ? body.max_tokens
    : 800;

  const requestBody = JSON.stringify({
    model,
    messages: finalMessages,
    temperature: 0.4,
    top_p: 0.9,
    max_tokens: maxTokens,
    stream: wantStream
  });

  const callNvidia = async () => fetch(NVIDIA_ENDPOINT, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${env.NVIDIA_API_KEY}`,
      "Content-Type": "application/json",
      "Accept": wantStream ? "text/event-stream" : "application/json"
    },
    body: requestBody
  });

  // 嘗試 Nvidia（含 429 / 5xx 一次重試），失敗則 fallback 到 Gemini
  let aiResp = null;
  let nvidiaError = null;
  try {
    aiResp = await callNvidia();
    if (aiResp.status === 429) {
      await new Promise(r => setTimeout(r, 1500));
      aiResp = await callNvidia();
    }
    if (aiResp.status >= 500 && aiResp.status < 600) {
      await new Promise(r => setTimeout(r, 1200));
      aiResp = await callNvidia();
    }
  } catch (err) {
    nvidiaError = err.message;
  }

  const nvidiaFailed = !aiResp || !aiResp.ok;
  if (nvidiaFailed) {
    // === Fallback：切到 Gemini ===
    console.log(`[Worker] Nvidia 失敗 (${aiResp?.status || nvidiaError})，切換 Gemini fallback`);
    const gem = await callGemini(env, finalMessages, maxTokens);
    if (gem.ok) {
      let answer = filterCompliance(gem.answer);
      answer = fixUsSnapshotDate(answer, context.usStocks);
      answer = fixUsFairValue(answer, context.usStocks);
      // Stream 模式：包成 SSE
      if (wantStream) {
        return new Response(geminiToSSE(answer, gem.model), {
          status: 200,
          headers: {
            "Content-Type": "text/event-stream; charset=utf-8",
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "X-LeadFu-Backend": "gemini-fallback",
            ...corsHeaders()
          }
        });
      }
      // 非串流：直接 JSON
      return new Response(JSON.stringify({
        answer,
        model: gem.model,
        usage: gem.usage,
        backend: "gemini-fallback"
      }), {
        headers: {
          "Content-Type": "application/json; charset=utf-8",
          "X-LeadFu-Backend": "gemini-fallback",
          ...corsHeaders()
        }
      });
    }
    // 兩家都失敗 → 回友善錯誤
    const status = aiResp?.status || 502;
    const friendlyMap = {
      429: "AI 服務目前太忙，請稍等 5 秒再試（免費額度速率限制）",
      401: "AI 服務驗證失敗，請聯絡客服",
      402: "AI 服務免費額度已用完，請聯絡客服",
      403: "AI 服務存取被拒",
      500: "AI 服務暫時故障，請稍後再試",
      502: "AI 服務閘道錯誤，請稍後再試",
      503: "AI 服務暫不可用，請稍後再試",
      504: "AI 服務回應逾時，請稍後再試"
    };
    const errMsg = friendlyMap[status] || `AI 服務異常 (代碼 ${status})`;
    return new Response(JSON.stringify({
      error: errMsg,
      status,
      detail: `Nvidia: ${nvidiaError || status} | Gemini: ${gem.error || "未配置"}`
    }), {
      status: 502,
      headers: { "Content-Type": "application/json", ...corsHeaders() }
    });
  }

  // === Nvidia 成功，照原流程 ===

  // Streaming 模式：直接把 Nvidia SSE 串流轉發給前端
  if (wantStream) {
    return new Response(aiResp.body, {
      status: 200,
      headers: {
        "Content-Type": "text/event-stream; charset=utf-8",
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
        "X-LeadFu-Backend": "nvidia",
        ...corsHeaders()
      }
    });
  }

  let data;
  try {
    data = await aiResp.json();
  } catch (e) {
    return new Response(JSON.stringify({ error: "Invalid AI response" }), {
      status: 502,
      headers: { "Content-Type": "application/json", ...corsHeaders() }
    });
  }

  let answer = data?.choices?.[0]?.message?.content || "";
  answer = filterCompliance(answer);
  answer = fixUsSnapshotDate(answer, context.usStocks);
  answer = fixUsFairValue(answer, context.usStocks);

  return new Response(JSON.stringify({
    answer,
    model,
    usage: data?.usage || null,
    backend: "nvidia"
  }), {
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "X-LeadFu-Backend": "nvidia",
      "X-LeadFu-Us-Count": String(context.usStocks?.length || 0),
      "X-LeadFu-Us-Tickers": (context.usStocks || []).map(s => s.ticker).join(",") || "none",
      "X-LeadFu-Us-HasFv": String(!!(context.usStocks?.[0]?.fair_value)),
      ...corsHeaders()
    }
  });
}


/* /api/health */
function handleHealth(env) {
  return new Response(JSON.stringify({
    ok: true,
    primary: {
      provider: "nvidia",
      hasKey: !!env.NVIDIA_API_KEY,
      model: env.NVIDIA_MODEL || DEFAULT_MODEL
    },
    fallback: {
      provider: "gemini",
      hasKey: !!env.GEMINI_API_KEY,
      model: GEMINI_MODEL
    },
    time: new Date().toISOString()
  }), { headers: { "Content-Type": "application/json", ...corsHeaders() } });
}


/* /api/quote — TWSE MIS 即時報價代理（5 秒延遲）
 *
 * 用法：/api/quote?ex_ch=tse_2330.tw|tse_t00.tw|otc_o00.tw
 *   - 上市股 / t00 加權指數：tse_<code>.tw
 *   - 上櫃股 / o00 櫃買指數：otc_<code>.tw
 *   - 最多 50 檔一次查（避免被擋）
 *
 * 為什麼要走 Worker：
 *   - mis.twse.com.tw 沒開 CORS，前端不能直接 fetch
 *   - Worker 代理 + 邊緣快取 5 秒 = 同樣 5 秒間隔 polling 不會打爆來源
 */
async function handleQuote(request) {
  const url = new URL(request.url);
  const ex_ch = (url.searchParams.get("ex_ch") || "").trim();
  if (!ex_ch) {
    return new Response(JSON.stringify({ error: "missing ex_ch param" }), {
      status: 400,
      headers: { "Content-Type": "application/json", ...corsHeaders() }
    });
  }
  // 簡單清洗：只允許 [a-z0-9._|] 避免被當作 SSRF 跳板
  if (!/^[a-z0-9._|]+$/i.test(ex_ch)) {
    return new Response(JSON.stringify({ error: "invalid ex_ch chars" }), {
      status: 400,
      headers: { "Content-Type": "application/json", ...corsHeaders() }
    });
  }
  // 限制最多 50 個（保護 upstream）
  const segs = ex_ch.split("|").filter(Boolean);
  if (segs.length > 50) {
    return new Response(JSON.stringify({ error: "max 50 codes" }), {
      status: 400,
      headers: { "Content-Type": "application/json", ...corsHeaders() }
    });
  }

  const target = `https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=${encodeURIComponent(ex_ch)}&json=1&delay=0&_=${Math.floor(Date.now() / 5000)}`;
  try {
    const resp = await fetch(target, {
      headers: {
        "User-Agent": "Mozilla/5.0 LeadFuAI/1.0",
        "Accept": "application/json",
        "Referer": "https://mis.twse.com.tw/stock/fibest.jsp"
      },
      cf: { cacheTtl: 5, cacheEverything: true }
    });
    const body = await resp.text();
    return new Response(body, {
      status: resp.status,
      headers: {
        "Content-Type": "application/json; charset=utf-8",
        "Cache-Control": "public, max-age=5",
        ...corsHeaders()
      }
    });
  } catch (e) {
    return new Response(JSON.stringify({ error: "upstream failed", detail: String(e) }), {
      status: 502,
      headers: { "Content-Type": "application/json", ...corsHeaders() }
    });
  }
}


/* ============================================================
 * LINE 一鍵登入（方法 ①：Worker 端跑 LINE OAuth，繞過 Supabase OIDC）
 *
 * 為什麼不走 Supabase Custom OIDC：
 *   LINE 的 id_token 用 HS256（對稱、channel secret 當 HMAC 金鑰）簽，
 *   但 LINE discovery 卻宣告 ES256 → Supabase 通用 OIDC 驗證器只收
 *   ES256/RS256（JWKS），永遠驗不過：
 *     "failed to verify ID token: oidc: id token signed with
 *      unsupported algorithm, expected [ES256] got HS256"
 *   → 這就是為什麼領富每次 LINE 登入都在 Supabase 端失敗。
 *
 * 解法（最穩、完全避開 JWT 簽章）：
 *   1. code → access_token（LINE token endpoint）
 *   2. GET https://api.line.me/v2/profile（Bearer）→ { userId, displayName, pictureUrl }
 *   3. Supabase admin API：用 line userId 派生固定 email、建/找該用戶，
 *      把 line_user_id 寫進 profiles
 *   4. admin generate_link（magiclink）→ 回 token_hash 給前端
 *      前端 verifyOtp(token_hash) 建立正式 session
 *
 * 安全性：
 *   - 只有完成本 channel LINE 授權、拿到有效 code 的人，才換得到自己
 *     userId 的 session（code 無法偽造、單次有效）。
 *   - service_role / channel secret 只在 Worker 端（env secret），絕不回前端。
 *   - 只回單次有效、短時效的 token_hash。CORS 限 leadfuai.com。
 * ============================================================ */
const LINE_LOGIN_CHANNEL_ID = "2010279883";
const LINE_LOGIN_REDIRECT_URI = "https://leadfuai.com/pages/line-callback.html";
const SUPABASE_PROJECT_URL = "https://lhwxpnyzplylajxunlua.supabase.co";

function lineAuthError(msg, status) {
  return new Response(JSON.stringify({ error: msg }), {
    status: status || 400,
    headers: { "Content-Type": "application/json", ...corsHeaders() }
  });
}

async function handleLineAuth(request, env) {
  if (request.method === "OPTIONS") {
    return new Response(null, { status: 204, headers: corsHeaders() });
  }
  if (request.method !== "POST") return lineAuthError("method not allowed", 405);

  if (!env.LINE_LOGIN_CHANNEL_SECRET || !env.SUPABASE_SERVICE_ROLE_KEY) {
    return lineAuthError("server not configured (missing LINE secret or service role key)", 500);
  }

  let body;
  try { body = await request.json(); }
  catch { return lineAuthError("invalid json body"); }
  const code = (body && body.code || "").trim();
  if (!code) return lineAuthError("missing code");

  // 1) code → access_token
  let accessToken;
  try {
    const tokenRes = await fetch("https://api.line.me/oauth2/v2.1/token", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        grant_type: "authorization_code",
        code,
        redirect_uri: LINE_LOGIN_REDIRECT_URI,
        client_id: LINE_LOGIN_CHANNEL_ID,
        client_secret: env.LINE_LOGIN_CHANNEL_SECRET
      })
    });
    const tokenData = await tokenRes.json();
    if (!tokenRes.ok || !tokenData.access_token) {
      return lineAuthError("line token exchange failed: " + (tokenData.error_description || tokenData.error || tokenRes.status), 400);
    }
    accessToken = tokenData.access_token;
  } catch (e) {
    return lineAuthError("line token exchange error: " + String(e), 502);
  }

  // 2) access_token → profile（不驗 id_token，直接打 profile API）
  let profile;
  try {
    const profRes = await fetch("https://api.line.me/v2/profile", {
      headers: { "Authorization": `Bearer ${accessToken}` }
    });
    profile = await profRes.json();
    if (!profRes.ok || !profile.userId) {
      return lineAuthError("line profile fetch failed: " + (profile.message || profRes.status), 400);
    }
  } catch (e) {
    return lineAuthError("line profile error: " + String(e), 502);
  }

  const lineUserId = profile.userId;                 // 形如 U + 32 hex
  if (!/^U[0-9a-f]{32}$/i.test(lineUserId)) {
    return lineAuthError("unexpected line userId format", 400);
  }
  const displayName = profile.displayName || "LINE 會員";
  const pictureUrl = profile.pictureUrl || "";
  const email = `line_${lineUserId.toLowerCase()}@line.leadfuai.com`;  // 固定派生、僅作識別鍵，不收信

  const adminHeaders = {
    "apikey": env.SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": `Bearer ${env.SUPABASE_SERVICE_ROLE_KEY}`,
    "Content-Type": "application/json"
  };

  // 3) Supabase admin：建用戶。
  //    盡力而為——回頭客的 email 已存在，不同 GoTrue 版本回 400/409/422 不一，
  //    一律不在這裡 fail；真正的關卡是下一步 generate_link（成功才代表用戶可登入）。
  let userId = null;
  try {
    const createRes = await fetch(`${SUPABASE_PROJECT_URL}/auth/v1/admin/users`, {
      method: "POST",
      headers: adminHeaders,
      body: JSON.stringify({
        email,
        email_confirm: true,
        user_metadata: { name: displayName, picture: pictureUrl, line_user_id: lineUserId, provider: "line" }
      })
    });
    if (createRes.ok) {
      const created = await createRes.json();
      userId = created.id || (created.user && created.user.id) || null;
    }
    // 非 ok（多半是 email 已存在）→ 略過，交給 generate_link
  } catch (e) {
    // 網路層錯誤也不致命，往下讓 generate_link 當關卡
    console.warn("[line-auth] create user error:", String(e));
  }

  // 4) generate_link（magiclink）→ 拿 token_hash（順便補 userId）
  let tokenHash = null;
  try {
    const linkRes = await fetch(`${SUPABASE_PROJECT_URL}/auth/v1/admin/generate_link`, {
      method: "POST",
      headers: adminHeaders,
      body: JSON.stringify({ type: "magiclink", email })
    });
    const linkData = await linkRes.json();
    if (!linkRes.ok) {
      return lineAuthError("supabase generate_link failed: " + linkRes.status + " " + JSON.stringify(linkData).slice(0, 200), 500);
    }
    tokenHash = linkData.hashed_token
      || (linkData.properties && linkData.properties.hashed_token)
      || null;
    if (!userId) {
      userId = linkData.id || (linkData.user && linkData.user.id) || null;
    }
    if (!tokenHash) {
      return lineAuthError("supabase generate_link returned no token", 500);
    }
  } catch (e) {
    return lineAuthError("supabase generate_link error: " + String(e), 502);
  }

  // 5) 把 line_user_id 寫進 profiles（盡力而為，失敗不擋登入；
  //    前端 member.html 也有後備擷取）
  if (userId) {
    try {
      await fetch(`${SUPABASE_PROJECT_URL}/rest/v1/profiles?id=eq.${userId}`, {
        method: "PATCH",
        headers: { ...adminHeaders, "Prefer": "return=minimal" },
        body: JSON.stringify({ line_user_id: lineUserId })
      });
    } catch (e) {
      // 不致命：登入仍成功，line_user_id 之後可由前端補上
      console.warn("[line-auth] profiles patch failed:", String(e));
    }
  }

  return new Response(JSON.stringify({ token_hash: tokenHash, email }), {
    status: 200,
    headers: { "Content-Type": "application/json", ...corsHeaders() }
  });
}


/* ============================================================
 * /api/line-handoff — PWA 登入接力
 *
 * 問題：iOS/Android 把「App(PWA)」和「外部瀏覽器」的登入狀態隔離。
 *   PWA 點 LINE 登入 → 在外部瀏覽器完成 → session 回不到 App。
 * 解法：外部瀏覽器端把 token_hash 暫存進接力站(keyed by 一次性 handoff token H)，
 *   PWA 切回後用 H 取回 token_hash → 自己 verifyOtp → session 建在 PWA。
 *
 *   POST {token,token_hash}  → 存(外部瀏覽器 line-callback 呼叫)
 *   GET  ?token=H            → 取走即刪、僅一次、10 分鐘 TTL(PWA 輪詢)
 *
 * 需 Supabase 建表 auth_handoff(token text pk, token_hash text, created_at timestamptz)。
 * 安全：H 為 128-bit 隨機、僅 PWA 知道；token_hash 本身一次性(verifyOtp 即失效)。
 * ============================================================ */
async function handleLineHandoff(request, env) {
  const adminHeaders = {
    "apikey": env.SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": `Bearer ${env.SUPABASE_SERVICE_ROLE_KEY}`,
    "Content-Type": "application/json"
  };
  const TABLE = `${SUPABASE_PROJECT_URL}/rest/v1/auth_handoff`;

  if (request.method === "POST") {
    let body;
    try { body = await request.json(); } catch { return lineAuthError("invalid json", 400); }
    const token = String((body && body.token) || "").trim();
    const tokenHash = String((body && body.token_hash) || "").trim();
    if (!/^[a-f0-9]{24,128}$/i.test(token) || !tokenHash) return lineAuthError("bad handoff params", 400);
    const res = await fetch(TABLE, {
      method: "POST",
      headers: { ...adminHeaders, "Prefer": "resolution=merge-duplicates,return=minimal" },
      body: JSON.stringify({ token, token_hash: tokenHash, created_at: new Date().toISOString() })
    });
    if (!res.ok) return lineAuthError("handoff store failed: " + res.status + " " + (await res.text()).slice(0, 150), 500);
    return new Response(JSON.stringify({ ok: true }), { status: 200, headers: { "Content-Type": "application/json", ...corsHeaders() } });
  }

  if (request.method === "GET") {
    const token = String(new URL(request.url).searchParams.get("token") || "").trim();
    if (!/^[a-f0-9]{24,128}$/i.test(token)) return lineAuthError("bad token", 400);
    const res = await fetch(`${TABLE}?token=eq.${encodeURIComponent(token)}&select=token_hash,created_at`, { headers: adminHeaders });
    const rows = await res.json().catch(() => []);
    if (!Array.isArray(rows) || !rows.length) {
      return new Response(JSON.stringify({ pending: true }), { status: 200, headers: { "Content-Type": "application/json", ...corsHeaders() } });
    }
    // 取走即刪（一次性）
    await fetch(`${TABLE}?token=eq.${encodeURIComponent(token)}`, { method: "DELETE", headers: adminHeaders });
    const age = Date.now() - new Date(rows[0].created_at).getTime();
    if (age > 10 * 60 * 1000) {
      return new Response(JSON.stringify({ expired: true }), { status: 200, headers: { "Content-Type": "application/json", ...corsHeaders() } });
    }
    return new Response(JSON.stringify({ token_hash: rows[0].token_hash }), { status: 200, headers: { "Content-Type": "application/json", ...corsHeaders() } });
  }

  return lineAuthError("method not allowed", 405);
}


/* ============================================================
 * 綠界 ECPay 定期定額 — VIP 訂閱
 *   /api/ecpay-create  POST {plan, access_token} → {action, fields}（前端組表單送綠界）
 *   /api/ecpay-return  POST（綠界首期付款結果）→ 開通 VIP，回 "1|OK"
 *   /api/ecpay-period  POST（綠界每期定期定額扣款）→ 續期 VIP，回 "1|OK"
 * 未設正式金鑰 → 走綠界公開測試帳號(測試環境)；設 ECPAY_MERCHANT_ID/HASH_KEY/HASH_IV 即切正式。
 * 需 Supabase profiles 欄位：vip_level, vip_until, ecpay_trade_no, ecpay_plan。
 * ============================================================ */
const ECPAY_ANON_KEY = "sb_publishable_hBrtHt8ham91nuXSU_tdmA__BqcfIX1";
const ECPAY_PLANS = {
  "adv-m": { item: "領富AI VIP進階(月付)", amount: 199,  pType: "M", freq: 1, exec: 99, level: "進階" },
  "pro-m": { item: "領富AI VIP旗艦(月付)", amount: 499,  pType: "M", freq: 1, exec: 99, level: "旗艦" },
  "adv-y": { item: "領富AI VIP進階(年付)", amount: 1990, pType: "Y", freq: 1, exec: 9,  level: "進階" },
  "pro-y": { item: "領富AI VIP旗艦(年付)", amount: 4990, pType: "Y", freq: 1, exec: 9,  level: "旗艦" }
};
function ecpayConf(env) {
  if (env.ECPAY_MERCHANT_ID && env.ECPAY_HASH_KEY && env.ECPAY_HASH_IV) {
    return { mid: env.ECPAY_MERCHANT_ID, key: env.ECPAY_HASH_KEY, iv: env.ECPAY_HASH_IV,
             url: "https://payment.ecpay.com.tw/Cashier/AioCheckOut/V5", live: true };
  }
  return { mid: "2000132", key: "5294y06JbISpM5x9", iv: "v77hoKGq4kWxNNIS",
           url: "https://payment-stage.ecpay.com.tw/Cashier/AioCheckOut/V5", live: false };
}
async function ecpayMac(params, key, iv) {
  const ks = Object.keys(params).filter(k => k !== "CheckMacValue" && params[k] != null)
    .sort((a, b) => { const x = a.toLowerCase(), y = b.toLowerCase(); return x < y ? -1 : x > y ? 1 : 0; });
  let raw = `HashKey=${key}&` + ks.map(k => `${k}=${params[k]}`).join("&") + `&HashIV=${iv}`;
  raw = encodeURIComponent(raw).replace(/%20/g, "+").replace(/~/g, "%7e").replace(/'/g, "%27").toLowerCase();
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(raw));
  return [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, "0")).join("").toUpperCase();
}
function ecpayDate() {
  const d = new Date(Date.now() + 8 * 3600 * 1000), p = n => String(n).padStart(2, "0");
  return `${d.getUTCFullYear()}/${p(d.getUTCMonth() + 1)}/${p(d.getUTCDate())} ${p(d.getUTCHours())}:${p(d.getUTCMinutes())}:${p(d.getUTCSeconds())}`;
}
function ecpayTradeNo() {
  const r = new Uint8Array(5); crypto.getRandomValues(r);
  return ("LF" + Date.now().toString(36) + [...r].map(b => b.toString(36)).join("")).replace(/[^0-9a-z]/gi, "").slice(0, 20).toUpperCase();
}
function ecpayAdmin(env) {
  return { "apikey": env.SUPABASE_SERVICE_ROLE_KEY, "Authorization": `Bearer ${env.SUPABASE_SERVICE_ROLE_KEY}`, "Content-Type": "application/json" };
}
async function ecpayUser(token) {
  if (!token) return null;
  try {
    const r = await fetch(`${SUPABASE_PROJECT_URL}/auth/v1/user`, { headers: { "Authorization": `Bearer ${token}`, "apikey": ECPAY_ANON_KEY } });
    if (!r.ok) return null;
    const u = await r.json();
    return (u && u.id) ? u : null;
  } catch { return null; }
}
async function ecpaySetVip(env, userId, planKey, tradeNo) {
  const plan = ECPAY_PLANS[planKey] || {};
  let base = Date.now();
  try {
    const r = await fetch(`${SUPABASE_PROJECT_URL}/rest/v1/profiles?id=eq.${userId}&select=vip_until`, { headers: ecpayAdmin(env) });
    const rows = await r.json();
    if (Array.isArray(rows) && rows[0] && rows[0].vip_until) {
      const t = Date.parse(rows[0].vip_until); if (t > base) base = t;
    }
  } catch {}
  const d = new Date(base);
  if (plan.pType === "Y") d.setUTCFullYear(d.getUTCFullYear() + 1); else d.setUTCMonth(d.getUTCMonth() + 1);
  d.setUTCDate(d.getUTCDate() + 3);   // 寬限 3 天
  const patch = { vip_level: plan.level || "進階", vip_until: d.toISOString(), ecpay_trade_no: tradeNo, ecpay_plan: planKey };
  await fetch(`${SUPABASE_PROJECT_URL}/rest/v1/profiles?id=eq.${userId}`, {
    method: "PATCH", headers: { ...ecpayAdmin(env), "Prefer": "return=minimal" }, body: JSON.stringify(patch)
  });
}
async function handleEcpayCreate(request, env) {
  if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: corsHeaders() });
  const jerr = (m, s) => new Response(JSON.stringify({ error: m }), { status: s || 400, headers: { "Content-Type": "application/json", ...corsHeaders() } });
  if (request.method !== "POST") return jerr("method", 405);
  if (!env.SUPABASE_SERVICE_ROLE_KEY) return jerr("server not configured", 500);
  let body; try { body = await request.json(); } catch { body = {}; }
  const plan = ECPAY_PLANS[body.plan];
  if (!plan) return jerr("unknown plan");
  const user = await ecpayUser(body.access_token);
  if (!user) return jerr("請先登入再訂閱", 401);
  const conf = ecpayConf(env);
  const params = {
    MerchantID: conf.mid,
    MerchantTradeNo: ecpayTradeNo(),
    MerchantTradeDate: ecpayDate(),
    PaymentType: "aio",
    TotalAmount: plan.amount,
    TradeDesc: "LeadFu AI VIP",
    ItemName: plan.item,
    ReturnURL: "https://leadfuai.com/api/ecpay-return",
    ClientBackURL: "https://leadfuai.com/pages/member?vip=ok",
    OrderResultURL: "https://leadfuai.com/api/ecpay-result",
    ChoosePayment: "Credit",
    EncryptType: 1,
    PeriodAmount: plan.amount,
    PeriodType: plan.pType,
    Frequency: plan.freq,
    ExecTimes: plan.exec,
    PeriodReturnURL: "https://leadfuai.com/api/ecpay-period",
    CustomField1: user.id,
    CustomField2: body.plan
  };
  params.CheckMacValue = await ecpayMac(params, conf.key, conf.iv);
  return new Response(JSON.stringify({ action: conf.url, fields: params, test: !conf.live }), {
    status: 200, headers: { "Content-Type": "application/json", ...corsHeaders() }
  });
}
async function handleEcpayReturn(request, env) {
  if (request.method !== "POST") return new Response("0|method", { status: 405 });
  const form = await request.formData();
  const data = {}; for (const [k, v] of form.entries()) data[k] = v;
  const conf = ecpayConf(env);
  const mac = await ecpayMac(data, conf.key, conf.iv);
  if (mac !== String(data.CheckMacValue || "").toUpperCase()) return new Response("0|CheckMacValue", { status: 200 });
  if (String(data.RtnCode) === "1") {
    const plan = ECPAY_PLANS[data.CustomField2];
    if (data.CustomField1 && plan) {
      try { await ecpaySetVip(env, data.CustomField1, data.CustomField2, data.MerchantTradeNo); } catch (e) {}
    }
  }
  return new Response("1|OK", { status: 200 });
}
async function handleEcpayPeriod(request, env) {
  if (request.method !== "POST") return new Response("0|method", { status: 405 });
  const form = await request.formData();
  const data = {}; for (const [k, v] of form.entries()) data[k] = v;
  const conf = ecpayConf(env);
  const mac = await ecpayMac(data, conf.key, conf.iv);
  if (mac !== String(data.CheckMacValue || "").toUpperCase()) return new Response("0|CheckMacValue", { status: 200 });
  if (String(data.RtnCode) === "1") {
    try {
      const r = await fetch(`${SUPABASE_PROJECT_URL}/rest/v1/profiles?ecpay_trade_no=eq.${encodeURIComponent(data.MerchantTradeNo)}&select=id,ecpay_plan`, { headers: ecpayAdmin(env) });
      const rows = await r.json();
      if (Array.isArray(rows) && rows[0]) await ecpaySetVip(env, rows[0].id, rows[0].ecpay_plan, data.MerchantTradeNo);
    } catch (e) {}
  }
  return new Response("1|OK", { status: 200 });
}
async function handleEcpayResult(request, env) {
  // 綠界 OrderResultURL：信用卡付款後瀏覽器會 POST 回來。
  // 順手再開通一次（與 ReturnURL 互為備援），再用 303 轉成 GET 導回乾淨會員頁，避免 .html→307+POST 變空白。
  if (request.method === "POST") {
    try {
      const form = await request.formData();
      const data = {}; for (const [k, v] of form.entries()) data[k] = v;
      const conf = ecpayConf(env);
      const mac = await ecpayMac(data, conf.key, conf.iv);
      if (mac === String(data.CheckMacValue || "").toUpperCase() && String(data.RtnCode) === "1") {
        const plan = ECPAY_PLANS[data.CustomField2];
        if (data.CustomField1 && plan) { try { await ecpaySetVip(env, data.CustomField1, data.CustomField2, data.MerchantTradeNo); } catch (e) {} }
      }
    } catch (e) {}
  }
  return new Response(null, { status: 303, headers: { "Location": "https://leadfuai.com/pages/member?vip=ok" } });
}

/* ── 新聞推播「立即試推一則」：驗登入→讀 line_user_id→配今日新聞→LINE 推一則（驗證綁定+看長相）── */
const NEWS_TOPIC_KW = {
  "半導體": ["半導體","晶圓","晶片","台積電","聯電","封測","日月光","聯發科","記憶體","IC"],
  "AI 人工智慧": ["人工智慧","輝達","NVIDIA","算力","伺服器","資料中心","生成式","GPU","AI"],
  "電動車": ["電動車","特斯拉","Tesla","電池","充電","鋰電","車用","EV"],
  "蘋果供應鏈": ["蘋果","Apple","iPhone","鴻海","大立光","和碩","可成"],
  "金融": ["金控","銀行","升息","降息","央行","壽險","利率","金融股","Fed"],
  "生技醫療": ["生技","醫療","新藥","製藥","疫苗","醫材","臨床"],
  "航運": ["航運","貨櫃","長榮","陽明","萬海","散裝","運價","海運","空運"],
  "綠能重電": ["綠能","重電","太陽能","風電","電網","儲能","台電","光電"],
  "軍工航太": ["軍工","國防","航太","無人機","衛星","低軌"],
  "台股大盤": ["大盤","台股","加權指數","外資","盤勢","成交量","期貨"]
};
function _newsRelated(n) {
  let r = n.ai_related || [];
  if (typeof r === "string") { try { r = JSON.parse(r); } catch { r = []; } }
  return Array.isArray(r) ? r : [];
}
async function handleTestPushNews(request, env) {
  if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: corsHeaders() });
  const jerr = (m, s) => new Response(JSON.stringify({ ok: false, error: m }), { status: s || 400, headers: { "Content-Type": "application/json", ...corsHeaders() } });
  if (request.method !== "POST") return jerr("method", 405);
  let body; try { body = await request.json(); } catch { body = {}; }
  const user = await ecpayUser(body.access_token);
  if (!user) return jerr("請先登入", 401);
  if (!env.LINE_CHANNEL_ACCESS_TOKEN) return jerr("server not configured", 500);
  let prof = {};
  try {
    const r = await fetch(`${SUPABASE_PROJECT_URL}/rest/v1/profiles?id=eq.${user.id}&select=line_user_id,watchlist`, { headers: ecpayAdmin(env) });
    const rows = await r.json();
    prof = (Array.isArray(rows) && rows[0]) ? rows[0] : {};
  } catch (e) {}
  if (!prof.line_user_id) return jerr("你還沒綁定 LINE —— 請改用「LINE 登入」一次，才收得到推播 🙏", 200);
  let news = [];
  try {
    const nr = await fetch("https://leadfuai.com/data/news_live.json?_=" + Date.now(), { cf: { cacheTtl: 0 } });
    const nj = await nr.json();
    news = nj.news || nj.data || nj.articles || [];
  } catch (e) {}
  const topics = Array.isArray(body.topics) ? body.topics : [];
  const wl = body.watchlist ? (prof.watchlist || []) : [];
  const match = (n) => {
    const hay = [n.title || "", n.summary || "", n.ai_note || "", _newsRelated(n).join(" ")].join(" ");
    if (wl.some(c => c && hay.includes(String(c)))) return true;
    return topics.some(t => (NEWS_TOPIC_KW[t] || []).some(k => hay.includes(k)));
  };
  let picks = news.filter(match).slice(0, 5);
  if (!picks.length) picks = news.slice(0, 3);   // 無相符就送最新幾則當範例
  const lines = picks.length
    ? picks.map(n => `・${(n.title || "").trim()}` + (n.source ? `（${n.source}）` : "")).join("\n")
    : "（今天暫無新聞，這是一則測試訊息）";
  const text = `📲 領富 AI ・ 推播試送\n\n${lines}\n\n※ 這是你按「立即試推」的測試訊息，正式推播會依你的設定每日自動送。公開新聞整理、非投資建議。`;
  try {
    const pr = await fetch("https://api.line.me/v2/bot/message/push", {
      method: "POST",
      headers: { "Authorization": `Bearer ${env.LINE_CHANNEL_ACCESS_TOKEN}`, "Content-Type": "application/json" },
      body: JSON.stringify({ to: prof.line_user_id, messages: [{ type: "text", text }] })
    });
    if (!pr.ok) { const et = await pr.text(); return jerr("LINE 推播失敗：" + et.slice(0, 120), 200); }
  } catch (e) { return jerr("LINE 推播發生錯誤", 200); }
  return new Response(JSON.stringify({ ok: true }), { headers: { "Content-Type": "application/json", ...corsHeaders() } });
}

/* ════════ 每日新聞推播（Cloudflare Cron 定時，準時、不受 GitHub Actions 排程延遲）════════ */
async function _linePush(env, to, text) {
  try {
    const r = await fetch("https://api.line.me/v2/bot/message/push", {
      method: "POST",
      headers: { "Authorization": `Bearer ${env.LINE_CHANNEL_ACCESS_TOKEN}`, "Content-Type": "application/json" },
      body: JSON.stringify({ to, messages: [{ type: "text", text }] })
    });
    return r.ok;
  } catch (e) { return false; }
}
async function _assetJson(env, file) {
  try { return await (await env.ASSETS.fetch(new Request("https://placeholder/data/" + file))).json(); }
  catch (e) { return null; }
}
function _newsTopicMatch(item, topic) {
  const kws = NEWS_TOPIC_KW[topic] || [];
  if (!kws.length) return false;
  const hay = [item.title || "", item.summary || "", item.tag || "", item.ai_note || "", _newsRelated(item).join(" ")].join(" ");
  return kws.some(k => hay.includes(k));
}
function buildNewsDigest(topics, news, opts) {
  const o = opts || {};
  const slot = o.slot || "post";
  const cap = Math.max(1, Math.min(o.maxItems || 10, 15));
  const pool = o.importantOnly ? news.filter(n => ["利多", "利空"].includes(String(n.ai_sentiment || "").trim())) : news;
  const blocks = []; let total = 0; const used = new Set();
  const key = n => n.id || n.link || n.title;
  const line = n => `・${(n.title || "").trim()}` + (n.source ? `（${n.source}）` : "");
  const wlCodes = o.wlCodes || []; const nameMap = o.nameMap || {};
  if (wlCodes.length) {
    const terms = new Set();
    for (const c of wlCodes) { if (c) { terms.add(String(c)); if (nameMap[c]) terms.add(nameMap[c]); } }
    const ls = ["⭐ 你的自選股相關"];
    for (const n of pool) {
      if (total >= cap) break;
      const k = key(n); if (used.has(k)) continue;
      const hay = [n.title || "", n.summary || "", n.ai_note || "", _newsRelated(n).join(" ")].join(" ");
      if ([...terms].some(t => hay.includes(t))) { used.add(k); ls.push(line(n)); total++; }
    }
    if (ls.length > 1) blocks.push(ls.join("\n"));
  }
  for (const topic of (topics || [])) {
    if (!NEWS_TOPIC_KW[topic] || total >= cap) continue;
    const hits = pool.filter(n => _newsTopicMatch(n, topic));
    if (!hits.length) continue;
    const ls = [`【${topic}】`];
    for (const n of hits.slice(0, 5)) {
      if (total >= cap) break;
      const k = key(n); if (used.has(k)) continue;
      used.add(k); ls.push(line(n)); total++;
    }
    if (ls.length > 1) blocks.push(ls.join("\n"));
  }
  if (!blocks.length) return null;
  const d = new Date(Date.now() + 8 * 3600 * 1000);
  const md = `${d.getUTCMonth() + 1}/${d.getUTCDate()}`;
  const head = slot === "pre" ? `🌅 領富 AI ・ 開盤前新聞（${md}）\n` : `📰 領富 AI ・ 今日收盤新聞（${md}）\n`;
  const more = o.loginUrl || "https://leadfuai.com/pages/news?openExternalBrowser=1";
  const foot = `\n\n※ 公開新聞整理，非投資建議。\n🔗 更多：${more}\n如需調整或關閉，請至網站會員中心。`;
  return (head + "\n" + blocks.join("\n\n") + foot).slice(0, 4900);
}
async function runNewsPush(env, slot) {
  if (!env.SUPABASE_SERVICE_ROLE_KEY || !env.LINE_CHANNEL_ACCESS_TOKEN) return { sent: 0, error: "not configured" };
  const d = new Date(Date.now() + 8 * 3600 * 1000);
  const today = `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}-${String(d.getUTCDate()).padStart(2, "0")}`;
  const nj = await _assetJson(env, "news_live.json");
  const allNews = (nj && (nj.news || nj.data || nj.articles)) || [];
  const news = allNews.filter(n => String(n.date || "").trim() === today);
  if (!news.length) return { sent: 0, note: "今日無新聞" };
  const sj = await _assetJson(env, "stocks_live.json");
  const nameMap = {}; for (const s of ((sj && sj.stocks) || [])) nameMap[s.code] = s.name || "";
  let members = [];
  try {
    const r = await fetch(`${SUPABASE_PROJECT_URL}/rest/v1/profiles?select=id,line_user_id,news_subs,watchlist&line_user_id=not.is.null`, { headers: ecpayAdmin(env) });
    members = await r.json();
  } catch (e) { return { sent: 0, error: "supabase" }; }
  const lpKey = "last_pushed_" + slot;
  let sent = 0;
  for (const m of (Array.isArray(members) ? members : [])) {
    const subs = m.news_subs;
    if (!subs || typeof subs !== "object" || !subs.active) continue;
    const times = subs.times || ["post"];
    if (!times.includes(slot)) continue;
    const topics = (subs.topics || []).filter(t => NEWS_TOPIC_KW[t]);
    const wantWl = !!subs.watchlist;
    if (!topics.length && !wantWl) continue;
    if (subs[lpKey] === today || (slot === "post" && subs.last_pushed === today)) continue;
    const lt = await makeLoginToken(env, m.id);
    const loginUrl = lt ? `https://leadfuai.com/pages/news?lt=${lt}&openExternalBrowser=1` : null;
    const text = buildNewsDigest(topics, news, { slot, wlCodes: wantWl ? (m.watchlist || []) : [], nameMap, maxItems: subs.max_items || 10, importantOnly: !!subs.important_only, loginUrl });
    if (!text) continue;
    if (await _linePush(env, m.line_user_id, text)) {
      sent++;
      subs[lpKey] = today;
      try { await fetch(`${SUPABASE_PROJECT_URL}/rest/v1/profiles?id=eq.${m.id}`, { method: "PATCH", headers: { ...ecpayAdmin(env), "Prefer": "return=minimal" }, body: JSON.stringify({ news_subs: subs }) }); } catch (e) {}
    }
  }
  return { sent };
}
async function handleManualNewsPush(request, env) {
  const url = new URL(request.url);
  const jerr = (m, s) => new Response(JSON.stringify({ error: m }), { status: s || 400, headers: { "Content-Type": "application/json", ...corsHeaders() } });
  const token = (request.headers.get("Authorization") || "").replace(/^Bearer /, "") || url.searchParams.get("access_token") || "";
  const user = await ecpayUser(token);
  if (!user || !OWNER_UIDS.includes(user.id)) return jerr("owner only", 403);
  const slot = url.searchParams.get("slot") === "pre" ? "pre" : "post";
  const res = await runNewsPush(env, slot);
  return new Response(JSON.stringify({ ok: true, slot, ...res }), { headers: { "Content-Type": "application/json", ...corsHeaders() } });
}

/* ── 推播自動登入：產一次性 token（推播時）+ 兌換成 session（點進來時）──
   推播發給已驗證的 line_user_id，token 只會到本人手機。一次性、7 天效期。
   兌換時才即時產 Supabase magiclink token_hash（避免預產的 1 小時就過期）。 */
async function makeLoginToken(env, userId) {
  try {
    const buf = new Uint8Array(24); crypto.getRandomValues(buf);
    const token = [...buf].map(b => b.toString(16).padStart(2, "0")).join("");
    const r = await fetch(`${SUPABASE_PROJECT_URL}/rest/v1/login_links`, {
      method: "POST", headers: { ...ecpayAdmin(env), "Prefer": "return=minimal" },
      body: JSON.stringify({ token, user_id: userId })
    });
    return r.ok ? token : null;
  } catch (e) { return null; }
}
async function handleLoginToken(request, env) {
  if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: corsHeaders() });
  const jerr = (m, s) => new Response(JSON.stringify({ error: m }), { status: s || 400, headers: { "Content-Type": "application/json", ...corsHeaders() } });
  if (request.method !== "POST") return jerr("method", 405);
  if (!env.SUPABASE_SERVICE_ROLE_KEY) return jerr("server not configured", 500);
  let body; try { body = await request.json(); } catch { body = {}; }
  const token = String(body.token || "");
  if (!/^[a-f0-9]{32,80}$/i.test(token)) return jerr("bad token");
  let row;
  try {
    const r = await fetch(`${SUPABASE_PROJECT_URL}/rest/v1/login_links?token=eq.${token}&select=user_id,created_at`, { headers: ecpayAdmin(env) });
    const rows = await r.json();
    row = Array.isArray(rows) ? rows[0] : null;
  } catch (e) { return jerr("lookup failed", 500); }
  if (!row) return jerr("連結已使用或無效", 401);
  try { await fetch(`${SUPABASE_PROJECT_URL}/rest/v1/login_links?token=eq.${token}`, { method: "DELETE", headers: ecpayAdmin(env) }); } catch (e) {}
  if (Date.now() - Date.parse(row.created_at) > 7 * 86400 * 1000) return jerr("連結已過期", 401);
  let email;
  try {
    const ur = await fetch(`${SUPABASE_PROJECT_URL}/auth/v1/admin/users/${row.user_id}`, { headers: ecpayAdmin(env) });
    const u = await ur.json();
    email = u && u.email;
  } catch (e) {}
  if (!email) return jerr("no email", 400);
  try {
    const gr = await fetch(`${SUPABASE_PROJECT_URL}/auth/v1/admin/generate_link`, {
      method: "POST", headers: { ...ecpayAdmin(env), "Content-Type": "application/json" },
      body: JSON.stringify({ type: "magiclink", email })
    });
    const g = await gr.json();
    const token_hash = g.hashed_token || (g.properties && g.properties.hashed_token);
    if (!token_hash) return jerr("gen failed", 500);
    return new Response(JSON.stringify({ token_hash }), { headers: { "Content-Type": "application/json", ...corsHeaders() } });
  } catch (e) { return jerr("gen error", 500); }
}


/* ============================================================
 * 站長後台：意見回饋清單（owner-only）
 *
 * 安全：含用戶 email，絕不可公開。
 *   1. 前端帶 Supabase access token（登入者的）
 *   2. Worker 用該 token 打 /auth/v1/user 驗證 → 取 user.id
 *   3. user.id 必須在 OWNER_UIDS 白名單，否則 403
 *   4. 通過才用 service_role 撈全部 feedback 回傳（service_role 只在 Worker 端）
 * 不需改 DB / RLS，也不需新密鑰（沿用 SUPABASE_SERVICE_ROLE_KEY）。
 * ============================================================ */
const SUPABASE_ANON_KEY = "sb_publishable_hBrtHt8ham91nuXSU_tdmA__BqcfIX1"; // 公開金鑰，僅用來驗 token
const OWNER_UIDS = [
  "5f5a8d9a-4fa6-4b38-a110-8211edc970e0", // leadwealthai.ai@gmail.com（Google）
  "1f5502ba-7d0a-427f-936f-bbc8b445b03e", // rayda0114@gmail.com（Google）
  "697c1764-e500-42e5-9266-c844fb587890"  // Da（LINE 登入）
  // 之後若新增站長帳號，把該 auth user 的 id 加進這個白名單即可
];

function adminError(msg, status) {
  return new Response(JSON.stringify({ error: msg }), {
    status: status || 400,
    headers: { "Content-Type": "application/json", ...corsHeaders() }
  });
}

async function handleAdminFeedback(request, env) {
  if (request.method === "OPTIONS") {
    return new Response(null, { status: 204, headers: corsHeaders() });
  }
  if (!env.SUPABASE_SERVICE_ROLE_KEY) return adminError("server not configured", 500);

  // 1) 取登入者 token
  const authz = request.headers.get("Authorization") || "";
  const token = authz.replace(/^Bearer\s+/i, "").trim();
  if (!token) return adminError("缺少登入憑證", 401);

  // 2) 驗 token → user
  let user = null;
  try {
    const ures = await fetch(`${SUPABASE_PROJECT_URL}/auth/v1/user`, {
      headers: { "Authorization": `Bearer ${token}`, "apikey": SUPABASE_ANON_KEY }
    });
    if (!ures.ok) return adminError("登入已失效，請重新登入", 401);
    user = await ures.json();
  } catch (e) {
    return adminError("驗證失敗: " + String(e), 502);
  }

  // 3) 站長白名單檢查
  if (!user || !user.id || !OWNER_UIDS.includes(user.id)) {
    return adminError("此帳號無權限（請用站長帳號登入）", 403);
  }

  // 4) service_role 撈全部 feedback（最新在前）
  try {
    const fres = await fetch(`${SUPABASE_PROJECT_URL}/rest/v1/feedback?select=*&order=id.desc`, {
      headers: {
        "apikey": env.SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": `Bearer ${env.SUPABASE_SERVICE_ROLE_KEY}`,
        "Accept": "application/json"
      }
    });
    if (!fres.ok) {
      const t = await fres.text();
      return adminError("讀取失敗: " + fres.status + " " + t.slice(0, 120), 500);
    }
    const data = await fres.json();
    return new Response(JSON.stringify({ feedback: data }), {
      status: 200,
      headers: { "Content-Type": "application/json", "Cache-Control": "no-store", ...corsHeaders() }
    });
  } catch (e) {
    return adminError("讀取錯誤: " + String(e), 502);
  }
}


// ════════════════════════════════════════════════════════════
// LINE 官方帳號 AI 客服 webhook
//   用戶在 LINE @130tqckv 問股票 → AI 用網站官方資料回答（沿用 SYSTEM_PROMPT 合規護欄）
//   env：LINE_CHANNEL_ACCESS_TOKEN（回覆，與推播共用，已設）
//        LINE_MESSAGING_CHANNEL_SECRET（X-Line-Signature 驗章，可選但強烈建議）
//   LINE 後台 Webhook URL 設為：https://leadfuai.com/api/line-webhook
// ════════════════════════════════════════════════════════════
const LINE_REPLY_URL = "https://api.line.me/v2/bot/message/reply";

async function verifyLineSignature(bodyText, signature, secret) {
  if (!signature || !secret) return false;
  try {
    const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(secret),
      { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
    const mac = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(bodyText));
    return btoa(String.fromCharCode(...new Uint8Array(mac))) === signature;
  } catch (e) { return false; }
}

async function lineReply(env, replyToken, text) {
  if (!env.LINE_CHANNEL_ACCESS_TOKEN || !replyToken) return;
  const msg = String(text || "").slice(0, 4900) || "（暫時無法回覆，請稍後再試）";
  try {
    await fetch(LINE_REPLY_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Authorization": `Bearer ${env.LINE_CHANNEL_ACCESS_TOKEN}` },
      body: JSON.stringify({ replyToken, messages: [{ type: "text", text: msg }] })
    });
  } catch (e) {}
}

// 非串流 AI（NVIDIA → Gemini 備援）
async function aiAnswerSync(env, messages, maxTokens = 700) {
  if (env.NVIDIA_API_KEY) {
    try {
      const r = await fetch(NVIDIA_ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": `Bearer ${env.NVIDIA_API_KEY}` },
        body: JSON.stringify({ model: env.NVIDIA_MODEL || DEFAULT_MODEL, messages, temperature: 0.4, max_tokens: maxTokens, stream: false })
      });
      if (r.ok) {
        const j = await r.json();
        const a = j.choices && j.choices[0] && j.choices[0].message && j.choices[0].message.content;
        if (a && a.trim()) return a.trim();
      }
    } catch (e) {}
  }
  const gem = await callGemini(env, messages, maxTokens);
  return (gem.ok && gem.answer) ? gem.answer.trim() : null;
}

// 從問題抓代號/股名 → 用 ASSETS 撈官方資料，組精簡 context（個股給合理區間/估值，ETF 給殖利率/規模/折溢價/成分）
async function getLineStockContext(env, q) {
  if (!env.ASSETS) return "";
  let stocks = [];
  try { stocks = (await (await env.ASSETS.fetch(new Request("https://placeholder/data/stocks_live.json"))).json()).stocks || []; }
  catch (e) { return ""; }
  const codes = (q.match(/\b(00\d{2,4}[A-Z]?|\d{4})\b/g) || []).slice(0, 2);
  let matched = codes.length ? stocks.filter(s => codes.includes(s.code)) : [];
  if (!matched.length && q.length <= 30) {
    matched = stocks.filter(s => s.name && s.name.length >= 2 && q.includes(s.name)).slice(0, 2);
  }
  if (!matched.length) return "";
  // 市場狀態（台北 UTC+8）→ 決定股價的「時間標示」，避免把收盤價講成即時。
  const _tpe = new Date(Date.now() + 8 * 3600 * 1000);
  const _dow = _tpe.getUTCDay(), _hm = _tpe.getUTCHours() * 60 + _tpe.getUTCMinutes();
  const _wd = _dow >= 1 && _dow <= 5;
  const _mState = !_wd ? "holiday" : (_hm < 540 ? "pre" : (_hm <= 810 ? "open" : "closed"));
  const _liveNote = _mState === "open" ? "即時（盤中·延遲約5秒）" : (_mState === "closed" ? "今日收盤" : "上一交易日收盤");
  // 預設「非即時參考價」；抓到 MIS 即時的才覆蓋成有時間標示的價。
  matched = matched.map(s => ({ ...s, _note: "參考價·非即時（請以網站即時報價為準）" }));
  // 用即時報價(MIS) 覆蓋落後的靜態價 —— TWSE 官方日檔(STOCK_DAY_ALL)出得慢，stocks_live 盤中常落後一個交易日。
  try {
    const exch = matched.filter(s => s.status !== "興櫃").map(s => (s.status === "上櫃" ? "otc_" : "tse_") + s.code + ".tw").join("|");
    if (exch) {
      const mr = await fetch(`https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=${encodeURIComponent(exch)}&json=1&delay=0&_=${Math.floor(Date.now() / 5000)}`,
        { headers: { "User-Agent": "Mozilla/5.0", "Accept": "application/json", "Referer": "https://mis.twse.com.tw/stock/fibest.jsp" } });
      const md = await mr.json();
      const qmap = {};
      for (const qq of (md.msgArray || [])) {
        let z = parseFloat(qq.z), approx = false; if (isNaN(z) || z <= 0) z = parseFloat(qq.pz);
        if (isNaN(z) || z <= 0) { const h = parseFloat(qq.h), l = parseFloat(qq.l); if (!isNaN(h) && !isNaN(l) && h > 0 && l > 0) { z = Math.round((h + l) / 2 * 100) / 100; approx = true; } }
        const y = parseFloat(qq.y);
        if (!isNaN(z) && z > 0) qmap[qq.c] = {
          price: Math.round(z * 100) / 100,
          change: (!isNaN(y) && y > 0) ? Math.round((z - y) * 100) / 100 : null,
          note: (approx && _mState === "open") ? "盤中參考（暫無最新成交價，為今日高低中值）" : _liveNote
        };
      }
      matched = matched.map(s => qmap[s.code] ? { ...s, price: qmap[s.code].price, change: qmap[s.code].change, _note: qmap[s.code].note } : s);
    }
  } catch (e) {}
  const grab = async (f) => { try { return (await (await env.ASSETS.fetch(new Request("https://placeholder/data/" + f))).json()).data || {}; } catch (e) { return {}; } };
  const [fv, val, nav, div, hold, basic] = await Promise.all([
    grab("fair_value_live.json"), grab("valuation_live.json"), grab("etf_nav_live.json"),
    grab("etf_div_live.json"), grab("etf_holdings_live.json"), grab("etf_basic_live.json")
  ]);
  const out = matched.map(s => {
    const o = { code: s.code, name: s.name, price: s.price, change: s.change, 股價時間: s._note, category: s.category, market: s.status };
    if (s.category === "ETF") {
      const nv = nav[s.code], dv = div[s.code], h = hold[s.code], b = basic[s.code];
      if (nv) { o.etf_淨值 = nv.nav; o.etf_折溢價百分比 = nv.premium; o.etf_規模億元 = nv.aumYi; }
      if (dv && dv.ttmCash && s.price) o.etf_殖利率百分比 = +(dv.ttmCash / s.price * 100).toFixed(1);
      if (b && b.index) o.etf_追蹤指數 = b.index;
      if (h && h.top) o.etf_前5大成分 = h.top.slice(0, 5).map(t => `${t.name}${t.weight}%`);
    } else {
      if (fv[s.code]) o.合理區間 = fv[s.code];
      if (val[s.code]) o.估值 = val[s.code];
    }
    return o;
  });
  return "\n\n---\n以下是領富 AI 提供的官方公開資料（請優先依此回答，**禁止編造數字**；**提到股價時務必照各檔「股價時間」標示是「即時」還是「收盤」，例如「2330 台積電 即時 2315」或「（今日收盤）」；絕對不可把收盤價/參考價講成即時價**；ETF 殖利率為近一年實際配息估算）：\n```json\n" + JSON.stringify(out).slice(0, 4000) + "\n```";
}

async function lineAnswer(env, q) {
  const ctxData = await getLineStockContext(env, q);
  const sys = SYSTEM_PROMPT + "\n\n【LINE 客服情境】你正在領富 AI 官方 LINE 回覆用戶，回答請**簡潔**、適合手機閱讀、善用換行、不要太長。資料不足就引導用戶到 leadfuai.com 查詢。嚴守合規：不推薦個股、不代操、不保證獲利。";
  const messages = [{ role: "system", content: sys }, { role: "user", content: q + ctxData }];
  const a = await aiAnswerSync(env, messages, 700);
  return a || "不好意思，剛剛忙線了 😅 再問我一次，或上 leadfuai.com 查台股／ETF 資料。";
}

async function handleLineWebhook(request, env, ctx) {
  const bodyText = await request.text();
  if (env.LINE_MESSAGING_CHANNEL_SECRET) {
    const ok = await verifyLineSignature(bodyText, request.headers.get("X-Line-Signature"), env.LINE_MESSAGING_CHANNEL_SECRET);
    if (!ok) return new Response("bad signature", { status: 403 });
  }
  let data;
  try { data = JSON.parse(bodyText); } catch (e) { return new Response("OK", { status: 200 }); }
  const events = (data && data.events) || [];
  const work = (async () => {
    for (const ev of events) {
      try {
        if (ev.type === "follow") {
          await lineReply(env, ev.replyToken, "歡迎加入領富 AI 🌱\n我可以幫你查台股（上市／上櫃／興櫃）＋ ETF 的公開資料 —— 合理區間、月營收、ETF 殖利率／規模／成分股。\n\n直接打代號或公司名問我，例如：\n・「0056 殖利率」\n・「2330 合理價」\n・「00878 是什麼」\n\n⚠ 我們只整理公開資料，不推薦個股、不代操。");
        } else if (ev.type === "message" && ev.message && ev.message.type === "text") {
          await lineReply(env, ev.replyToken, await lineAnswer(env, ev.message.text));
        } else if (ev.type === "message") {
          await lineReply(env, ev.replyToken, "收到 🙌 想查台股／ETF 直接打代號或公司名問我，例如「0050 殖利率」「台積電 合理價」。");
        }
      } catch (e) {}
    }
  })();
  if (ctx && ctx.waitUntil) ctx.waitUntil(work); else await work;
  return new Response("OK", { status: 200 });
}


export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // ── SEO 正規化：www→非 www、http→https（301 永久導向，消除重複網址稀釋排名）──
    if (url.hostname.startsWith("www.") || url.protocol === "http:") {
      url.protocol = "https:";
      url.hostname = url.hostname.replace(/^www\./, "");
      url.port = "";
      return Response.redirect(url.toString(), 301);
    }

    if (url.pathname === "/api/ask")            return handleAsk(request, env);
    if (url.pathname === "/api/health")         return handleHealth(env);
    if (url.pathname === "/api/quote")          return handleQuote(request);
    if (url.pathname === "/api/line-auth")      return handleLineAuth(request, env);
    if (url.pathname === "/api/line-handoff")   return handleLineHandoff(request, env);
    if (url.pathname === "/api/ecpay-create")   return handleEcpayCreate(request, env);
    if (url.pathname === "/api/ecpay-return")   return handleEcpayReturn(request, env);
    if (url.pathname === "/api/ecpay-period")   return handleEcpayPeriod(request, env);
    if (url.pathname === "/api/ecpay-result")   return handleEcpayResult(request, env);
    if (url.pathname === "/api/test-push-news") return handleTestPushNews(request, env);
    if (url.pathname === "/api/admin-feedback") return handleAdminFeedback(request, env);
    if (url.pathname === "/api/line-webhook")   return handleLineWebhook(request, env, ctx);
    if (url.pathname === "/api/cron-news")      return handleManualNewsPush(request, env);
    if (url.pathname === "/api/login-token")    return handleLoginToken(request, env);

    // 其他 path → 交給 ASSETS binding 處理（保留所有原本的靜態行為）
    return env.ASSETS.fetch(request);
  },
  // Cloudflare Cron Triggers：準時跑每日新聞推播（不受 GitHub Actions 排程延遲）
  async scheduled(event, env, ctx) {
    const cron = (event && event.cron) || "";
    // 00:30 UTC = 08:30 台北（盤前，開盤前）；07:50 UTC = 15:50 台北（盤後）。
    ctx.waitUntil(runNewsPush(env, cron.startsWith("30 0 ") ? "pre" : "post"));
  }
};
