from __future__ import annotations
import asyncio
from typing import Dict, List, Optional, Type

from bus import MessageBus, Message, Topic
from schemas import (
    Candidate, CandidateStatus, ConfigSnapshot, ModificationDomain,
    WorkloadSignature,
)
from services.cvs import ConfigVersionStore
from .strategies.base import CandidateStrategy
from .strategies import (
    IndexingStrategy, StorageLayoutStrategy,
    PartitioningStrategy, CompressionStrategy, ExecutionConfigStrategy,
)


class CandidateGenerationEngine:
    def __init__(
        self,
        bus: MessageBus,
        cvs: ConfigVersionStore,
    ):
        self.bus = bus
        self.cvs = cvs
        self._running = False
        self._strategies: Dict[ModificationDomain, CandidateStrategy] = {
            ModificationDomain.indexing: IndexingStrategy(),
            ModificationDomain.storage_layout: StorageLayoutStrategy(),
            ModificationDomain.partitioning: PartitioningStrategy(),
            ModificationDomain.compression: CompressionStrategy(),
            ModificationDomain.execution_config: ExecutionConfigStrategy(),
        }

    def register_strategy(self, domain: ModificationDomain, strategy: CandidateStrategy):
        self._strategies[domain] = strategy

    async def start(self):
        self._running = True
        self.bus.subscribe(Topic.WORKLOAD_UPDATE, self._on_workload_update)
        self.bus.subscribe(Topic.WORKLOAD_ANOMALY, self._on_workload_anomaly)

    async def stop(self):
        self._running = False

    async def _on_workload_update(self, msg: Message):
        signature = WorkloadSignature(**msg.payload)
        current_state = self._get_current_state()
        rejected_ids = self.cvs.get_rejected_candidate_ids()
        candidates: List[Candidate] = []
        for strategy in self._strategies.values():
            try:
                result = strategy.generate(signature, current_state, rejected_ids)
                for c in result:
                    c.correlation_id = msg.correlation_id
                candidates.extend(result)
            except Exception as e:
                print(f"[cge] strategy error: {e}")
        candidates.sort(key=lambda c: (c.confidence_score or 0) * (c.predicted_improvement or 0), reverse=True)
        for candidate in candidates[:10]:
            candidate.correlation_id = msg.correlation_id
            self.cvs.save_candidate(candidate.model_dump(mode="json"))
            await self.bus.publish(Topic.CANDIDATE_PROPOSED, candidate.model_dump(mode="json"), msg.correlation_id)

    async def _on_workload_anomaly(self, msg: Message):
        await self._on_workload_update(msg)

    def _get_current_state(self) -> ConfigSnapshot:
        snap = self.cvs.get_latest_snapshot()
        if snap:
            return ConfigSnapshot(**snap)
        return ConfigSnapshot()
