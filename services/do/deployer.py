from __future__ import annotations
import asyncio
import subprocess
from datetime import datetime
from typing import Optional

from bus import MessageBus, Topic, Message
from schemas import (
    Candidate, CandidateStatus, ConfigSnapshot, DeploymentEvent,
    DeploymentStrategy, DDLStatement,
)
from services.cvs import ConfigVersionStore


class DeploymentOrchestrator:
    def __init__(
        self,
        bus: MessageBus,
        cvs: ConfigVersionStore,
        pg_dsn: str = "postgresql://postgres@localhost:5542/sedbms_prod",
        pg_bin: str = r"C:\Program Files\PostgreSQL\18\bin",
    ):
        self.bus = bus
        self.cvs = cvs
        self.pg_dsn = pg_dsn
        self.pg_bin = pg_bin
        self._running = False

    async def start(self):
        self._running = True
        self.bus.subscribe(Topic.VALIDATION_COMPLETE, self._on_validation)

    async def stop(self):
        self._running = False

    async def _on_validation(self, msg: Message):
        report = msg.payload
        if not report.get("passed"):
            return
        candidate = self.cvs.get_candidate(report["candidate_id"])
        if not candidate:
            return

        asyncio.create_task(self._deploy(candidate, report))

    async def _deploy(self, candidate: dict, report: dict):
        correlation_id = candidate["correlation_id"]
        port = self._dsn_port()
        database = self._dsn_db()
        pre_snapshot = self._capture_snapshot(correlation_id)
        pre_snapshot_id = self.cvs.save_snapshot(pre_snapshot.model_dump(mode="json"))

        event = DeploymentEvent(
            candidate_id=candidate["id"],
            correlation_id=correlation_id,
            strategy=DeploymentStrategy.blue_green,
            status="starting",
            pre_deploy_snapshot_id=pre_snapshot_id,
        )
        self.cvs.save_deployment_event(event.model_dump(mode="json"))
        await self.bus.publish(Topic.DEPLOYMENT_STARTED, event.model_dump(mode="json"), correlation_id)

        try:
            for ddl_stmt in candidate.get("ddl_statements", []):
                sql = ddl_stmt["sql"]
                result = subprocess.run(
                    [f"{self.pg_bin}\\psql", "-U", "postgres", "-h", "localhost", "-p", str(port),
                     "-d", database, "-c", sql],
                    capture_output=True, text=True, timeout=30,
                )
                if result.returncode != 0 and "already exists" not in result.stderr:
                    raise RuntimeError(f"DDL failed: {result.stderr}")

            await asyncio.sleep(2)
            health_ok = await self._health_check(port)

            post_snapshot = self._capture_snapshot(correlation_id)
            post_snapshot_id = self.cvs.save_snapshot(post_snapshot.model_dump(mode="json"))

            event = DeploymentEvent(
                candidate_id=candidate["id"],
                correlation_id=correlation_id,
                strategy=DeploymentStrategy.blue_green,
                status="completed" if health_ok else "failed",
                health_check_passed=health_ok,
                pre_deploy_snapshot_id=pre_snapshot_id,
                post_deploy_snapshot_id=post_snapshot_id,
            )
            self.cvs.save_deployment_event(event.model_dump(mode="json"))
            topic = Topic.DEPLOYMENT_COMPLETED if health_ok else Topic.DEPLOYMENT_FAILED
            await self.bus.publish(topic, event.model_dump(mode="json"), correlation_id)

        except Exception as e:
            event = DeploymentEvent(
                candidate_id=candidate["id"],
                correlation_id=correlation_id,
                strategy=DeploymentStrategy.blue_green,
                status="failed",
                error=str(e),
                pre_deploy_snapshot_id=pre_snapshot_id,
            )
            self.cvs.save_deployment_event(event.model_dump(mode="json"))
            await self.bus.publish(Topic.DEPLOYMENT_FAILED, event.model_dump(mode="json"), correlation_id)

    async def _health_check(self, port: int) -> bool:
        try:
            result = subprocess.run(
                [f"{self.pg_bin}\\pg_isready", "-h", "localhost", "-p", str(port)],
                capture_output=True, text=True, timeout=10,
            )
            return result.returncode == 0
        except Exception:
            return False

    def _dsn_port(self) -> int:
        try:
            return int(self.pg_dsn.rsplit(":", 1)[1].split("/", 1)[0])
        except Exception:
            return 5542

    def _dsn_db(self) -> str:
        try:
            return self.pg_dsn.rsplit("/", 1)[1]
        except Exception:
            return "sedbms_prod"

    def _capture_snapshot(self, correlation_id: str) -> ConfigSnapshot:
        return ConfigSnapshot(correlation_id=correlation_id)
