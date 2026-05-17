/**
 * 領富 AI · Cloudflare Worker（自訂 API + 靜態資源）
 *
 * 路由：
 *   /api/ask     → AI 問答（Nvidia API）
 *   /api/health  → 健康檢查
 *   其他         → 靜態資源（ASSETS binding）
 *
 * 環境變數（在 Cloudflare Dashboard → Settings → Variables and Secrets 設）：
 *   NVIDIA_API_KEY  (Secret)
 *   NVIDIA_MODEL    (Plain Text，預設 meta/llama-3.3-70b-instruct)
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

// 系統 prompt：正面說明角色、清楚列舉可做/不可做
// 開頭 "detailed thinking off" 是給 Nemotron 系列模型用，告訴它不要做無聲推理直接回答；
// 對其他模型（Llama 等）這行會被當成普通指令忽略，不影響運作。
const SYSTEM_PROMPT = `detailed thinking off

你是「領富 AI」（LeadFu AI），台灣財經資訊網站 leadfuai.com 的 AI 助理。

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

不要單純拒絕。而是用以下三段式結構回答（用自己的話自然寫，不要照抄）：

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
- watchlistStocks（使用者自選股即時報價）
- watchlistCompanies（自選股公司基本資料）
- watchlistRevenue（自選股月營收）
- watchlistNews（自選股近期相關新聞）
- watchlistAnnouncements（自選股重大公告 / 注意股）
- watchlistIsEmpty: true（使用者還沒加任何自選股）

【被問自選股時】
- 如 watchlistIsEmpty=true：友善告訴使用者「您還沒加任何自選股，先到個股頁面按『＋自選』加入幾檔，下次就能直接問我了」
- 如有自選股資料：根據使用者問題，**整合多源資料**回答。例如：
  - 「我的自選股今天怎樣」→ 列出每檔的代號名稱、價格、漲跌（元+%）、所屬市場
  - 「我自選股有什麼新聞」→ 用 watchlistNews 整理近期新聞要點（含日期）
  - 「我自選股月營收」→ 用 watchlistRevenue 整理每檔的最新月營收 + 年增率
  - 「我自選股有沒有公告」→ 用 watchlistAnnouncements 提醒注意股或處置股
  - 「自選股全部一次幫我看」→ 跨資料源綜合整理（股價 + 新聞 + 重大訊息）

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


/* CORS / preflight */
function corsHeaders() {
  return {
    "Access-Control-Allow-Origin": "https://leadfuai.com",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "86400"
  };
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
    context.companyInfo || context.revenueInfo || context.industryStats;

  let augmentedLast = lastUserContent;
  const hasWatchlistContext = context.watchlistStocks
    || context.watchlistNews
    || context.watchlistAnnouncements
    || context.watchlistCompanies
    || context.watchlistRevenue
    || (context.watchlistIsEmpty === true);

  if (hasContext || hasWatchlistContext) {
    augmentedLast += `\n\n---\n以下是領富 AI 網站提供給你的相關公開資料，請優先依此回答：`;
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

  const requestBody = JSON.stringify({
    model,
    messages: finalMessages,
    temperature: 0.4,
    top_p: 0.9,
    max_tokens: 800,
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

  let aiResp;
  try {
    aiResp = await callNvidia();
    // 429 = rate limit，等 1.5 秒重試一次（免費 tier 容易遇到）
    if (aiResp.status === 429) {
      await new Promise(r => setTimeout(r, 1500));
      aiResp = await callNvidia();
    }
    // 5xx 也重試一次（暫時服務問題）
    if (aiResp.status >= 500 && aiResp.status < 600) {
      await new Promise(r => setTimeout(r, 1200));
      aiResp = await callNvidia();
    }
  } catch (err) {
    return new Response(JSON.stringify({ error: "AI 服務連線失敗，請稍後再試", detail: err.message }), {
      status: 502,
      headers: { "Content-Type": "application/json", ...corsHeaders() }
    });
  }

  // === Streaming 模式：直接把 Nvidia SSE 串流轉發給前端 ===
  if (wantStream && aiResp.ok) {
    return new Response(aiResp.body, {
      status: 200,
      headers: {
        "Content-Type": "text/event-stream; charset=utf-8",
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
        ...corsHeaders()
      }
    });
  }

  if (!aiResp.ok) {
    const errText = await aiResp.text().catch(() => "");
    // 把常見錯誤碼轉成中文（前端會直接顯示）
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
    const errMsg = friendlyMap[aiResp.status] || `AI 服務異常 (代碼 ${aiResp.status})`;
    return new Response(JSON.stringify({ error: errMsg, status: aiResp.status, detail: errText.slice(0, 300) }), {
      status: 502,
      headers: { "Content-Type": "application/json", ...corsHeaders() }
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

  return new Response(JSON.stringify({
    answer,
    model,
    usage: data?.usage || null
  }), {
    headers: { "Content-Type": "application/json; charset=utf-8", ...corsHeaders() }
  });
}


/* /api/health */
function handleHealth(env) {
  return new Response(JSON.stringify({
    ok: true,
    hasKey: !!env.NVIDIA_API_KEY,
    model: env.NVIDIA_MODEL || DEFAULT_MODEL,
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


export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    if (url.pathname === "/api/ask")    return handleAsk(request, env);
    if (url.pathname === "/api/health") return handleHealth(env);
    if (url.pathname === "/api/quote")  return handleQuote(request);

    // 其他 path → 交給 ASSETS binding 處理（保留所有原本的靜態行為）
    return env.ASSETS.fetch(request);
  }
};
