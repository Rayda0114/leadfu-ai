-- 領富 AI · 市場洞察 SEO 升級：mirofish_briefs 加 slug + meta_description
-- 在 Supabase SQL Editor 執行一次（複製整段 → Run）。冪等，可重複跑。
--
-- 用途：讓每篇 published 文章有獨立 SEO 網址 /insights/{slug}。
--   slug         網址用的識別字（選填）。主編在審核頁填漂亮的英文-連字號 slug，SEO 最佳；
--                留空時 Worker 自動退回用 id（uuid）當網址，所以不填也能正常運作。
--   meta_description  Google 搜尋結果/分享卡片顯示的描述（選填）。留空時 Worker 自動用 thesis。
--
-- 對應程式：worker.js renderInsightArticle / renderInsightsSitemap、pages/insights-admin.html（slug 欄）。

alter table public.mirofish_briefs add column if not exists slug             text;
alter table public.mirofish_briefs add column if not exists meta_description text;

-- slug 唯一（但允許多筆 null：沒填 slug 的文章用 id 當網址，不互相衝突）。
-- partial unique index → 只對「有值」的 slug 強制唯一。
create unique index if not exists mirofish_briefs_slug_key
  on public.mirofish_briefs (slug)
  where slug is not null;

-- 公開頁（/insights/{slug}）查詢：published + slug 命中。
create index if not exists mirofish_briefs_pub_slug_idx
  on public.mirofish_briefs (slug)
  where status = 'published';

-- 備註：RLS 是「列」層級，新欄位 published 列依舊由既有 public_read_published policy 開放匿名讀，
--       不需新增 policy。Worker 以 service_role 讀取，本來就繞過 RLS。
