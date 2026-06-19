-- 領富 AI · MiroFish/選題引擎 內容橋：選題簡報（mirofish_briefs）
-- 在 Supabase SQL Editor 執行一次（複製整段 → Run）。冪等，可重複跑。
--
-- 用途：外部「選題引擎」產生的 brief（題材方向，非事實內容）由 Worker
--   /api/mirofish-ingest 以 service_role 寫進這張表，狀態一律 draft。
--   主編在審核 UI 用真實來源把 article_md 重寫好，人工按發佈才會 published。
--
-- ⚠️ YMYL 財經內容：published 只能由主編在 UI 人工推進；端點與本表都沒有自動發佈路徑。
--
-- 狀態機：draft（引擎進來）→ pending_review（主編寫好 article_md）
--          → published（主編人工發佈）／ rejected（主編退回）
--
-- 權限（RLS）：
--   owner_all              站長白名單（沿用 worker.js OWNER_UIDS）可全 CRUD
--   public_read_published  已發佈的列開放公開讀（給前端 /insights 渲染）
--   Worker 用 service_role 寫入會繞過 RLS，不受上面 policy 限制（但端點自己擋成 draft）。

create table if not exists public.mirofish_briefs (
  id            uuid primary key default gen_random_uuid(),

  -- 來自選題引擎的原始方向（只讀參考，不直接出稿）
  title_hint    text not null,                 -- 建議標題
  thesis        text not null,                 -- 核心預測/主軸（產業/題材，非個股）
  points        jsonb,                         -- [{point, needs_verify:true}] 論點＋待查證旗標
  seo_keywords  text[],                        -- SEO 關鍵字
  sectors       jsonb,                         -- [{sector, sample_tickers:[...]}] 代表族群（待查證）
  risk_notes    text[],                        -- 風險/時點提醒（含反方觀點）
  source_meta   jsonb,                         -- {report_id, sim_id, seed_label, brief_md, ...} 來源與原始 brief

  -- 主編產出
  article_md    text,                          -- 主編查證後重寫的正式文章（繁中），引擎進來時為 null

  -- 狀態機
  status        text not null default 'draft'
                check (status in ('draft','pending_review','published','rejected')),
  quality_flags jsonb,                         -- 自動品質閘門結果（供主編參考）
  verify_report jsonb,                          -- L3 AI 查證清單：[{claim, basis, source, verdict, ...}]（供主編逐條核可）

  created_by    uuid references auth.users(id),
  reviewed_by   uuid references auth.users(id),
  created_at    timestamptz not null default now(),
  published_at  timestamptz,
  updated_at    timestamptz not null default now()
);

-- 常用查詢索引：審核清單（依狀態＋時間）、公開頁（已發佈依發佈時間）
create index if not exists mirofish_briefs_status_idx
  on public.mirofish_briefs (status, created_at desc);
create index if not exists mirofish_briefs_published_idx
  on public.mirofish_briefs (published_at desc) where status = 'published';

-- updated_at 自動更新（任何 update 都把 updated_at 設成 now()）
create or replace function public.touch_mirofish_briefs_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at := now();
  return new;
end;
$$;

drop trigger if exists trg_touch_mirofish_briefs on public.mirofish_briefs;
create trigger trg_touch_mirofish_briefs
  before update on public.mirofish_briefs
  for each row
  execute function public.touch_mirofish_briefs_updated_at();

-- ── RLS ──
-- 既有安裝補欄位（L3 查證清單；新建的表上面已含此欄，這行只為舊表升級用，冪等）
alter table public.mirofish_briefs add column if not exists verify_report jsonb;

alter table public.mirofish_briefs enable row level security;

-- 站長白名單可全 CRUD（沿用 worker.js OWNER_UIDS 的三個 id）。
--   for all 省略 with check 時，using 條件同時當 insert/update 的檢查條件。
drop policy if exists "owner_all" on public.mirofish_briefs;
create policy "owner_all" on public.mirofish_briefs
  for all using (
    auth.uid() = any (array[
      '5f5a8d9a-4fa6-4b38-a110-8211edc970e0',  -- leadwealthai.ai@gmail.com（Google）
      '1f5502ba-7d0a-427f-936f-bbc8b445b03e',  -- rayda0114@gmail.com（Google）
      '697c1764-e500-42e5-9266-c844fb587890'   -- Da（LINE 登入）
    ]::uuid[])
  )
  with check (
    auth.uid() = any (array[
      '5f5a8d9a-4fa6-4b38-a110-8211edc970e0',
      '1f5502ba-7d0a-427f-936f-bbc8b445b03e',
      '697c1764-e500-42e5-9266-c844fb587890'
    ]::uuid[])
  );

-- 已發佈的文章開放公開讀（匿名也能讀，給 /insights 前端）。
drop policy if exists "public_read_published" on public.mirofish_briefs;
create policy "public_read_published" on public.mirofish_briefs
  for select using (status = 'published');
