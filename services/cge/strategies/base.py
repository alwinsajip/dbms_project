from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List

from schemas import Candidate, WorkloadSignature, ConfigSnapshot


class CandidateStrategy(ABC):
    @abstractmethod
    def generate(
        self,
        signature: WorkloadSignature,
        current_state: ConfigSnapshot,
        rejected_ids: List[str],
    ) -> List[Candidate]:
        ...
