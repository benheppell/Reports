-- Events report (Tripleseat), London or Paris, monthly or weekly. Source of truth for the function; apply with
-- the Supabase migration tool or psql. Reconciled to the FY25 vs FY26 events decks (Nov 2026).
--
-- Rules
--   enquiries   = leads created in the period (London time)
--   conversion  = share of those leads whose event has a booking definite date
--   confirmed   = events whose booking definite date falls in the period, any current status
--   held        = CLOSED or DEFINITE events dated in the period, not deleted (also last year: Paris rarely
--                 closes events, London has none left Definite)
--   lost        = events first marked LOST in the period. A "lost booking" had been Definite first;
--                 a "lost enquiry" never was. Reason = Tripleseat's lost reason.
--   value       = actual, else grand total, else F&B minimum; every value is net (/1.2)
--   upcoming    = events after the as-of date already confirmed by it
--   forecast    = upcoming at F&B min x the venue's uplift last year (actual / F&B min on closed events)
--   last year   = month: same month a year earlier; week: the same ISO week, 364 days earlier
--   team        = only when p_team is true (the emailed report). The public page never asks for it.
--   market      = 'london' or 'paris' (separate Tripleseat accounts; every row carries its market)

drop function if exists public.events_report_period(date, date, text, boolean);
drop function if exists public.events_report_payload(date);
drop function if exists public.events_report_week_payload(date);

create or replace function public.events_report_period(p_start date, p_end date, p_kind text, p_team boolean default false,
                                                       p_market text default 'london')
returns jsonb language plpgsql stable security definer set search_path = public as $$
declare
  shift interval := case when p_kind = 'week' then interval '364 days' else interval '1 year' end;
  asof date := least(p_end - 1, (now() at time zone 'Europe/London')::date);
  fy0 date := make_date(extract(year from asof)::int - case when extract(month from asof) = 1 then 1 else 0 end, 2, 1);
  fy1 date := (fy0 + interval '1 year')::date;
  ly date := (fy0 - interval '1 year')::date;
  res jsonb;
  team jsonb;
begin
  with
  ev as (
    select e.*, case e.venue when 'Shiro Sushi' then 'Shiro' else e.venue end v,
           case when e.venue in ('Aqua Kyoto','Aqua Nueva') then 'Regent Street'
                when e.venue = 'Shiro Sushi' then 'Shiro' else e.venue end vg,
           coalesce(e.value,0)/1.2 net,
           coalesce(e.booking_definite_date, (e.first_definite_at at time zone 'Europe/London')::date) defd,
           coalesce(e.booking_lost_date, (e.lost_at at time zone 'Europe/London')::date) lostd
    from tripleseat_events e where e.market = p_market),
  ld as (
    select l.*, case l.venue when 'Shiro Sushi' then 'Shiro' else l.venue end v,
           (l.created_at at time zone 'Europe/London')::date cd
    from tripleseat_leads l where l.deleted_at is null and l.market = p_market),
  per as (select 'ty' y, interval '0' sh union all select 'ly', shift),
  enq as (
    select p.y, l.v,
      count(*) filter (where l.cd >= p_start - p.sh and l.cd < p_end - p.sh) month_n,
      count(*) filter (where l.cd >= fy0 - p.sh and l.cd <= asof - p.sh) fytd_n,
      count(*) filter (where l.cd >= fy0 - p.sh and l.cd <= asof - p.sh and e.booking_definite_date is not null) fytd_conv
    from per p cross join ld l left join ev e on e.event_id = l.event_id
    group by 1,2),
  enq_m as (
    select p.y, to_char(date_trunc('month', l.cd + p.sh), 'YYYY-MM') mon, count(*) n
    from per p join ld l on l.cd >= fy0 - p.sh and l.cd <= asof - p.sh
    group by 1,2),
  conf as (
    select p.y, e.v,
      case when p_kind = 'week' then extract(isodow from e.booking_definite_date)::int
           else least(4, (extract(day from e.booking_definite_date)::int - 1) / 7 + 1) end wk,
      count(*) n, sum(e.net) val
    from per p join ev e on e.booking_definite_date >= p_start - p.sh and e.booking_definite_date < p_end - p.sh
    group by 1,2,3),
  held_p as (
    select p.y, e.v, count(*) n, sum(e.net) val
    from per p join ev e on e.event_date >= p_start - p.sh and e.event_date < p_end - p.sh
    where e.deleted_at is null and e.status in ('CLOSED','DEFINITE')
    group by 1,2),
  held as (
    select p.y, e.v, to_char(date_trunc('month', e.event_date + p.sh), 'YYYY-MM') mon, count(*) n, sum(e.net) val
    from per p join ev e on e.event_date >= fy0 - p.sh and e.event_date <= asof - p.sh
    where e.deleted_at is null and e.status in ('CLOSED','DEFINITE')
    group by 1,2,3),
  lost as (
    select p.y, e.v, case when e.defd is not null then 'booking' else 'enquiry' end kind,
      coalesce(e.lost_reason, 'No reason recorded') reason, count(*) n, sum(e.net) val
    from per p join ev e on e.lostd >= p_start - p.sh and e.lostd < p_end - p.sh
    where e.deleted_at is null and e.status = 'LOST'
    group by 1,2,3,4),
  uplift as (
    select e.vg, sum(e.actual_amount) / nullif(sum(e.food_and_beverage_min),0) u
    from ev e where e.status = 'CLOSED' and e.deleted_at is null and e.event_date >= ly and e.event_date < fy0
      and e.actual_amount > 0 and e.food_and_beverage_min > 0
    group by 1),
  up as (
    select e.* from ev e
    where e.deleted_at is null and e.event_date > asof and e.event_date < fy1
      and e.status in ('CLOSED','DEFINITE') and e.defd <= asof),
  fy as (
    select e.v, e.vg,
      count(*) filter (where e.event_date >= ly and e.event_date < fy0 and e.status in ('CLOSED','DEFINITE')) ly_n,
      sum(e.net) filter (where e.event_date >= ly and e.event_date < fy0 and e.status in ('CLOSED','DEFINITE')) ly_val,
      count(*) filter (where e.event_date >= fy0 and e.event_date <= asof and e.status in ('CLOSED','DEFINITE')) done_n,
      sum(e.net) filter (where e.event_date >= fy0 and e.event_date <= asof and e.status in ('CLOSED','DEFINITE')) done_val,
      (select count(*) from up where up.v = e.v) up_n,
      (select sum(up.net) from up where up.v = e.v) up_val,
      (select sum(case when up.food_and_beverage_min > 0 and u.u is not null
                       then greatest(up.food_and_beverage_min * u.u / 1.2, up.net) else up.net end)
         from up left join uplift u on u.vg = up.vg where up.v = e.v) up_fc
    from ev e where e.deleted_at is null
    group by 1,2),
  rooms as (
    select e.event_id,
      count(*) filter (where r.room_class = 'Exclusive hire') x,
      count(*) filter (where r.room_class = 'Semi-exclusive & wings') s,
      count(*) filter (where r.room_class = 'PDR') p,
      count(*) filter (where r.room_class = 'Multiple PDR') mp,
      count(*) filter (where r.room_class = 'Restaurant') g,
      min(coalesce(r.area, r.name)) filter (where r.room_class = 'Semi-exclusive & wings') area,
      string_agg(distinct coalesce(r.name, 'Unnamed room'), ' + ' order by coalesce(r.name, 'Unnamed room')) room_names
    from ev e cross join lateral unnest(e.room_ids) rid left join tripleseat_rooms r on r.room_id = rid
    where e.event_date >= ly and e.event_date < fy1
    group by 1),
  bt as (
    select e.event_id, e.net, e.v, coalesce(r.room_names, 'No room set') rooms,
      case when e.event_date >= fy0 then 'ty' else 'ly' end y,
      case when coalesce(r.x,0) > 0 then 'Exclusive hire'
           when coalesce(r.s,0) > 0 then 'Semi-exclusive & wings'
           when coalesce(r.mp,0) > 0 or coalesce(r.p,0) > 1 then 'Multiple PDR'
           when coalesce(r.p,0) = 1 then 'Single PDR'
           when coalesce(r.g,0) > 0 then 'Group booking'
           else 'Unmapped' end btype,
      r.area
    from ev e left join rooms r on r.event_id = e.event_id
    where e.deleted_at is null
      and ((e.event_date >= ly and e.event_date < fy0 and e.status in ('CLOSED','DEFINITE'))
        or (e.event_date >= fy0 and e.event_date <= asof and e.status in ('CLOSED','DEFINITE'))
        or e.event_id in (select event_id from up))),
  -- the months ahead: confirmed (as at the as-of date) and still under discussion (current status)
  fwd as (
    select to_char(date_trunc('month', e.event_date), 'YYYY-MM') mon, e.v,
      count(*) filter (where e.status in ('CLOSED','DEFINITE') and e.defd <= asof) conf_n,
      sum(e.net) filter (where e.status in ('CLOSED','DEFINITE') and e.defd <= asof) conf_val,
      count(*) filter (where e.status in ('TENTATIVE','PROSPECT')) disc_n,
      sum(e.net) filter (where e.status in ('TENTATIVE','PROSPECT')) disc_val
    from ev e where e.deleted_at is null and e.event_date > asof
      and e.event_date < date_trunc('month', asof) + interval '7 months'
    group by 1,2),
  -- last year's held revenue by month, labelled with this year's month
  mly as (
    select to_char(date_trunc('month', e.event_date + interval '1 year'), 'YYYY-MM') mon, e.v, count(*) n, sum(e.net) val
    from ev e where e.deleted_at is null and e.status in ('CLOSED','DEFINITE') and e.event_date >= ly
      and e.event_date < date_trunc('month', asof) + interval '7 months' - interval '1 year'
    group by 1,2),
  -- the next three whole months after the as-of month: confirmed by the as-of date, against the same point last year
  -- (confirmed by the same date a year earlier, including events lost since) and last year's final
  ahead as (
    select coalesce(a.mon, b.mon) mon, coalesce(a.v, b.v) v,
      coalesce(a.conf_n, 0) conf_n, coalesce(a.conf, 0) conf, coalesce(a.disc_n, 0) disc_n, coalesce(a.disc, 0) disc,
      coalesce(b.pace_n, 0) pace_n, coalesce(b.pace, 0) pace, coalesce(b.fin_n, 0) fin_n, coalesce(b.fin, 0) fin
    from (
      select to_char(date_trunc('month', e.event_date), 'YYYY-MM') mon, e.v,
        count(*) filter (where e.status in ('CLOSED','DEFINITE') and e.defd <= asof) conf_n,
        sum(e.net) filter (where e.status in ('CLOSED','DEFINITE') and e.defd <= asof) conf,
        count(*) filter (where e.status in ('TENTATIVE','PROSPECT')) disc_n,
        sum(e.net) filter (where e.status in ('TENTATIVE','PROSPECT')) disc
      from ev e where e.deleted_at is null
        and e.event_date >= date_trunc('month', asof) + interval '1 month'
        and e.event_date < date_trunc('month', asof) + interval '4 months'
      group by 1,2) a
    full join (
      select to_char(date_trunc('month', e.event_date + interval '1 year'), 'YYYY-MM') mon, e.v,
        count(*) filter (where e.status in ('CLOSED','DEFINITE')) fin_n,
        sum(e.net) filter (where e.status in ('CLOSED','DEFINITE')) fin,
        count(*) filter (where e.defd <= asof - interval '1 year' and (e.status in ('CLOSED','DEFINITE') or (e.status = 'LOST' and e.lostd > asof - interval '1 year'))) pace_n,
        sum(e.net) filter (where e.defd <= asof - interval '1 year' and (e.status in ('CLOSED','DEFINITE') or (e.status = 'LOST' and e.lostd > asof - interval '1 year'))) pace
      from ev e where e.deleted_at is null
        and e.event_date >= date_trunc('month', asof) + interval '1 month' - interval '1 year'
        and e.event_date < date_trunc('month', asof) + interval '4 months' - interval '1 year'
      group by 1,2) b on a.mon = b.mon and a.v = b.v),
  -- the selected period's own book (used when a future month is picked): confirmed for it as at the as-of date,
  -- against the same point last year, last year's final, and under discussion now
  books as (
    select coalesce(a.v, b.v) v,
      coalesce(a.conf_n, 0) conf_n, coalesce(a.conf, 0) conf, coalesce(a.disc_n, 0) disc_n, coalesce(a.disc, 0) disc,
      coalesce(b.pace_n, 0) pace_n, coalesce(b.pace, 0) pace, coalesce(b.fin_n, 0) fin_n, coalesce(b.fin, 0) fin
    from (
      select e.v,
        count(*) filter (where e.status in ('CLOSED','DEFINITE') and e.defd <= asof) conf_n,
        sum(e.net) filter (where e.status in ('CLOSED','DEFINITE') and e.defd <= asof) conf,
        count(*) filter (where e.status in ('TENTATIVE','PROSPECT')) disc_n,
        sum(e.net) filter (where e.status in ('TENTATIVE','PROSPECT')) disc
      from ev e where e.deleted_at is null and e.event_date >= p_start and e.event_date < p_end
      group by 1) a
    full join (
      select e.v,
        count(*) filter (where e.status in ('CLOSED','DEFINITE')) fin_n,
        sum(e.net) filter (where e.status in ('CLOSED','DEFINITE')) fin,
        count(*) filter (where e.defd <= asof - shift and (e.status in ('CLOSED','DEFINITE') or (e.status = 'LOST' and e.lostd > asof - shift))) pace_n,
        sum(e.net) filter (where e.defd <= asof - shift and (e.status in ('CLOSED','DEFINITE') or (e.status = 'LOST' and e.lostd > asof - shift))) pace
      from ev e where e.deleted_at is null and e.event_date >= p_start - shift and e.event_date < p_end - shift
      group by 1) b on a.v = b.v)
  select jsonb_build_object(
    'market', p_market, 'kind', p_kind, 'start', p_start, 'end', p_end - 1,
    'month', to_char(p_start,'YYYY-MM'), 'as_of', asof, 'fy_start', fy0, 'fy_label', 'FY' || to_char(fy0,'YY'),
    'pulled_at', (select max(pulled_at) from tripleseat_events where market = p_market),
    'enquiries', (select jsonb_agg(enq) from enq),
    'enquiries_by_month', (select jsonb_agg(enq_m order by mon) from enq_m),
    'confirmed', (select jsonb_agg(conf) from conf),
    'held_period', (select jsonb_agg(held_p) from held_p),
    'held', (select jsonb_agg(held) from held),
    'lost', (select jsonb_agg(lost) from lost),
    'full_year', (select jsonb_agg(fy) from fy),
    'uplift', (select jsonb_agg(uplift) from uplift),
    'targets', (select jsonb_agg(t) from events_targets t where t.fy = extract(year from fy0)::int and t.market = p_market),
    'targets_monthly', (select jsonb_agg(jsonb_build_object('mon', to_char(t.month,'YYYY-MM'), 'target', t.target) order by t.month)
                        from events_targets_monthly t where t.market = p_market and t.month >= fy0
                          and t.month < greatest(fy1, (date_trunc('month', asof) + interval '7 months')::date)),
    'forward', (select jsonb_agg(fwd order by mon) from fwd),
    'ahead', (select jsonb_agg(ahead order by mon) from ahead),
    'books', (select jsonb_agg(books) from books),
    'held_ly_by_month', (select jsonb_agg(mly order by mon) from mly),
    'booking_type', (select jsonb_agg(x) from (select y, btype, count(*) n, sum(net) val from bt group by 1,2) x),
    'areas', (select jsonb_agg(x) from (select y, area, count(*) n, sum(net) val from bt where btype = 'Semi-exclusive & wings' group by 1,2) x),
    -- by venue (and, for booking types, by room): the page filters and drills down on these
    'enquiries_by_month_v', (select jsonb_agg(x) from (
        select p.y, l.v, to_char(date_trunc('month', l.cd + p.sh), 'YYYY-MM') mon, count(*) n
        from per p join ld l on l.cd >= fy0 - p.sh and l.cd <= asof - p.sh group by 1,2,3) x),
    'booking_type_rooms', (select jsonb_agg(x) from (select y, v, btype, rooms, count(*) n, sum(net) val from bt group by 1,2,3,4) x),
    'areas_v', (select jsonb_agg(x) from (select y, v, area, count(*) n, sum(net) val from bt where btype = 'Semi-exclusive & wings' group by 1,2,3) x)
  ) into res;

  if p_team then
    with
    ev as (
      select e.*, case e.venue when 'Shiro Sushi' then 'Shiro' else e.venue end v, coalesce(e.value,0)/1.2 net,
             coalesce(e.booking_lost_date, (e.lost_at at time zone 'Europe/London')::date) lostd,
             coalesce(u.name, 'Unassigned') who
      from tripleseat_events e left join tripleseat_users u on u.user_id = e.owner_id
      where e.deleted_at is null and e.market = p_market),
    ld as (
      select (l.created_at at time zone 'Europe/London')::date cd, e.*
      from tripleseat_leads l join ev e on e.event_id = l.event_id where l.deleted_at is null and l.market = p_market)
    select jsonb_agg(x) into team from (
      select coalesce(a.v, b.v) v, coalesce(a.who, b.who) who,
        coalesce(a.enq_p,0) enq_p, coalesce(a.fytd_n,0) fytd_n, coalesce(a.fytd_conv,0) fytd_conv,
        coalesce(b.conf_n,0) conf_n, coalesce(b.conf_val,0) conf_val,
        coalesce(b.lost_enq,0) lost_enq, coalesce(b.lost_book,0) lost_book, coalesce(b.lost_book_val,0) lost_book_val
      from (
        select v, who,
          count(*) filter (where cd >= p_start and cd < p_end) enq_p,
          count(*) filter (where cd >= fy0 and cd <= asof) fytd_n,
          count(*) filter (where cd >= fy0 and cd <= asof and booking_definite_date is not null) fytd_conv
        from ld group by 1,2) a
      full join (
        select v, who,
          count(*) filter (where booking_definite_date >= p_start and booking_definite_date < p_end) conf_n,
          sum(net) filter (where booking_definite_date >= p_start and booking_definite_date < p_end) conf_val,
          count(*) filter (where status = 'LOST' and lostd >= p_start and lostd < p_end and first_definite_at is null and booking_definite_date is null) lost_enq,
          count(*) filter (where status = 'LOST' and lostd >= p_start and lostd < p_end and (first_definite_at is not null or booking_definite_date is not null)) lost_book,
          sum(net) filter (where status = 'LOST' and lostd >= p_start and lostd < p_end and (first_definite_at is not null or booking_definite_date is not null)) lost_book_val
        from ev group by 1,2) b on a.v = b.v and a.who = b.who
    ) x where enq_p + fytd_n + conf_n + lost_enq + lost_book > 0;
    res := res || jsonb_build_object('team', coalesce(team, '[]'::jsonb));
  end if;
  return res;
end $$;
revoke all on function public.events_report_period(date, date, text, boolean, text) from public, anon, authenticated;

-- Public page: month or ISO week, never the team view.
create or replace function public.events_report_payload(p_month date, p_market text default 'london')
returns jsonb language sql stable security definer set search_path = public as $$
  select public.events_report_period(date_trunc('month', p_month)::date,
                                     (date_trunc('month', p_month) + interval '1 month')::date, 'month', false, p_market)
$$;
create or replace function public.events_report_week_payload(p_week date, p_market text default 'london')
returns jsonb language sql stable security definer set search_path = public as $$
  select public.events_report_period(date_trunc('week', p_week)::date, (date_trunc('week', p_week) + interval '7 days')::date,
                                     'week', false, p_market)
$$;
revoke all on function public.events_report_payload(date, text) from public, anon, authenticated;
revoke all on function public.events_report_week_payload(date, text) from public, anon, authenticated;
