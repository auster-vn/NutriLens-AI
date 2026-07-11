from typing import Protocol

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.rag.contracts import IndexedChunk
from app.rag.pipeline import indexed_chunks
from app.rag.text import tokenize

PGVECTOR_CANDIDATE_SQL = """
with lexical as (
  select id,
         row_number() over (
           order by ts_rank_cd(
             to_tsvector('simple', source_title || ' ' || content), websearch_to_tsquery('simple', :query_text)
           ) desc
         ) as lexical_rank
  from rag_chunks
  where release_id = :release_id
    and to_tsvector('simple', source_title || ' ' || content) @@ websearch_to_tsquery('simple', :query_text)
  order by ts_rank_cd(
    to_tsvector('simple', source_title || ' ' || content), websearch_to_tsquery('simple', :query_text)
  ) desc
  limit :candidate_limit
), semantic as (
  select id,
         row_number() over (order by embedding_vector <=> cast(:query_vector as vector)) as semantic_rank
  from rag_chunks
  where release_id = :release_id and embedding_vector is not null
  order by embedding_vector <=> cast(:query_vector as vector)
  limit :candidate_limit
), candidates as (
  select id from lexical union select id from semantic
)
select c.id, c.source_filename, c.source_title, c.source_url, c.content,
       c.heading_path, c.metadata_json, c.embedding, c.embedding_model
from rag_chunks c
join candidates candidate on candidate.id = c.id
left join lexical on lexical.id = c.id
left join semantic on semantic.id = c.id
order by coalesce(lexical.lexical_rank, 2147483647), coalesce(semantic.semantic_rank, 2147483647)
"""


class CandidateStore(Protocol):
    backend_name: str

    async def load_candidates(
        self,
        session: AsyncSession,
        *,
        release_id: str,
        query: str,
        query_embedding: list[float],
        limit: int,
    ) -> list[IndexedChunk]: ...


class SqlAlchemyCandidateStore:
    backend_name = "sqlalchemy_json"

    async def load_candidates(
        self,
        session: AsyncSession,
        *,
        release_id: str,
        query: str,
        query_embedding: list[float],
        limit: int,
    ) -> list[IndexedChunk]:
        del query, query_embedding, limit
        return await indexed_chunks(session, release_id)


class PgvectorCandidateStore:
    backend_name = "postgres_pgvector"

    async def load_candidates(
        self,
        session: AsyncSession,
        *,
        release_id: str,
        query: str,
        query_embedding: list[float],
        limit: int,
    ) -> list[IndexedChunk]:
        query_terms = tokenize(query, remove_stop_words=True, expand_aliases=True)
        result = await session.execute(
            text(PGVECTOR_CANDIDATE_SQL),
            {
                "release_id": release_id,
                "query_text": " OR ".join(query_terms) or query,
                "query_vector": "[" + ",".join(f"{value:.12g}" for value in query_embedding) + "]",
                "candidate_limit": limit,
            },
        )
        return [_row_to_chunk(row) for row in result.mappings().all()]


def create_candidate_store(backend: str, database_url: str, dimensions: int) -> CandidateStore:
    normalized = backend.strip().lower()
    use_pgvector = normalized == "pgvector" or (normalized == "auto" and database_url.startswith("postgresql"))
    if use_pgvector:
        if dimensions != 256:
            raise ValueError("The pgvector schema currently requires NUTRILENS_RAG_EMBEDDING_DIMENSIONS=256.")
        return PgvectorCandidateStore()
    if normalized not in {"auto", "sqlalchemy_json"}:
        raise ValueError(f"Unsupported RAG retrieval backend: {backend}")
    return SqlAlchemyCandidateStore()


def _row_to_chunk(row) -> IndexedChunk:
    return IndexedChunk(
        id=row["id"],
        source_filename=row["source_filename"],
        source_title=row["source_title"],
        source_url=row["source_url"],
        content=row["content"],
        heading_path=tuple(row["heading_path"] or []),
        metadata=row["metadata_json"] or {},
        embedding=tuple(float(value) for value in (row["embedding"] or [])),
        embedding_model=row["embedding_model"],
    )
