from __future__ import annotations
from typing import List

from schemas import (
    Candidate, CandidateStatus, ConfigDelta, ModificationDomain,
    WorkloadSignature, ConfigSnapshot,
)
from .base import CandidateStrategy


class ExecutionConfigStrategy(CandidateStrategy):
    CONFIG_RECOMMENDATIONS = [
        {
            "param": "work_mem",
            "condition": lambda sig, _: sig.resource_metrics.memory_percent < 70,
            "value": "64MB",
            "improvement": 5.0,
        },
        {
            "param": "max_parallel_workers_per_gather",
            "condition": lambda sig, _: any(
                s.join_count > 1 for s in sig.query_shapes
            ),
            "value": "4",
            "improvement": 20.0,
        },
        {
            "param": "effective_cache_size",
            "condition": lambda sig, _: sig.resource_metrics.memory_percent < 60,
            "value": "4GB",
            "improvement": 8.0,
        },
    ]

    def generate(
        self,
        signature: WorkloadSignature,
        current_state: ConfigSnapshot,
        rejected_ids: List[str],
    ) -> List[Candidate]:
        candidates: List[Candidate] = []
        for rec in self.CONFIG_RECOMMENDATIONS:
            if not rec["condition"](signature, current_state):
                continue
            old_val = current_state.execution_config.get(rec["param"], "default")
            candidates.append(Candidate(
                domain=ModificationDomain.execution_config,
                title=f"Set {rec['param']} to {rec['value']}",
                description=f"Adjust {rec['param']} based on workload pattern",
                config_deltas=[
                    ConfigDelta(
                        parameter=rec["param"],
                        old_value=old_val,
                        new_value=rec["value"],
                    )
                ],
                predicted_improvement=rec["improvement"],
                predicted_risk=0.1,
                confidence_score=0.5,
                correlation_id="",
            ))
        return candidates
