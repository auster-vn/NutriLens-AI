alter table rag_documents add column if not exists content_hash text;
alter table rag_documents add column if not exists version integer not null default 1;
alter table rag_documents add column if not exists updated_at timestamptz not null default now();

create table if not exists data_pipeline_runs (
  id text primary key default gen_random_uuid()::text,
  pipeline text not null,
  status text not null default 'running',
  config_json jsonb not null default '{}'::jsonb,
  input_count integer not null default 0,
  output_count integer not null default 0,
  rejected_count integer not null default 0,
  metrics_json jsonb not null default '{}'::jsonb,
  error_message text,
  started_at timestamptz not null default now(),
  finished_at timestamptz
);

create table if not exists rag_releases (
  id text primary key default gen_random_uuid()::text,
  version text not null unique,
  status text not null default 'draft',
  manifest_hash text not null,
  pipeline_run_id text not null references data_pipeline_runs(id),
  document_count integer not null default 0,
  chunk_count integer not null default 0,
  metrics_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  published_at timestamptz
);

create table if not exists rag_chunks (
  id text primary key default gen_random_uuid()::text,
  release_id text not null references rag_releases(id) on delete cascade,
  source_document_id text references rag_documents(id) on delete set null,
  source_filename text not null,
  source_title text not null,
  source_url text,
  chunk_index integer not null,
  heading_path jsonb not null default '[]'::jsonb,
  content text not null,
  content_hash text not null,
  token_count integer not null,
  metadata_json jsonb not null default '{}'::jsonb,
  embedding jsonb not null default '[]'::jsonb,
  embedding_model text not null,
  created_at timestamptz not null default now(),
  constraint uq_rag_chunk_release_source_index unique (release_id, source_filename, chunk_index)
);

create table if not exists rag_evaluation_runs (
  id text primary key default gen_random_uuid()::text,
  release_id text references rag_releases(id),
  dataset_name text not null,
  dataset_hash text not null,
  metrics_json jsonb not null default '{}'::jsonb,
  case_results jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists ix_data_pipeline_runs_pipeline_started
  on data_pipeline_runs(pipeline, started_at desc);
create index if not exists ix_rag_releases_status_created
  on rag_releases(status, created_at desc);
create index if not exists ix_rag_chunks_release_source
  on rag_chunks(release_id, source_filename);
create index if not exists ix_rag_chunks_content_hash
  on rag_chunks(content_hash);
create index if not exists ix_rag_evaluation_runs_release_created
  on rag_evaluation_runs(release_id, created_at desc);
