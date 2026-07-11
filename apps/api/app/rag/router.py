from hashlib import sha256
from time import perf_counter

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import get_optional_user
from app.core.database import get_session
from app.core.models import RagAnswerAudit, User
from app.rag.runtime import answer_with_retrieval, retrieve
from app.schemas.rag import ChatRequest, ChatResponse, Citation, RagSearchOut, RagSearchRequest

router = APIRouter(tags=["rag"])


@router.post("/api/rag/search", response_model=RagSearchOut)
async def rag_search(
    request: RagSearchRequest,
    session: AsyncSession = Depends(get_session),
) -> RagSearchOut:
    context = await retrieve(session, request.question, request.limit)
    return RagSearchOut(
        query=request.question,
        results=[
            Citation(
                source=hit.chunk.source_filename,
                title=hit.chunk.source_title,
                source_url=hit.chunk.source_url,
                snippet=hit.chunk.content[:420],
                chunk_id=hit.chunk.id,
                heading_path=list(hit.chunk.heading_path),
                lexical_score=round(hit.lexical_score, 6),
                semantic_score=round(hit.semantic_score, 6),
                fused_score=round(hit.fused_score, 8),
            )
            for hit in context.hits
        ],
    )


@router.post("/api/chat/stream", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user: User | None = Depends(get_optional_user),
    session: AsyncSession = Depends(get_session),
) -> ChatResponse:
    started_at = perf_counter()
    answer = await answer_with_retrieval(session, request.question, request.barcode)
    session.add(
        RagAnswerAudit(
            user_id=user.id if user else None,
            question_hash=sha256(request.question.strip().lower().encode()).hexdigest(),
            route=answer.route,
            abstained=answer.abstained,
            citation_count=len(answer.citations),
            latency_ms=round((perf_counter() - started_at) * 1000),
        )
    )
    await session.commit()
    return answer
