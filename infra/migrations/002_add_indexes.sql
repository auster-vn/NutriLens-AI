create index if not exists ix_scan_history_user_created
  on scan_history(user_id, created_at desc);

create index if not exists ix_scan_history_barcode_created
  on scan_history(barcode, created_at desc);

create index if not exists ix_pantry_items_user_expiry
  on pantry_items(user_id, expiry_date);

create index if not exists ix_pantry_items_barcode
  on pantry_items(barcode);

create index if not exists ix_meal_plans_user_created
  on meal_plans(user_id, created_at desc);

create index if not exists ix_rag_documents_status
  on rag_documents(status);

create index if not exists ix_product_favorites_user_created
  on product_favorites(user_id, created_at desc);

create index if not exists ix_rag_answer_audit_user_created
  on rag_answer_audit(user_id, created_at desc);
