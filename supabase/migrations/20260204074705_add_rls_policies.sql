-- Enable RLS on all tables
alter table public.rates_runs enable row level security;
alter table public.rates_entries enable row level security;
alter table public.symbols_runs enable row level security;

-- Drop existing policies if any (idempotent)
drop policy if exists "Service role has full access to rates_runs" on public.rates_runs;
drop policy if exists "Service role has full access to rates_entries" on public.rates_entries;
drop policy if exists "Service role has full access to symbols_runs" on public.symbols_runs;
drop policy if exists "Public read access to rates_runs" on public.rates_runs;
drop policy if exists "Public read access to rates_entries" on public.rates_entries;
drop policy if exists "Public read access to symbols_runs" on public.symbols_runs;

-- Service role policies (full access for backend)
-- The service role key is kept secret in the backend .env
create policy "Service role has full access to rates_runs"
  on public.rates_runs
  for all
  to service_role
  using (true)
  with check (true);

create policy "Service role has full access to rates_entries"
  on public.rates_entries
  for all
  to service_role
  using (true)
  with check (true);

create policy "Service role has full access to symbols_runs"
  on public.symbols_runs
  for all
  to service_role
  using (true)
  with check (true);

-- Public policies (read-only for Chrome extension using anon key)
create policy "Public read access to rates_runs"
  on public.rates_runs
  for select
  to anon
  using (true);

create policy "Public read access to rates_entries"
  on public.rates_entries
  for select
  to anon
  using (true);

create policy "Public read access to symbols_runs"
  on public.symbols_runs
  for select
  to anon
  using (true);
