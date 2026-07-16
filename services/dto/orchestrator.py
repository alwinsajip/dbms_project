from __future__ import annotations
import asyncio
import time
import subprocess
import shutil
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4


class TwinState(str, Enum):
    IDLE = "idle"
    PROVISIONING = "provisioning"
    APPLYING = "applying"
    REPLAYING = "replaying"
    EVALUATING = "evaluating"
    DESTROYING = "destroying"


class TwinInstance:
    def __init__(
        self,
        twin_id: str,
        data_dir: str,
        port: int,
        production_dsn: str,
        template_data_dir: str,
        production_host: str = "localhost",
        production_port: int = 5542,
        production_user: str = "postgres",
        pg_bin: str = r"C:\Program Files\PostgreSQL\18\bin",
    ):
        self.twin_id = twin_id
        self.data_dir = data_dir
        self.port = port
        self.production_dsn = production_dsn
        self.template_data_dir = template_data_dir
        self.production_host = production_host
        self.production_port = production_port
        self.production_user = production_user
        self.state = TwinState.IDLE
        self.pg_bin = pg_bin
        self._proc: Optional[subprocess.Popen] = None

    async def provision(self):
        self.state = TwinState.PROVISIONING
        source = Path(self.template_data_dir)
        target = Path(self.data_dir)
        if not source.exists():
            raise RuntimeError(f"Twin template directory does not exist: {source}")
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)

        shutil.copytree(
            source,
            target,
            ignore=shutil.ignore_patterns("postmaster.pid", "postmaster.opts", "logfile"),
        )
        self._rewrite_runtime_config(target / "postgresql.conf")

        logfile = open(f"{self.data_dir}\\logfile", "a", encoding="utf-8")
        self._proc = subprocess.Popen(
            [
                f"{self.pg_bin}\\postgres.exe",
                "-D",
                self.data_dir,
                "-p",
                str(self.port),
            ],
            stdout=logfile,
            stderr=subprocess.STDOUT,
            text=True,
        )

        deadline = time.time() + 30
        while time.time() < deadline:
            ready = subprocess.run(
                [f"{self.pg_bin}\\pg_isready", "-h", "localhost", "-p", str(self.port)],
                capture_output=True, text=True, timeout=5,
            )
            if ready.returncode == 0:
                self.state = TwinState.IDLE
                return
            if self._proc.poll() is not None:
                raise RuntimeError(f"postgres twin process exited early with code {self._proc.returncode}")
            await asyncio.sleep(0.5)

        raise RuntimeError("Twin postgres process did not become ready within 30 seconds")

    def _rewrite_runtime_config(self, config_path: Path):
        text = config_path.read_text(encoding="utf-8")
        lines = text.splitlines()
        kept = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("port =") or stripped.startswith("listen_addresses ="):
                continue
            kept.append(line)
        kept.extend([
            f"port = {self.port}",
            "listen_addresses = 'localhost'",
        ])
        config_path.write_text("\n".join(kept) + "\n", encoding="utf-8")

    async def apply_ddl(self, ddl_statements: list):
        self.state = TwinState.APPLYING
        for ddl in sorted(ddl_statements, key=lambda d: d["order"]):
            result = subprocess.run(
                [f"{self.pg_bin}\\psql", "-U", "postgres", "-p", str(self.port),
                 "-d", "postgres", "-c", ddl["sql"]],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                if "already exists" not in result.stderr:
                    print(f"[dto] DDL warning on twin {self.twin_id}: {result.stderr}")
        self.state = TwinState.IDLE

    async def destroy(self):
        self.state = TwinState.DESTROYING
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._proc.kill()
                self._proc.wait(timeout=5)
        shutil.rmtree(self.data_dir, ignore_errors=True)
        self.state = TwinState.IDLE


class DigitalTwinOrchestrator:
    def __init__(self, twin_base_dir: str = "J:\\Patent\\dbms\\pgdata\\twins",
                 port_range: tuple = (5544, 5554), production_dsn: str = "",
                 template_data_dir: str = "J:\\Patent\\dbms\\pgdata\\twin",
                 production_host: str = "localhost", production_port: int = 5542,
                 production_user: str = "postgres", pg_bin: str = r"C:\Program Files\PostgreSQL\18\bin"):
        self.twin_base_dir = Path(twin_base_dir)
        self.twin_base_dir.mkdir(parents=True, exist_ok=True)
        self.port_range = port_range
        self.production_dsn = production_dsn
        self.template_data_dir = template_data_dir
        self.production_host = production_host
        self.production_port = production_port
        self.production_user = production_user
        self.pg_bin = pg_bin
        self._next_port = port_range[0]
        self._active_twins: Dict[str, TwinInstance] = {}

    async def provision_twin(self, candidate: dict) -> TwinInstance:
        twin_id = str(uuid4())[:8]
        port = self._next_port
        self._next_port += 1
        if self._next_port > self.port_range[1]:
            self._next_port = self.port_range[0]

        data_dir = str(self.twin_base_dir / twin_id)
        twin = TwinInstance(
            twin_id, data_dir, port, self.production_dsn,
            template_data_dir=self.template_data_dir,
            production_host=self.production_host,
            production_port=self.production_port,
            production_user=self.production_user,
            pg_bin=self.pg_bin,
        )
        await twin.provision()
        self._active_twins[twin_id] = twin
        return twin

    async def apply_to_twin(self, twin: TwinInstance, candidate: dict):
        ddl_statements = candidate.get("ddl_statements", [])
        await twin.apply_ddl(ddl_statements)

    async def destroy_twin(self, twin: TwinInstance):
        await twin.destroy()
        self._active_twins.pop(twin.twin_id, None)

    async def destroy_all(self):
        for twin_id, twin in list(self._active_twins.items()):
            await twin.destroy()
        self._active_twins.clear()
