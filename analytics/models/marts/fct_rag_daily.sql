select
  cast(created_at as date) as activity_date,
  route,
  count(*) as answer_count,
  avg(latency_ms) as latency_mean_ms,
  avg(case when abstained then 1.0 else 0.0 end) as abstention_rate,
  avg(case when citation_count > 0 then 1.0 else 0.0 end) as citation_coverage
from {{ source('app', 'rag_answer_audit') }}
group by 1, 2
