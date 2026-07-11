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

create table if not exists product_cache (
  barcode text primary key,
  name text,
  brand text,
  categories jsonb not null default '[]'::jsonb,
  ingredients_text text,
  allergens jsonb not null default '[]'::jsonb,
  additives jsonb not null default '[]'::jsonb,
  nutriments jsonb not null default '{}'::jsonb,
  nutriscore text,
  ecoscore text,
  image_url text,
  source text not null default 'open_food_facts',
  raw_summary jsonb,
  completeness_score numeric not null default 0,
  cached_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists scan_history (
  id text primary key default gen_random_uuid()::text,
  user_id text references users(id),
  barcode text not null references product_cache(barcode),
  score integer,
  warnings jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists user_profiles (
  user_id text primary key references users(id),
  age_group text,
  goal text not null default 'general',
  allergies jsonb not null default '[]'::jsonb,
  diet text,
  disliked_ingredients jsonb not null default '[]'::jsonb,
  budget_daily numeric,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists pantry_items (
  id text primary key default gen_random_uuid()::text,
  user_id text not null references users(id),
  barcode text not null references product_cache(barcode),
  quantity numeric,
  unit text,
  expiry_date date,
  storage_location text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists meal_plans (
  id text primary key default gen_random_uuid()::text,
  user_id text references users(id),
  days integer not null,
  budget numeric,
  goal text,
  plan jsonb not null,
  created_at timestamptz not null default now()
);

create table if not exists rag_documents (
  id text primary key default gen_random_uuid()::text,
  title text not null,
  filename text not null unique,
  metadata_json jsonb not null default '{}'::jsonb,
  content text not null,
  status text not null default 'approved',
  created_at timestamptz not null default now()
);

create table if not exists admin_operation_audit (
  id text primary key default gen_random_uuid()::text,
  operation text not null,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

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
