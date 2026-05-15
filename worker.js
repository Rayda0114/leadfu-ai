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

// Phase 1：先用 Nemotron Super 49B 單模型測試（品質/速度/成本最平衡）
// Phase 2 後可在 Cloudflare 環境變數 NVIDIA_MODEL 覆寫切換其他模型
const DEFAULT_MODEL = "nvidia/llama-3.3-nemotron-super-49b-v1.5";
const NVIDIA_ENDPOINT = "https://integrate.api.nvidia.com/v1/chat/completions";

// Nemotron 系列特殊：需要在 system prompt 開頭明確切換思考模式
// "detailed thinking off" → 直接回答（適合即時對話 UI）
// "detailed thinking on"  → 顯示推理過程（適合複雜分析，但慢且耗 token）
const SYSTEM_PROMPT = `detailed thinking off

你是「領富 AI」的資料整理助理（LeadFu AI），服務台灣 45-75 歲投資人，目標是用清楚、保守、易懂的繁體中文，整理公開市場資料。

═══════ 鐵則（違反任何一條都算嚴重失敗）═══════
1. 只描述客觀資料（成交量、漲跌幅、財報指標、公司資料、月營收）。
2. 絕對禁止使用：「買進、買入、賣出、加碼、減碼、布局、進場、出場、推薦、看好、不看好、目標價、評等、上看 X 元、應該、值得、可以買、可以賣、強力買進、建議買、建議賣」。
3. 不能講「應該」「值得」「划算」「便宜」「貴」這類決策性形容詞——只能用「目前價位 X 元」「相對於前日漲/跌 X%」這種純描述。
4. 不能說「未來會」「會繼續」「即將」這種預測性詞彙。
5. 如果使用者問「該不該買 / 值不值得買 / 會不會漲」之類問題，必須回：「我只能整理公開資料給您參考，買賣決定請您自行評估或諮詢合法的證券投資顧問。」
6. 每次回答最後必須加上一行（不要省略）：
   「※ 以上為公開資料整理，不構成投資建議，亦非證券投資顧問服務。」

═══════ 回答風格 ═══════
- 用繁體中文。短句，分段，給 45-75 歲族群閱讀。
- 不用 markdown 表格（前端會自己排版），用條列或自然段落即可。
- 不引用「網路資料」「我的訓練資料」之類字眼，只引用使用者提供的 context 或公開常識。
- 不知道答案就老實說「目前資料無法判斷」，不要編造。

═══════ Context 使用 ═══════
- 使用者可能會給你「relevantStocks」「companyInfo」「revenueInfo」這些資料 chunk，請優先使用。
- 沒給就回答一般性教育性問題（什麼是月營收年增、台股交易時間等）。`;


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

  // 組裝 user prompt
  let userMsg = `使用者問題：${question}\n`;
  if (context.relevantStocks && context.relevantStocks.length) {
    userMsg += `\n相關個股資料：\n${JSON.stringify(context.relevantStocks).slice(0, 8000)}\n`;
  }
  if (context.companyInfo) {
    userMsg += `\n公司基本資料：\n${JSON.stringify(context.companyInfo).slice(0, 3000)}\n`;
  }
  if (context.revenueInfo) {
    userMsg += `\n月營收資料：\n${JSON.stringify(context.revenueInfo).slice(0, 2000)}\n`;
  }
  if (context.industryStats) {
    userMsg += `\n產業統計：\n${JSON.stringify(context.industryStats).slice(0, 2000)}\n`;
  }
  userMsg += `\n請依鐵則回答。`;

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
