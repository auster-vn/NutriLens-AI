-- Compatibility migration for databases created before Identity existed.
create extension if not exists pgcrypto;

create table if not exists users (
  id text primary key default gen_random_uuid()::text,
  email text not null unique,
  display_name text not null,
  password_hash text not null,
  role text not null default 'user',
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table user_profiles add column if not exists age_group text;

create table if not exists product_favorites (
  id text primary key default gen_random_uuid()::text,
  user_id text not null references users(id),
  barcode text not null references product_cache(barcode),
  created_at timestamptz not null default now(),
  constraint uq_product_favorites_user_barcode unique (user_id, barcode)
);

create table if not exists rag_answer_audit (
  id text primary key default gen_random_uuid()::text,
  user_id text references users(id),
  question_hash text not null,
  route text not null,
  abstained boolean not null,
  citation_count integer not null,
  latency_ms integer not null,
  created_at timestamptz not null default now()
);

create index if not exists ix_product_favorites_user_created
  on product_favorites(user_id, created_at desc);
create index if not exists ix_rag_answer_audit_user_created
  on rag_answer_audit(user_id, created_at desc);
