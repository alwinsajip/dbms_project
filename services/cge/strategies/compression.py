from __future__ import annotations
from typing import List

from schemas import (
    Candidate, CandidateStatus, DDLStatement, ModificationDomain,
    WorkloadSignature, ConfigSnapshot,
)
from .base import CandidateStrategy


class CompressionStrategy(CandidateStrategy):
    def generate(
        self,
        signature: WorkloadSignature,
        current_state: ConfigSnapshot,
        rejected_ids: List[str],
    ) -> List[Candidate]:
        candidates: List[Candidate] = []
        hot_tables = set()
        for s in signature.query_shapes:
            if s.frequency > 10:
                for t in s.tables_accessed:
                    hot_tables.add(t)

        for table, size in signature.table_sizes.items():
            freq = sum(
                s.frequency for s in signature.query_shapes
                if table in s.tables_accessed
            )
            if table in hot_tables:
                continue
            if size > 50 * 1024 * 1024 and freq < 5:
                candidates.append(Candidate(
                    domain=ModificationDomain.compression,
                    title=f"Enable pglz compression on {table}",
                    description=f"Cold table ({freq} queries, {size} bytes) — enable TOAST compression",
                    ddl_statements=[
                        DDLStatement(
                            sql=f"ALTER TABLE {table} SET (toast_tuple_target = 2048);",
                            rollback_sql=f"ALTER TABLE {table} RESET (toast_tuple_target);",
                            order=0,
                        )
                    ],
                    predicted_improvement=float(size // (1024 * 1024)),
                    predicted_risk=0.05,
                    confidence_score=0.6,
                    correlation_id="",
                ))
        return candidates
