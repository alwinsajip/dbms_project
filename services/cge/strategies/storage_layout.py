from __future__ import annotations
from typing import List

from schemas import (
    Candidate, CandidateStatus, DDLStatement, ModificationDomain,
    WorkloadSignature, ConfigSnapshot,
)
from .base import CandidateStrategy


class StorageLayoutStrategy(CandidateStrategy):
    def generate(
        self,
        signature: WorkloadSignature,
        current_state: ConfigSnapshot,
        rejected_ids: List[str],
    ) -> List[Candidate]:
        candidates: List[Candidate] = []
        for table, size in signature.table_sizes.items():
            if size < 10 * 1024 * 1024:
                continue
            table_freq = sum(
                s.frequency for s in signature.query_shapes
                if table in s.tables_accessed
            )
            write_heavy = False
            for s in signature.query_shapes:
                if table in s.tables_accessed and "INSERT" in s.query_fingerprint:
                    write_heavy = True
                    break

            if write_heavy and table_freq > 100:
                ddl = DDLStatement(
                    sql=f"ALTER TABLE {table} SET (fillfactor = 70);",
                    rollback_sql=f"ALTER TABLE {table} SET (fillfactor = 100);",
                    order=0,
                )
                candidates.append(Candidate(
                    domain=ModificationDomain.storage_layout,
                    title=f"Adjust fillfactor on {table}",
                    description=f"Write-heavy table {table} with {table_freq} ops — lower fillfactor to reduce page splits",
                    ddl_statements=[ddl],
                    predicted_improvement=15.0,
                    predicted_risk=0.05,
                    confidence_score=0.7,
                    correlation_id="",
                ))
        return candidates
