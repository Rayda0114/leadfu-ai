-- 領富 AI · 每日新聞推播（第一期）所需資料表變更
-- 在 Supabase SQL Editor 執行一次即可。
--
-- 為 profiles 新增 news_subs（jsonb）欄位，存每位會員的新聞推播訂閱：
--   {
--     "topics": ["半導體", "AI 人工智慧", ...],   -- 勾選的主題（須與 push_news_digest.py 的 TOPICS 一致）
--     "active": true,                              -- 總開關
--     "last_pushed": "2026-06-05"                  -- 上次推播日期（同一天不重推；由腳本回寫）
--   }
--
-- 權限：沿用 profiles 既有 RLS（會員只能讀寫自己的列；服務端 service_role 可全讀寫），
--       news_subs 只是新欄位，無需新增 policy。前端 js/auth.js 以 update 寫入，
--       後端 scripts/push_news_digest.py 以 service_role 讀取並回寫 last_pushed。

alter table public.profiles
  add column if not exists news_subs jsonb not null default '{}'::jsonb;

-- （選用）若想用 GIN 索引加速「找出有啟用推播的會員」可加：
-- create index if not exists profiles_news_subs_active_idx
--   on public.profiles ((news_subs->>'active')) where (news_subs->>'active') = 'true';
