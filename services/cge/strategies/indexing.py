from __future__ import annotations
from typing import List

from schemas import (
    Candidate, CandidateStatus, DDLStatement, ModificationDomain,
    WorkloadSignature, ConfigSnapshot,
)
from .base import CandidateStrategy


class IndexingStrategy(CandidateStrategy):
    def generate(
        self,
        signature: WorkloadSignature,
        current_state: ConfigSnapshot,
        rejected_ids: List[str],
    ) -> List[Candidate]:
        candidates: List[Candidate] = []
        seen_tables = set()

        for shape in signature.query_shapes:
            if shape.frequency < 5:
                continue
            for table in shape.tables_accessed:
                if table in seen_tables:
                    continue
                seen_tables.add(table)
                predicates = [p for p in shape.predicates if p.strip()]
                if not predicates:
                    continue

                cols = [p.split()[0] if " " in p else p for p in predicates[:3]]
                col_list = ", ".join(cols)
                idx_name = f"idx_auto_{table.replace('.', '_')}_{'_'.join(cols)}"
                idx_name = idx_name[:63]

                if idx_name in current_state.index_definitions:
                    continue

                create_sql = f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} ({col_list});"
                drop_sql = f"DROP INDEX IF EXISTS {idx_name};"

                predicted = shape.p95_latency_ms * 0.4

                ddl = DDLStatement(sql=create_sql, rollback_sql=drop_sql, order=0)
                candidates.append(Candidate(
                    domain=ModificationDomain.indexing,
                    title=f"Index {idx_name} on {table}",
                    description=f"B-tree index on ({col_list}) for filter pattern: {shape.query_fingerprint[:80]}",
                    ddl_statements=[ddl],
                    predicted_improvement=predicted,
                    predicted_risk=0.1,
                    confidence_score=shape.frequency / max(s.frequency for s in signature.query_shapes) if signature.query_shapes else 0.5,
                    correlation_id="",
                    status=CandidateStatus.proposed,
                ))
        return candidates
