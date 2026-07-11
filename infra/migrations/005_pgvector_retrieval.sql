create extension if not exists vector;

alter table rag_chunks
  add column if not exists embedding_vector vector(256);

create or replace function sync_rag_chunk_embedding_vector()
returns trigger
language plpgsql
as $$
begin
  new.embedding_vector := case
    when new.embedding is null or jsonb_array_length(new.embedding::jsonb) = 0 then null
    else new.embedding::text::vector
  end;
  return new;
end;
$$;

drop trigger if exists trg_rag_chunk_embedding_vector on rag_chunks;
create trigger trg_rag_chunk_embedding_vector
before insert or update of embedding on rag_chunks
for each row execute function sync_rag_chunk_embedding_vector();

update rag_chunks
set embedding_vector = embedding::text::vector
where jsonb_array_length(embedding::jsonb) = 256 and embedding_vector is null;

create index if not exists ix_rag_chunks_embedding_hnsw
  on rag_chunks using hnsw (embedding_vector vector_cosine_ops);

create index if not exists ix_rag_chunks_content_fts
  on rag_chunks using gin (to_tsvector('simple', source_title || ' ' || content));
