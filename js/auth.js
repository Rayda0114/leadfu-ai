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

  /* ── GA4 登入漏斗事件（診斷 form_start→註冊 0 斷在哪一跳）──
     用 transport_type:beacon → 跳轉/重導前也能送出（navigator.sendBeacon）。
     gtag 由各頁 main.js 載入；line-callback 不載 main.js 故自帶 gtag snippet。 */
  _ga(name, params) {
    try {
      if (typeof window.gtag === "function") {
        window.gtag("event", name, Object.assign({ transport_type: "beacon" }, params || {}));
      }
    } catch (e) { /* 追蹤失敗不影響登入 */ }
  },
  /* 登入完成（session 已建立）→ 判斷新註冊 vs 回訪，送 sign_up / login。
     created_at ≈ last_sign_in_at（差 < 8 秒）視為首次＝新註冊；用伺服器兩個時間比，
     不吃使用者端時鐘誤差。沒 session 視為失敗(login_fail/no_session)。
     供 member.html(Google) 與 line-callback(LINE) 共用。回傳是否成功。 */
  async _gaAuthDone(method) {
    try {
      const { data } = await _sb.auth.getUser();
      const u = data && data.user;
      if (!u) { this._ga("login_fail", { method: method, stage: "no_session" }); return false; }
      const c = new Date(u.created_at).getTime();
      const l = new Date(u.last_sign_in_at || u.created_at).getTime();
      const isNew = Math.abs(l - c) < 8000;
      this._ga(isNew ? "sign_up" : "login", { method: method, is_new: isNew });
      return true;
    } catch (e) {
      this._ga("login", { method: method });   // 拿不到 user 細節仍記一筆登入
      return true;
    }
  },

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
    // 廣告轉換：email 註冊成功即記一筆（每瀏覽器只送一次，由 main.js trackLineConversion 控管）
    try { window.LeadFu && window.LeadFu.trackLineConversion && window.LeadFu.trackLineConversion(); } catch (e) {}
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
    this._ga("login_start", { method: provider });   // ① 按鈕：開始登入（跳轉前）
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
  /* 是否在已安裝的 PWA(App, standalone)中執行 */
  _isPWA() {
    try {
      return window.matchMedia("(display-mode: standalone)").matches
        || window.navigator.standalone === true;
    } catch (e) { return false; }
  },
  _rndHex(n) {
    const rnd = new Uint8Array(n);
    (window.crypto || {}).getRandomValues && window.crypto.getRandomValues(rnd);
    return Array.from(rnd, b => b.toString(16).padStart(2, "0")).join("");
  },
  _clearHandoff() {
    try { localStorage.removeItem("leadfu_handoff_pending"); localStorage.removeItem("leadfu_handoff_at"); } catch (e) {}
  },
  /* 回傳仍有效(<9 分鐘)的接力 token；過期則清掉回 "" */
  _pendingHandoff() {
    try {
      const t = localStorage.getItem("leadfu_handoff_pending") || "";
      const at = parseInt(localStorage.getItem("leadfu_handoff_at") || "0", 10);
      if (!t) return "";
      if (Date.now() - at > 9 * 60 * 1000) { this._clearHandoff(); return ""; }
      return t;
    } catch (e) { return ""; }
  },

  async signInWithLine() {
    const CHANNEL_ID = "2010279883";
    const REDIRECT_URI = "https://leadfuai.com/pages/line-callback.html";
    const csrf = this._rndHex(16);
    // PWA(App) → 啟用「登入接力」：授權頁在外部瀏覽器開，session 用一次性 token 接回 App
    const handoff = this._isPWA() ? this._rndHex(24) : "";
    const state = handoff ? (csrf + "~" + handoff) : csrf;
    try {
      sessionStorage.setItem("line_login_state", csrf);
      sessionStorage.setItem("line_login_next", "/pages/member.html");
      if (handoff) {
        localStorage.setItem("leadfu_handoff_pending", handoff);
        localStorage.setItem("leadfu_handoff_at", String(Date.now()));
      }
    } catch (e) { /* 隱私模式可能擋；接力情境會略過 CSRF 比對 */ }
    const authUrl = "https://access.line.me/oauth2/v2.1/authorize?" +
      new URLSearchParams({
        response_type: "code",
        client_id: CHANNEL_ID,
        redirect_uri: REDIRECT_URI,
        state,
        scope: "profile openid"
      }).toString();
    // ⚠ 一律用「同視窗導向」。window.open 在 iOS PWA 會開一個無分頁 UI 的新視窗，
    //   使用者回 App 會看到反白且回不去原頁。改用 location 後：外部瀏覽器完成授權，
    //   App 仍停在本頁（或回前景重載），由 _startHandoffPolling / 載入時的恢復把 session 接回。
    if (handoff) this._startHandoffPolling();
    this._ga("login_start", { method: "line" });   // ① 按鈕：開始 LINE 登入（跳轉前）
    window.location.href = authUrl;
  },

  /* ===== PWA 登入接力輪詢 ===== */
  _handoffTimer: null,
  _visHandler: null,
  async _checkHandoffOnce() {
    const token = this._pendingHandoff();
    if (!token) { this._stopHandoffPolling(); return true; }
    let data = {};
    try {
      const r = await fetch("/api/line-handoff?token=" + encodeURIComponent(token), { cache: "no-store" });
      data = await r.json().catch(() => ({}));
    } catch (e) { return false; }
    if (data.expired) { this._clearHandoff(); this._stopHandoffPolling(); return true; }
    if (!data.token_hash) return false;   // 還沒登入完成，繼續等
    this._clearHandoff();
    try {
      const { error } = await _sb.auth.verifyOtp({ token_hash: data.token_hash, type: "magiclink" });
      if (!error) {
        this._stopHandoffPolling();
        try { await this._gaAuthDone("line"); } catch (e) {}   // ③ PWA 接力建 session 成功
        window.location.replace("/pages/member.html");
        return true;
      }
    } catch (e) {}
    return false;
  },
  _startHandoffPolling() {
    this._stopHandoffPolling();
    let tries = 0;
    const tick = async () => {
      tries++;
      const done = await this._checkHandoffOnce();
      if (done || tries > 120) {              // ~5 分鐘上限
        this._stopHandoffPolling();
        if (tries > 120) this._clearHandoff();
      }
    };
    // App 回到前景立即查一次（最常見觸發點：使用者授權完切回 App）
    this._visHandler = () => { if (!document.hidden) this._checkHandoffOnce(); };
    document.addEventListener("visibilitychange", this._visHandler);
    window.addEventListener("focus", this._visHandler);
    this._handoffTimer = setInterval(tick, 2500);
  },
  _stopHandoffPolling() {
    if (this._handoffTimer) { clearInterval(this._handoffTimer); this._handoffTimer = null; }
    if (this._visHandler) {
      document.removeEventListener("visibilitychange", this._visHandler);
      window.removeEventListener("focus", this._visHandler);
      this._visHandler = null;
    }
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
    // 先讀現有再合併，保留 push 腳本寫的 last_pushed_post/pre（避免存設定後當天重複推播）
    let existing = {};
    try {
      const { data } = await _sb.from("profiles").select("news_subs").eq("id", user.id).single();
      if (data && data.news_subs && typeof data.news_subs === "object") existing = data.news_subs;
    } catch (e) {}
    const merged = { ...existing, ...subs };
    const { error } = await _sb.from("profiles").update({ news_subs: merged }).eq("id", user.id);
    if (error) console.warn("[領富 AI] 寫雲端新聞訂閱失敗:", error.message);
  },

  /* ── 🔔 到價提醒（price_alerts 表，RLS：本人 CRUD）──
     欄位：id / user_id / code / direction('above'|'below') / target(numeric) / note / active / triggered_at / created_at
     盤中 cron（worker.js runPriceAlertCheck）比對現價→LINE 推播，觸發後寫 triggered_at 去重。*/
  async getPriceAlerts() {
    const user = await this.getUser();
    if (!user) return null;
    const { data, error } = await _sb.from("price_alerts").select("*").eq("user_id", user.id).order("created_at", { ascending: false });
    if (error) { console.warn("[領富 AI] 讀到價提醒失敗:", error.message); return null; }
    return data || [];
  },
  async addPriceAlert({ code, direction, target, note }) {
    const user = await this.getUser();
    if (!user) throw new Error("尚未登入");
    const row = { user_id: user.id, code: String(code), direction: (direction === "above" ? "above" : "below"), target: Number(target), note: note || null, active: true };
    const { data, error } = await _sb.from("price_alerts").insert(row).select().single();
    if (error) throw error;
    return data;
  },
  async deletePriceAlert(id) {
    const user = await this.getUser();
    if (!user) throw new Error("尚未登入");
    const { error } = await _sb.from("price_alerts").delete().eq("id", id).eq("user_id", user.id);
    if (error) throw error;
  },
  async setPriceAlertActive(id, active) {
    const user = await this.getUser();
    if (!user) throw new Error("尚未登入");
    const { error } = await _sb.from("price_alerts").update({ active: !!active }).eq("id", id).eq("user_id", user.id);
    if (error) throw error;
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

// PWA 登入接力：頁面載入時若有未完成的接力（App 被系統重啟/重整），恢復輪詢
try {
  if (window.LeadFuAuth._isPWA() && window.LeadFuAuth._pendingHandoff()) {
    window.LeadFuAuth._startHandoffPolling();
  }
} catch (e) {}
