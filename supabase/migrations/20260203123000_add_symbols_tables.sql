create table if not exists public.symbols_runs (
  id uuid primary key default gen_random_uuid(),
  provider text not null,
  fetched_at timestamptz not null default now(),
  symbols jsonb not null
);

create index if not exists symbols_runs_provider_fetched_at_idx
  on public.symbols_runs (provider, fetched_at desc);

create or replace view public.latest_symbols as
select distinct on (provider)
  provider,
  fetched_at,
  symbols
from public.symbols_runs
order by provider, fetched_at desc;
