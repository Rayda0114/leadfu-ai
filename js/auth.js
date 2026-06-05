/* ============================================================
 * 領富 AI · 會員系統（Supabase Auth）
 * 依賴：頁面需先載入 @supabase/supabase-js CDN
 *   <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
 *   <script src="../js/auth.js"></script>
 * 用法：window.LeadFuAuth.signUp(...) / signIn(...) / signOut() / getProfile()
 * ============================================================ */

const SUPABASE_URL = "https://lhwxpnyzplylajxunlua.supabase.co";
const SUPABASE_KEY = "sb_publishable_hBrtHt8ham91nuXSU_tdmA__BqcfIX1";

// 建立 Supabase client（全站共用一個）
const _sb = window.supabase.createClient(SUPABASE_URL, SUPABASE_KEY);

window.LeadFuAuth = {
  client: _sb,

  /* 註冊：email/密碼 + 額外 profile 資料（name/phone/experience）
     額外資料用 user_metadata 帶進去，Postgres trigger 會自動建 profiles 列 */
  async signUp({ email, password, name, phone, experience }) {
    const { data, error } = await _sb.auth.signUp({
      email,
      password,
      options: {
        data: { name: name || "", phone: phone || "", experience: experience || "" }
      }
    });
    if (error) throw error;
    // data.session 有值 = 已自動登入（Confirm email 關閉時）
    // data.session 為 null = 需收信確認
    return {
      user: data.user,
      needsConfirmation: !data.session
    };
  },

  /* 登入 */
  async signIn({ email, password }) {
    const { data, error } = await _sb.auth.signInWithPassword({ email, password });
    if (error) throw error;
    return data;
  },

  /* 社群一鍵登入（Google / LINE）
     會跳轉到第三方授權頁，授權後自動導回 member.html */
  async signInWithProvider(provider) {
    const { data, error } = await _sb.auth.signInWithOAuth({
      provider,
      options: {
        redirectTo: window.location.origin + "/pages/member.html"
      }
    });
    if (error) throw error;
    return data;
  },
  async signInWithGoogle()   { return this.signInWithProvider("google"); },

  /* LINE 一鍵登入（方法 ①：自走 LINE OAuth，繞過 Supabase OIDC）
     不用 Supabase Custom OIDC——LINE id_token 是 HS256，Supabase 通用
     OIDC 驗證器只收 ES256/JWKS，永遠驗不過。改成：
       導去 LINE authorize → 回 /pages/line-callback.html（帶 code）
       → callback 把 code 丟給 Worker /api/line-auth 換 session。
     參見 worker.js handleLineAuth。 */
  async signInWithLine() {
    const CHANNEL_ID = "2010279883";
    const REDIRECT_URI = "https://leadfuai.com/pages/line-callback.html";
    // CSRF state
    const rnd = new Uint8Array(16);
    (window.crypto || {}).getRandomValues && window.crypto.getRandomValues(rnd);
    const state = Array.from(rnd, b => b.toString(16).padStart(2, "0")).join("");
    try {
      sessionStorage.setItem("line_login_state", state);
      // 登入後要回哪頁（預設會員中心；登入/註冊頁也都導去會員中心）
      sessionStorage.setItem("line_login_next", "/pages/member.html");
    } catch (e) { /* 隱私模式可能擋 sessionStorage，state 驗證會略過 */ }
    const authUrl = "https://access.line.me/oauth2/v2.1/authorize?" +
      new URLSearchParams({
        response_type: "code",
        client_id: CHANNEL_ID,
        redirect_uri: REDIRECT_URI,
        state,
        scope: "profile openid"
      }).toString();
    window.location.href = authUrl;
  },

  /* 登出 */
  async signOut() {
    await _sb.auth.signOut();
  },

  /* 目前登入的 auth user（沒登入回 null）*/
  async getUser() {
    const { data } = await _sb.auth.getUser();
    return data.user || null;
  },

  /* 取得完整會員資料（auth user + profiles 表）*/
  async getProfile() {
    const user = await this.getUser();
    if (!user) return null;
    const { data, error } = await _sb
      .from("profiles")
      .select("*")
      .eq("id", user.id)
      .single();
    if (error) {
      console.warn("[領富 AI] 讀取 profile 失敗:", error.message);
      return { id: user.id, email: user.email };
    }
    return { ...data, email: user.email };
  },

  /* 更新會員資料 */
  async updateProfile(fields) {
    const user = await this.getUser();
    if (!user) throw new Error("尚未登入");
    const { error } = await _sb
      .from("profiles")
      .update(fields)
      .eq("id", user.id);
    if (error) throw error;
  },

  /* ── 自選股雲端同步（profiles.watchlist 欄位，jsonb）── */
  // 讀雲端自選股；未登入回 null、讀失敗回 null（呼叫端會退回本地 localStorage）
  async getCloudWatchlist() {
    const user = await this.getUser();
    if (!user) return null;
    const { data, error } = await _sb.from("profiles").select("watchlist").eq("id", user.id).single();
    if (error) { console.warn("[領富 AI] 讀雲端自選失敗:", error.message); return null; }
    return Array.isArray(data && data.watchlist) ? data.watchlist : [];
  },
  // 寫雲端自選股（整份覆蓋；未登入則 no-op）
  async setCloudWatchlist(codes) {
    const user = await this.getUser();
    if (!user) return;
    const { error } = await _sb.from("profiles").update({ watchlist: codes }).eq("id", user.id);
    if (error) console.warn("[領富 AI] 寫雲端自選失敗:", error.message);
  },

  /* ── 持股雲端同步（profiles.holdings 欄位，jsonb；格式 {code:{shares,cost}}）── */
  async getCloudHoldings() {
    const user = await this.getUser();
    if (!user) return null;
    const { data, error } = await _sb.from("profiles").select("holdings").eq("id", user.id).single();
    if (error) { console.warn("[領富 AI] 讀雲端持股失敗:", error.message); return null; }
    return (data && data.holdings && typeof data.holdings === "object") ? data.holdings : {};
  },
  async setCloudHoldings(holdings) {
    const user = await this.getUser();
    if (!user) return;
    const { error } = await _sb.from("profiles").update({ holdings }).eq("id", user.id);
    if (error) console.warn("[領富 AI] 寫雲端持股失敗:", error.message);
  },

  /* ── 選股策略雲端同步（profiles.scan_strategies 欄位，jsonb 陣列）──
     每個策略：{ name, filters, scan:bool, last_codes:[...], last_scan:"YYYY-MM-DD" }
     scan=true 的策略由 scripts/scan_strategies.py 每日盤後掃描、把新符合的股票推到 LINE。*/
  async getCloudStrategies() {
    const user = await this.getUser();
    if (!user) return null;
    const { data, error } = await _sb.from("profiles").select("scan_strategies").eq("id", user.id).single();
    if (error) { console.warn("[領富 AI] 讀雲端策略失敗:", error.message); return null; }
    return Array.isArray(data && data.scan_strategies) ? data.scan_strategies : [];
  },
  async setCloudStrategies(strategies) {
    const user = await this.getUser();
    if (!user) return;
    const { error } = await _sb.from("profiles").update({ scan_strategies: strategies }).eq("id", user.id);
    if (error) console.warn("[領富 AI] 寫雲端策略失敗:", error.message);
  },

  /* ── 新聞推播訂閱雲端同步（profiles.news_subs 欄位，jsonb 物件）──
     格式：{ topics:[...], active:bool, last_pushed:"YYYY-MM-DD" }
     由 scripts/push_news_digest.py 每日比對今日新聞、把相符主題推到會員 LINE。
     一併回傳 hasLine（是否已綁 line_user_id），UI 用來判斷能否推播。*/
  async getCloudNewsSubs() {
    const user = await this.getUser();
    if (!user) return null;
    const { data, error } = await _sb.from("profiles").select("news_subs,line_user_id").eq("id", user.id).single();
    if (error) { console.warn("[領富 AI] 讀雲端新聞訂閱失敗:", error.message); return null; }
    const subs = (data && data.news_subs && typeof data.news_subs === "object") ? data.news_subs : {};
    return { subs, hasLine: !!(data && data.line_user_id) };
  },
  async setCloudNewsSubs(subs) {
    const user = await this.getUser();
    if (!user) return;
    const { error } = await _sb.from("profiles").update({ news_subs: subs }).eq("id", user.id);
    if (error) console.warn("[領富 AI] 寫雲端新聞訂閱失敗:", error.message);
  },

  /* 把 Supabase 錯誤碼轉成中文（給 45-75 歲族群看得懂）*/
  zhError(error) {
    const msg = (error && error.message) || String(error);
    const map = {
      "Invalid login credentials": "Email 或密碼錯誤，請重新輸入",
      "User already registered":   "這個 Email 已經註冊過了，請直接登入",
      "Password should be at least 6 characters": "密碼至少要 6 碼",
      "Unable to validate email address": "Email 格式不正確",
      "Email not confirmed": "請先到信箱收確認信並點擊連結",
      "For security purposes, you can only request this after": "操作太頻繁，請稍等幾秒再試",
      "Unsupported provider": "這個登入方式即將開放，請先用 Email 或 Google 登入",
      "provider is not enabled": "這個登入方式即將開放，請先用 Email 或 Google 登入"
    };
    for (const key in map) {
      if (msg.includes(key)) return map[key];
    }
    return "發生錯誤：" + msg;
  }
};
