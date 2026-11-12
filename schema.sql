-- Run once in Supabase SQL Editor. Rerunnable. Never disable RLS.
begin;
create table if not exists public.admins(user_id uuid primary key references auth.users(id) on delete cascade);
alter table public.admins enable row level security;
create or replace function public.is_garden_admin() returns boolean language sql stable security definer set search_path=public as $$ select exists(select 1 from public.admins where user_id=auth.uid()) $$;
revoke all on function public.is_garden_admin() from public;
grant execute on function public.is_garden_admin() to anon,authenticated;
create table if not exists public.posts(
 id uuid primary key default gen_random_uuid(), user_id uuid not null references auth.users(id) on delete cascade,
 kind text not null check(kind in ('forum','help')), title text not null check(char_length(trim(title)) between 3 and 100),
 content text not null check(char_length(trim(content)) between 5 and 6000 and (kind!='help' or char_length(content)<=1200)),
 nickname text not null check(char_length(nickname) between 1 and 24), category text not null check(category in ('闲聊','番剧讨论','推荐分享','寻番','观看问题','其他')),
 created_at timestamptz not null default now(), hidden boolean not null default false, accepted_reply uuid
);
create table if not exists public.replies(
 id uuid primary key default gen_random_uuid(),post_id uuid not null references public.posts(id) on delete cascade,
 user_id uuid not null references auth.users(id) on delete cascade,nickname text not null check(char_length(nickname) between 1 and 24),
 content text not null check(char_length(trim(content)) between 2 and 2000),created_at timestamptz not null default now()
);
do $$ begin if not exists(select 1 from pg_constraint where conname='posts_accepted_reply_fkey') then alter table public.posts add constraint posts_accepted_reply_fkey foreign key(accepted_reply) references public.replies(id) on delete set null; end if; end $$;
create table if not exists public.likes(post_id uuid not null references public.posts(id) on delete cascade,user_id uuid not null references auth.users(id) on delete cascade,primary key(post_id,user_id));
create table if not exists public.reports(id uuid primary key default gen_random_uuid(),post_id uuid not null references public.posts(id) on delete cascade,reply_id uuid references public.replies(id) on delete set null,user_id uuid not null references auth.users(id) on delete cascade,reason text not null check(char_length(reason) between 2 and 600),status text not null default 'pending' check(status in ('pending','resolved','dismissed')),created_at timestamptz not null default now());
create index if not exists posts_kind_date on public.posts(kind,created_at desc);
create index if not exists replies_post on public.replies(post_id,created_at);
create index if not exists reports_status on public.reports(status,created_at);
alter table public.posts enable row level security;
alter table public.replies enable row level security;
alter table public.likes enable row level security;
alter table public.reports enable row level security;
-- Protect immutable ownership and moderation columns even from an author's PATCH.
create or replace function public.garden_guard() returns trigger language plpgsql set search_path=public as $$
begin
 if tg_op='INSERT' then
  if new.hidden or new.accepted_reply is not null then raise exception 'Invalid initial state'; end if;
  new.created_at=now();
 else
  if new.user_id is distinct from old.user_id or new.id is distinct from old.id or new.kind is distinct from old.kind or new.created_at is distinct from old.created_at or new.nickname is distinct from old.nickname then raise exception 'Immutable post fields'; end if;
  if new.hidden is distinct from old.hidden and not public.is_garden_admin() then raise exception 'Moderator required'; end if;
 end if;
 if new.accepted_reply is not null and (new.kind!='help' or not exists(select 1 from public.replies where id=new.accepted_reply and post_id=new.id)) then raise exception 'Reply must belong to this help post'; end if;
 return new;
end $$;
drop trigger if exists garden_guard on public.posts;
create trigger garden_guard before insert or update on public.posts for each row execute function public.garden_guard();
create or replace function public.garden_report_guard() returns trigger language plpgsql set search_path=public as $$ begin
 if tg_op='INSERT' then
  if new.status!='pending' then raise exception 'Initial status must be pending';end if;
  if new.reply_id is not null and not exists(select 1 from public.replies where id=new.reply_id and post_id=new.post_id) then raise exception 'Reply must belong to post';end if;
  new.created_at=now();
 else
  if new.id is distinct from old.id or new.post_id is distinct from old.post_id or new.user_id is distinct from old.user_id or new.reason is distinct from old.reason or new.created_at is distinct from old.created_at then raise exception 'Only report status may change';end if;
  -- FK ON DELETE SET NULL may clear reply_id after a moderator deletes a reply.
  if new.reply_id is distinct from old.reply_id and new.reply_id is not null then raise exception 'Cannot change reply target';end if;
 end if;
 return new;
end $$;
drop trigger if exists garden_report_guard on public.reports;
create trigger garden_report_guard before insert or update on public.reports for each row execute function public.garden_report_guard();
drop policy if exists admins_read on public.admins;
create policy admins_read on public.admins for select to authenticated using(user_id=auth.uid());
drop policy if exists posts_read on public.posts;
create policy posts_read on public.posts for select to anon,authenticated using(not hidden or public.is_garden_admin());
drop policy if exists posts_create on public.posts;
create policy posts_create on public.posts for insert to authenticated with check(user_id=auth.uid() and not hidden);
drop policy if exists posts_edit on public.posts;
create policy posts_edit on public.posts for update to authenticated using((user_id=auth.uid() and not hidden) or public.is_garden_admin()) with check(user_id=auth.uid() or public.is_garden_admin());
drop policy if exists posts_delete on public.posts;
create policy posts_delete on public.posts for delete to authenticated using(user_id=auth.uid() or public.is_garden_admin());
drop policy if exists replies_read on public.replies;
create policy replies_read on public.replies for select to anon,authenticated using(exists(select 1 from public.posts where id=post_id and (not hidden or public.is_garden_admin())));
drop policy if exists replies_create on public.replies;
create policy replies_create on public.replies for insert to authenticated with check(user_id=auth.uid() and exists(select 1 from public.posts where id=post_id and not hidden));
drop policy if exists replies_delete on public.replies;
create policy replies_delete on public.replies for delete to authenticated using(user_id=auth.uid() or public.is_garden_admin());
drop policy if exists likes_read on public.likes;
create policy likes_read on public.likes for select to anon,authenticated using(exists(select 1 from public.posts where id=post_id and not hidden));
drop policy if exists likes_create on public.likes;
create policy likes_create on public.likes for insert to authenticated with check(user_id=auth.uid() and exists(select 1 from public.posts where id=post_id and not hidden));
drop policy if exists likes_delete on public.likes;
create policy likes_delete on public.likes for delete to authenticated using(user_id=auth.uid());
drop policy if exists reports_read on public.reports;
create policy reports_read on public.reports for select to authenticated using(user_id=auth.uid() or public.is_garden_admin());
drop policy if exists reports_create on public.reports;
create policy reports_create on public.reports for insert to authenticated with check(user_id=auth.uid() and status='pending' and exists(select 1 from public.posts where id=post_id and not hidden));
drop policy if exists reports_update on public.reports;
create policy reports_update on public.reports for update to authenticated using(public.is_garden_admin()) with check(public.is_garden_admin());
grant usage on schema public to anon,authenticated;
grant select on public.posts,public.replies,public.likes to anon;
grant select,insert,update,delete on public.posts to authenticated;
grant select,insert,delete on public.replies,public.likes to authenticated;
grant select,insert,update on public.reports to authenticated;
grant select on public.admins to authenticated;
revoke insert,update,delete on public.admins from anon,authenticated;
commit;
-- After registering your admin account, promote ONLY through SQL Editor:
-- insert into public.admins(user_id) select id from auth.users where email='your-admin-email@example.com' on conflict do nothing;
