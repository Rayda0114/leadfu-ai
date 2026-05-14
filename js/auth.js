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

  /* 社群一鍵登入（Google / Facebook）
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
  async signInWithFacebook() { return this.signInWithProvider("facebook"); },

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

  /* 把 Supabase 錯誤碼轉成中文（給 45-75 歲族群看得懂）*/
  zhError(error) {
    const msg = (error && error.message) || String(error);
    const map = {
      "Invalid login credentials": "Email 或密碼錯誤，請重新輸入",
      "User already registered":   "這個 Email 已經註冊過了，請直接登入",
      "Password should be at least 6 characters": "密碼至少要 6 碼",
      "Unable to validate email address": "Email 格式不正確",
      "Email not confirmed": "請先到信箱收確認信並點擊連結",
      "For security purposes, you can only request this after": "操作太頻繁，請稍等幾秒再試"
    };
    for (const key in map) {
      if (msg.includes(key)) return map[key];
    }
    return "發生錯誤：" + msg;
  }
};
