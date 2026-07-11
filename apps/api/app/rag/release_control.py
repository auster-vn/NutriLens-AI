from dataclasses import dataclass
from time import perf_counter

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import RagRelease
from app.rag.benchmark import load_core_benchmark
from app.rag.gate import GateDecision, evaluate_release_gate
from app.rag.pipeline import _activate_release, ingest_knowledge_release


@dataclass(frozen=True)
class ReleaseOutcome:
    release: RagRelease
    gate: GateDecision | None
    timings_ms: dict[str, float]


class KnowledgeReleaseControl:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def build_draft(self, version: str | None = None) -> RagRelease:
        return await ingest_knowledge_release(self.session, version=version)

    async def evaluate(self, release_id: str) -> GateDecision:
        cases, dataset_hash = load_core_benchmark()
        return await evaluate_release_gate(
            self.session,
            release_id,
            cases,
            dataset_name="core-rag-v2",
            dataset_hash=dataset_hash,
        )

    async def publish(self, release_id: str) -> ReleaseOutcome:
        started = perf_counter()
        decision = await self.evaluate(release_id)
        gate_ms = round((perf_counter() - started) * 1000, 2)
        if not decision.passed:
            return ReleaseOutcome(await self._release(release_id), decision, {"evaluation_gate": gate_ms})
        started = perf_counter()
        release = await _activate_release(self.session, release_id)
        return ReleaseOutcome(
            release,
            decision,
            {"evaluation_gate": gate_ms, "publish": round((perf_counter() - started) * 1000, 2)},
        )

    async def build(self, *, version: str | None = None, publish: bool = True) -> ReleaseOutcome:
        release = await self.build_draft(version)
        return await self.publish(release.id) if publish else ReleaseOutcome(release, None, {})

    async def _release(self, release_id: str) -> RagRelease:
        release = await self.session.get(RagRelease, release_id)
        if release is None:
            raise ValueError("Knowledge release not found.")
        return release
