-- 領富 AI · 到價提醒（price_alerts）
-- 在 Supabase SQL Editor 執行一次（複製整段貼上 → Run）。
-- 前端用 supabase-js 在 RLS 下自行 CRUD（auth.js getPriceAlerts/addPriceAlert/…）；
-- 盤中由 Cloudflare Worker runPriceAlertCheck（service_role）比對現價、到價推播 LINE，
-- 觸發後寫 triggered_at 並 active=false 去重。

create table if not exists public.price_alerts (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid not null references auth.users(id) on delete cascade,
  code         text not null,
  direction    text not null default 'below' check (direction in ('above','below')),
  target       numeric not null check (target > 0),
  note         text,
  active       boolean not null default true,
  triggered_at timestamptz,
  created_at   timestamptz not null default now()
);

create index if not exists price_alerts_active_idx on public.price_alerts (active, triggered_at);
create index if not exists price_alerts_user_idx   on public.price_alerts (user_id);

alter table public.price_alerts enable row level security;

-- 本人才能讀／新增／修改／刪除自己的提醒；service_role（Worker 檢查程式）繞過 RLS 不需額外 policy。
drop policy if exists "price_alerts own select" on public.price_alerts;
create policy "price_alerts own select" on public.price_alerts for select using (auth.uid() = user_id);

drop policy if exists "price_alerts own insert" on public.price_alerts;
create policy "price_alerts own insert" on public.price_alerts for insert with check (auth.uid() = user_id);

drop policy if exists "price_alerts own update" on public.price_alerts;
create policy "price_alerts own update" on public.price_alerts for update using (auth.uid() = user_id);

drop policy if exists "price_alerts own delete" on public.price_alerts;
create policy "price_alerts own delete" on public.price_alerts for delete using (auth.uid() = user_id);
