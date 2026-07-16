from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from schemas import Candidate, PolicyRule


class PolicyEngine:
    def __init__(self, policy_path: str = "policy.yaml"):
        self.policy_path = Path(policy_path)
        self.rules: List[PolicyRule] = []
        self._load_policy()

    def _load_policy(self):
        if self.policy_path.exists():
            with open(self.policy_path) as f:
                data = yaml.safe_load(f)
                if data:
                    for rule_def in data.get("rules", []):
                        self.rules.append(PolicyRule(**rule_def))

    def reload(self):
        self.rules.clear()
        self._load_policy()

    def check_candidate_allowed(self, candidate: Candidate) -> tuple[bool, Optional[str]]:
        for rule in self.rules:
            if not rule.enabled:
                continue
            if rule.rule_type == "block_table" and candidate.ddl_statements:
                blocked_tables = rule.config.get("tables", [])
                for ddl in candidate.ddl_statements:
                    for tbl in blocked_tables:
                        if tbl in ddl.sql:
                            return False, f"Table {tbl} is blocked by policy '{rule.name}'"
            if rule.rule_type == "max_risk" and candidate.predicted_risk:
                max_risk = rule.config.get("value", 1.0)
                if candidate.predicted_risk > max_risk:
                    return False, f"Risk {candidate.predicted_risk} exceeds max {max_risk} by policy '{rule.name}'"
        return True, None

    def check_action_allowed(self, action: str, context: dict) -> tuple[bool, Optional[str]]:
        for rule in self.rules:
            if not rule.enabled:
                continue
            if rule.rule_type == "blackout_window":
                import datetime
                now = datetime.datetime.now(datetime.timezone.utc)
                start = rule.config.get("start", "00:00")
                end = rule.config.get("end", "23:59")
                start_h, start_m = map(int, start.split(":"))
                end_h, end_m = map(int, end.split(":"))
                start_min = start_h * 60 + start_m
                end_min = end_h * 60 + end_m
                now_min = now.hour * 60 + now.minute
                if start_min <= now_min <= end_min:
                    return False, f"Blackout window active ({start}-{end}) by policy '{rule.name}'"
        return True, None
