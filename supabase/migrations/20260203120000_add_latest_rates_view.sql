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
