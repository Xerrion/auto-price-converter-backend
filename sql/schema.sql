create extension if not exists "pgcrypto";

create table if not exists public.rates_runs (
  id uuid primary key default gen_random_uuid(),
  provider text not null,
  base text not null,
  date date not null,
  fetched_at timestamptz not null default now()
);

create table if not exists public.rates_entries (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references public.rates_runs(id) on delete cascade,
  currency text not null,
  rate numeric not null
);

create index if not exists rates_runs_provider_fetched_at_idx
  on public.rates_runs (provider, fetched_at desc);

create index if not exists rates_entries_run_id_idx
  on public.rates_entries (run_id);

create table if not exists public.symbols_runs (
  id uuid primary key default gen_random_uuid(),
  provider text not null,
  fetched_at timestamptz not null default now(),
  symbols jsonb not null
);

create index if not exists symbols_runs_provider_fetched_at_idx
  on public.symbols_runs (provider, fetched_at desc);

create or replace view public.latest_rates as
select
  rr.provider,
  rr.base,
  rr.date,
  rr.fetched_at,
  jsonb_object_agg(re.currency, re.rate order by re.currency) as rates
from public.rates_runs rr
join public.rates_entries re on re.run_id = rr.id
where rr.id in (
  select distinct on (provider) id
  from public.rates_runs
  order by provider, fetched_at desc
)
group by rr.id, rr.provider, rr.base, rr.date, rr.fetched_at;

create or replace view public.latest_symbols as
select distinct on (provider)
  provider,
  fetched_at,
  symbols
from public.symbols_runs
order by provider, fetched_at desc;
