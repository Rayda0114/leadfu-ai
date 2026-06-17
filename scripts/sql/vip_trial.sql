-- 領富 AI · 新會員自動送 7 天 VIP 試用
-- 在 Supabase SQL Editor 執行一次（複製整段 → Run）。
-- 作法：profiles 新建一列時（不管 email / Google / LINE 哪種註冊），若還沒有 vip_until，
--   自動給 now()+7 天、vip_level='試用'。到期後 vip_until 變過去 → 自動回免費，不自動扣款。
-- 只影響「之後新註冊」的人；現有用戶不變。

create or replace function public.grant_trial_vip()
returns trigger
language plpgsql
as $$
begin
  if new.vip_until is null then
    new.vip_until := now() + interval '7 days';
    new.vip_level := coalesce(nullif(new.vip_level, ''), '試用');
  end if;
  return new;
end;
$$;

drop trigger if exists trg_grant_trial_vip on public.profiles;
create trigger trg_grant_trial_vip
  before insert on public.profiles
  for each row
  execute function public.grant_trial_vip();

-- （選用）想讓「現有的免費會員」也補一次 7 天試用體驗，把下面這行的註解拿掉再跑一次：
-- update public.profiles set vip_until = now() + interval '7 days', vip_level = '試用'
--   where vip_until is null or vip_until < now();
