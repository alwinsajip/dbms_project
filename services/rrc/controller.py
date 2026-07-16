from __future__ import annotations
import asyncio
import subprocess
from typing import Dict, Optional

from bus import MessageBus, Topic, Message
from schemas import RollbackEvent
from services.cvs import ConfigVersionStore


class RollbackRegressionController:
    def __init__(
        self,
        bus: MessageBus,
        cvs: ConfigVersionStore,
        pg_bin: str = r"C:\Program Files\PostgreSQL\18\bin",
        pg_port: int = 5542,
        pg_db: str = "sedbms_prod",
        regression_p95_threshold: float = 1.5,
        regression_error_threshold: int = 5,
    ):
        self.bus = bus
        self.cvs = cvs
        self.pg_bin = pg_bin
        self.pg_port = pg_port
        self.pg_db = pg_db
        self.regression_p95_threshold = regression_p95_threshold
        self.regression_error_threshold = regression_error_threshold
        self._running = False
        self._deployed_candidates: Dict[str, dict] = {}
        self._baselines: Dict[str, dict] = {}

    async def start(self):
        self._running = True
        self.bus.subscribe(Topic.DEPLOYMENT_COMPLETED, self._on_deployed)
        self.bus.subscribe(Topic.WORKLOAD_UPDATE, self._on_workload)

    async def stop(self):
        self._running = False

    async def _on_deployed(self, msg: Message):
        event = msg.payload
        if event.get("status") == "completed":
            candidate = self.cvs.get_candidate(event["candidate_id"])
            if candidate:
                self._deployed_candidates[candidate["id"]] = candidate
                self._baselines[candidate["id"]] = {
                    "p95": 0,
                    "errors": 0,
                }

    async def _on_workload(self, msg: Message):
        for cand_id, candidate in list(self._deployed_candidates.items()):
            asyncio.create_task(self._check_regression(cand_id, msg.payload))

    async def _check_regression(self, candidate_id: str, workload: dict):
        baseline = self._baselines.get(candidate_id)
        if not baseline:
            return

        query_shapes = workload.get("query_shapes", [])
        current_p95 = max((s.get("p95_latency_ms", 0) for s in query_shapes), default=0)
        current_errors = workload.get("connection_count", 0)

        if baseline["p95"] == 0:
            baseline["p95"] = current_p95 or 0.001
            return

        p95_ratio = current_p95 / baseline["p95"] if baseline["p95"] > 0 else 1.0
        if p95_ratio > self.regression_p95_threshold or current_errors > self.regression_error_threshold:
            await self._rollback(candidate_id, f"p95_ratio={p95_ratio:.2f}, errors={current_errors}")

    async def _rollback(self, candidate_id: str, reason: str):
        candidate = self._deployed_candidates.pop(candidate_id, None)
        if not candidate:
            return

        event = RollbackEvent(
            candidate_id=candidate_id,
            correlation_id=candidate.get("correlation_id", ""),
            trigger_reason=reason,
        )
        self.cvs.save_rollback_event(event.model_dump(mode="json"))
        await self.bus.publish(Topic.ROLLBACK_TRIGGERED, event.model_dump(mode="json"), candidate["correlation_id"])

        try:
            ddl_statements = candidate.get("ddl_statements", [])
            for ddl_stmt in reversed(sorted(ddl_statements, key=lambda d: d["order"])):
                rollback_sql = ddl_stmt["rollback_sql"]
                result = subprocess.run(
                    [f"{self.pg_bin}\\psql", "-U", "postgres", "-h", "localhost", "-p", str(self.pg_port),
                     "-d", self.pg_db, "-c", rollback_sql],
                    capture_output=True, text=True, timeout=30,
                )
                if result.returncode != 0 and "does not exist" not in result.stderr:
                    print(f"[rrc] rollback warning: {result.stderr}")

            await asyncio.sleep(2)
            rollback_ok = True
        except Exception as e:
            rollback_ok = False
            print(f"[rrc] rollback error: {e}")

        event = RollbackEvent(
            candidate_id=candidate_id,
            correlation_id=candidate.get("correlation_id", ""),
            trigger_reason=reason,
            duration_seconds=5.0,
            success=rollback_ok,
        )
        self.cvs.save_rollback_event(event.model_dump(mode="json"))
        await self.bus.publish(Topic.ROLLBACK_COMPLETED, event.model_dump(mode="json"), candidate["correlation_id"])
