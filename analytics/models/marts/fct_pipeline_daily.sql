select
  cast(started_at as date) as activity_date,
  pipeline,
  count(*) as run_count,
  sum(case when status = 'succeeded' then 1 else 0 end) as succeeded_count,
  sum(case when status in ('failed', 'blocked') then 1 else 0 end) as failed_count,
  sum(output_count) as output_count
from {{ source('app', 'data_pipeline_runs') }}
group by 1, 2
