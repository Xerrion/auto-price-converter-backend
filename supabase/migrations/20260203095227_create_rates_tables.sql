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
