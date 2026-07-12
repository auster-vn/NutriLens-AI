create table if not exists product_label_extractions (
  id varchar(36) primary key,
  barcode varchar(32) not null,
  user_id varchar(36) references users(id),
  status varchar(32) not null default 'needs_review',
  image_sha256 varchar(64) not null,
  image_mime varchar(64) not null,
  ocr_provider varchar(64) not null,
  extractor_version varchar(32) not null,
  raw_text text not null,
  words_json jsonb not null default '[]'::jsonb,
  preprocessing_json jsonb not null default '{}'::jsonb,
  provider_runs_json jsonb not null default '[]'::jsonb,
  extracted_json jsonb not null default '{}'::jsonb,
  confidence double precision not null default 0,
  validation_issues jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  confirmed_at timestamptz
);

create index if not exists ix_product_label_extractions_barcode_created
  on product_label_extractions(barcode, created_at desc);
create index if not exists ix_product_label_extractions_status
  on product_label_extractions(status);

create table if not exists label_ocr_evaluation_runs (
  id varchar(36) primary key,
  dataset_name varchar(255) not null,
  dataset_hash varchar(64) not null,
  providers jsonb not null default '[]'::jsonb,
  metrics_json jsonb not null default '{}'::jsonb,
  case_results jsonb not null default '[]'::jsonb,
  readiness_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists ix_label_ocr_evaluation_runs_created
  on label_ocr_evaluation_runs(created_at desc);
