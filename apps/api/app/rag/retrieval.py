from collections import Counter
from math import log

from app.rag.contracts import IndexedChunk, RetrievalHit
from app.rag.embeddings import EmbeddingProvider, cosine_similarity
from app.rag.text import tokenize


class HybridRetriever:
    def __init__(
        self,
        chunks: list[IndexedChunk],
        embedding_provider: EmbeddingProvider,
        *,
        rrf_k: int = 60,
        lexical_weight: float = 1.0,
        semantic_weight: float = 0.8,
    ) -> None:
        self.chunks = chunks
        self.embedding_provider = embedding_provider
        self.rrf_k = rrf_k
        self.lexical_weight = lexical_weight
        self.semantic_weight = semantic_weight
        self._tokens = [
            tokenize(
                " ".join(
                    (
                        chunk.source_title,
                        chunk.source_title,
                        chunk.source_title,
                        *chunk.heading_path,
                        *chunk.heading_path,
                        chunk.content,
                    )
                ),
                remove_stop_words=True,
            )
            for chunk in chunks
        ]
        self._document_frequency = self._build_document_frequency()
        self._average_length = sum(map(len, self._tokens)) / len(self._tokens) if self._tokens else 0.0

    def search(self, query: str, limit: int = 5) -> list[RetrievalHit]:
        if not self.chunks or limit <= 0:
            return []
        query_tokens = tokenize(query, remove_stop_words=True, expand_aliases=True)
        query_embedding = self.embedding_provider.embed([query])[0]
        lexical_scores = [self._bm25(query_tokens, index) for index in range(len(self.chunks))]
        semantic_scores = [cosine_similarity(query_embedding, chunk.embedding) for chunk in self.chunks]
        lexical_order = sorted(range(len(self.chunks)), key=lambda index: lexical_scores[index], reverse=True)
        # Semantic similarity refines grounded lexical candidates. Feature-hash
        # collisions must not introduce unrelated chunks as evidence.
        semantic_order = sorted(
            (index for index, score in enumerate(lexical_scores) if score > 0),
            key=lambda index: semantic_scores[index],
            reverse=True,
        )
        lexical_ranks = {index: rank for rank, index in enumerate(lexical_order, start=1) if lexical_scores[index] > 0}
        semantic_ranks = {
            index: rank for rank, index in enumerate(semantic_order, start=1) if semantic_scores[index] > 0
        }
        hits: list[RetrievalHit] = []
        for index, chunk in enumerate(self.chunks):
            lexical_rank = lexical_ranks.get(index)
            semantic_rank = semantic_ranks.get(index)
            if lexical_rank is None and semantic_rank is None:
                continue
            fused = 0.0
            if lexical_rank is not None:
                fused += self.lexical_weight / (self.rrf_k + lexical_rank)
            if semantic_rank is not None:
                fused += self.semantic_weight / (self.rrf_k + semantic_rank)
            hits.append(
                RetrievalHit(
                    chunk=chunk,
                    fused_score=fused,
                    lexical_score=lexical_scores[index],
                    semantic_score=semantic_scores[index],
                    lexical_rank=lexical_rank,
                    semantic_rank=semantic_rank,
                    debug={"query_tokens": query_tokens},
                )
            )
        hits.sort(key=lambda hit: (hit.fused_score, hit.lexical_score, hit.semantic_score), reverse=True)
        return hits[:limit]

    def _build_document_frequency(self) -> Counter[str]:
        frequency: Counter[str] = Counter()
        for tokens in self._tokens:
            frequency.update(set(tokens))
        return frequency

    def _bm25(self, query_tokens: list[str], document_index: int, k1: float = 1.5, b: float = 0.75) -> float:
        tokens = self._tokens[document_index]
        if not tokens or not self._average_length:
            return 0.0
        counts = Counter(tokens)
        total_documents = len(self._tokens)
        score = 0.0
        for token in set(query_tokens):
            term_frequency = counts[token]
            if not term_frequency:
                continue
            document_frequency = self._document_frequency[token]
            inverse_frequency = log(1 + (total_documents - document_frequency + 0.5) / (document_frequency + 0.5))
            denominator = term_frequency + k1 * (1 - b + b * len(tokens) / self._average_length)
            score += inverse_frequency * (term_frequency * (k1 + 1)) / denominator
        return score
