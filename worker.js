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

// Nemotron Super 49B 對中文 prompt 不穩（連續測試多次都回「編碼錯誤」拒答）
// 改用 Qwen 2.5 72B Instruct（Alibaba 中文母系訓練、對繁中表現最好）
// 可在 Cloudflare 環境變數 NVIDIA_MODEL 覆寫切換
const DEFAULT_MODEL = "qwen/qwen2.5-72b-instruct";
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
✔ 可以說：「以下是符合條件的公司列表」「月營收年增率是跟去年同月相比的成長」
✘ 不要說：「建議買進」「建議賣出」「值得買」「會漲」「目標價是」「我看好」「我推薦」
✘ 如有人問「該不該買」「會不會漲」，回答：「我只整理公開資料給您參考，買賣決定請您自行評估或諮詢合法投顧」

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

  const question = (body.question || "").toString().slice(0, 800);
  const context = body.context || {};
  if (!question.trim()) {
    return new Response(JSON.stringify({ error: "No question provided" }), {
      status: 400,
      headers: { "Content-Type": "application/json", ...corsHeaders() }
    });
  }

  // 組裝 user message：問題在最上面，context 用 markdown 樣式包起來，
  // 不要在最後加任何「請依鐵則」之類的句子，否則模型會困惑找鐵則
  let userMsg = question;
  const hasContext =
    (context.relevantStocks && context.relevantStocks.length) ||
    context.companyInfo || context.revenueInfo || context.industryStats;

  if (hasContext) {
    userMsg += `\n\n---\n以下是領富 AI 網站提供給你的相關公開資料，請優先依此回答：`;
    if (context.relevantStocks && context.relevantStocks.length) {
      userMsg += `\n\n### 相關個股\n\`\`\`json\n${JSON.stringify(context.relevantStocks).slice(0, 8000)}\n\`\`\``;
    }
    if (context.companyInfo) {
      userMsg += `\n\n### 公司基本資料\n\`\`\`json\n${JSON.stringify(context.companyInfo).slice(0, 3000)}\n\`\`\``;
    }
    if (context.revenueInfo) {
      userMsg += `\n\n### 月營收\n\`\`\`json\n${JSON.stringify(context.revenueInfo).slice(0, 2000)}\n\`\`\``;
    }
    if (context.industryStats) {
      userMsg += `\n\n### 產業統計\n\`\`\`json\n${JSON.stringify(context.industryStats).slice(0, 2000)}\n\`\`\``;
    }
  }

  const model = env.NVIDIA_MODEL || DEFAULT_MODEL;

  let aiResp;
  try {
    aiResp = await fetch(NVIDIA_ENDPOINT, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${env.NVIDIA_API_KEY}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        model,
        messages: [
          { role: "system", content: SYSTEM_PROMPT },
          { role: "user", content: userMsg }
        ],
        temperature: 0.3,
        top_p: 0.9,
        max_tokens: 700,
        stream: false
      })
    });
  } catch (err) {
    return new Response(JSON.stringify({ error: "Network error calling AI service", detail: err.message }), {
      status: 502,
      headers: { "Content-Type": "application/json", ...corsHeaders() }
    });
  }

  if (!aiResp.ok) {
    const errText = await aiResp.text().catch(() => "");
    return new Response(JSON.stringify({ error: `AI service error (HTTP ${aiResp.status})`, detail: errText.slice(0, 300) }), {
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
