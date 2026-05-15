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

// 模型測試紀錄：
//   ✘ nvidia/llama-3.3-nemotron-super-49b-v1.5 → 中文 prompt 拒答（「編碼錯誤」）
//   ✘ qwen/qwen2.5-72b-instruct                → Nvidia NIM 沒這模型（404）
//   ✓ meta/llama-3.3-70b-instruct              → 穩定、中文可
// 之後可在 Cloudflare 環境變數 NVIDIA_MODEL 覆寫
const DEFAULT_MODEL = "meta/llama-3.3-70b-instruct";
const NVIDIA_ENDPOINT = "https://integrate.api.nvidia.com/v1/chat/completions";

// 系統 prompt：正面說明角色、清楚列舉可做/不可做
// Qwen 系列不需要 detailed thinking 切換（不是 Nemotron）
const SYSTEM_PROMPT = `你是「領富 AI」（LeadFu AI），台灣財經資訊網站 leadfuai.com 的 AI 助理。

【你的工作】
- 用清楚易懂的繁體中文，幫使用者解答關於股票、市場、財報、公司的問題
- 解釋金融概念（例如：月營收年增率、本益比、興櫃市場、IPO）
- 整理使用者提供的公開資料（個股報價、公司基本資料、月營收等）
- 用淺白語言寫，目標讀者是 45-75 歲台灣投資人，避免複雜術語
- 簡短分段，必要時用條列，但不用 markdown 表格

【免責規則】
你只整理公開資料，不做個股買賣建議。所以：
✔ 可以說：「該股目前股價 X 元」「月營收年增 Y%」「資本額 Z 億」「成立於 19XX 年」
✔ 可以說：「以下是今日成交量前 N 名」「月營收年增率是跟去年同月相比的成長」
✘ 不要說：「建議買進」「建議賣出」「值得買」「會漲」「目標價是」「我看好」「我推薦」「好推薦」「值得關注」
✘ 如有人問「推薦股票」「該不該買」「會不會漲」「有什麼好的」「值不值得」「建議買哪檔」，
   你必須直接回答：「我是資料整理助理，不提供個股推薦或買賣建議。買賣決定請您自行評估或諮詢合法的證券投資顧問。如果您想知道客觀數據（例如今天成交量最大、漲幅最高的股票），我可以幫您整理。」
   不要列出任何個股清單，也不要說「以下是公開資料」之類的開場白，直接給上述回答即可。

回答最後請加一行：
※ 以上為公開資料整理，不構成投資建議，亦非投顧服務。

【資料來源】
使用者訊息中可能含 relevantStocks（個股報價陣列）、companyInfo（公司基本資料）、revenueInfo（月營收）、industryStats（產業統計）等欄位，請優先使用這些資料回答。沒給就用一般金融常識回答。

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
  //   2. 多輪聊天：{ messages: [{role, content}, ...], context }
  const question = (body.question || "").toString().slice(0, 1500);
  const context = body.context || {};
  const incomingMessages = Array.isArray(body.messages) ? body.messages : null;

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
  if (hasContext) {
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

  const model = env.NVIDIA_MODEL || DEFAULT_MODEL;

  const requestBody = JSON.stringify({
    model,
    messages: finalMessages,
    temperature: 0.4,
    top_p: 0.9,
    max_tokens: 800,
    stream: false
  });

  const callNvidia = async () => fetch(NVIDIA_ENDPOINT, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${env.NVIDIA_API_KEY}`,
      "Content-Type": "application/json"
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


export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    if (url.pathname === "/api/ask")    return handleAsk(request, env);
    if (url.pathname === "/api/health") return handleHealth(env);

    // 其他 path → 交給 ASSETS binding 處理（保留所有原本的靜態行為）
    return env.ASSETS.fetch(request);
  }
};
