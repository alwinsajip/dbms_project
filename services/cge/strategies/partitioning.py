from __future__ import annotations
from typing import List

from schemas import (
    Candidate, CandidateStatus, DDLStatement, ModificationDomain,
    WorkloadSignature, ConfigSnapshot,
)
from .base import CandidateStrategy


class PartitioningStrategy(CandidateStrategy):
    def generate(
        self,
        signature: WorkloadSignature,
        current_state: ConfigSnapshot,
        rejected_ids: List[str],
    ) -> List[Candidate]:
        candidates: List[Candidate] = []
        if not signature.hot_keys:
            return candidates
        for table, size in signature.table_sizes.items():
            if size < 100 * 1024 * 1024:
                continue
            skew = signature.hot_keys.get(table, 0)
            if skew > 1000:
                candidates.append(Candidate(
                    domain=ModificationDomain.partitioning,
                    title=f"Repartition {table} by range",
                    description=f"Table {table} has {skew} hot keys — range partitioning suggested",
                    ddl_statements=[
                        DDLStatement(
                            sql=f"-- TODO: ALTER TABLE {table} ATTACH PARTITION",
                            rollback_sql=f"-- TODO: DETACH PARTITION",
                            order=0,
                        )
                    ],
                    predicted_improvement=30.0,
                    predicted_risk=0.3,
                    confidence_score=0.5,
                    correlation_id="",
                ))
        return candidates
