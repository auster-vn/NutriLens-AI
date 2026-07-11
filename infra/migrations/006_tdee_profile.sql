alter table user_profiles add column if not exists biological_sex varchar(16);
alter table user_profiles add column if not exists age integer;
alter table user_profiles add column if not exists height_cm double precision;
alter table user_profiles add column if not exists weight_kg double precision;
alter table user_profiles add column if not exists activity_level varchar(32);
alter table user_profiles add column if not exists target_weight_loss_kg_week double precision;
