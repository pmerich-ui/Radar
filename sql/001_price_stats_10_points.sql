-- Apply to the supplied Supabase schema only after its tables exist.
-- Match Python's minimum of 10 actual price observations.
-- This view is an aggregate of observed samples, not proof of continuous
-- 90-day coverage. Source timestamps and merchant validation remain required.
create or replace view deal_stats as
select
  d.id as deal_id,
  d.current_price,
  count(h.*) as points_90d,
  percentile_cont(0.5) within group (order by h.price) as median_90d,
  min(h.price) as min_90d,
  max(h.price) as max_90d,
  case when count(h.*) >= 10
       then round((1 - d.current_price / nullif(percentile_cont(0.5)
            within group (order by h.price),0)) * 100, 1)
  end as discount_vs_median_pct
from deals d
left join price_history h
  on h.deal_id = d.id
 and h.observed_at > now() - interval '90 days'
 and h.observed_at <= now()
group by d.id, d.current_price;
