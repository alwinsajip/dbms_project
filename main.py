from __future__ import annotations
import asyncio
import signal
import sys
from typing import List

import uvicorn

from bus import MessageBus
from services.cvs import ConfigVersionStore
from services.twm import TelemetryWorkloadMonitor
from services.cge import CandidateGenerationEngine
from services.dto import DigitalTwinOrchestrator
from services.vce import ValidationCorrectnessEngine
from services.do import DeploymentOrchestrator
from services.rrc import RollbackRegressionController
from services.policy import PolicyEngine
from services.api import create_app
from services.settings import get_settings


class SEDBMSOrchestrator:
    def __init__(self):
        self.components = []
        self._running = False

    async def startup(self):
        print("[sedbms] Initializing services...")
        settings = get_settings()

        cvs = ConfigVersionStore(settings.cvs_path)
        cvs.connect()
        self.components.append(cvs)

        bus = MessageBus.get_instance()
        await bus.start("sedbms")
        self.components.append(bus)

        policy = PolicyEngine(settings.policy_path)
        self.components.append(policy)

        twm = TelemetryWorkloadMonitor(bus, pg_dsn=settings.prod_dsn)
        await twm.start()
        self.components.append(twm)

        dto = DigitalTwinOrchestrator(
            production_dsn=settings.prod_dsn,
            production_host=settings.prod_host,
            production_port=settings.prod_port,
            production_user=settings.prod_user,
            pg_bin=settings.pg_bin,
        )
        self.components.append(dto)

        cge = CandidateGenerationEngine(bus, cvs)
        await cge.start()
        self.components.append(cge)

        vce = ValidationCorrectnessEngine(bus, cvs, dto)
        await vce.start()
        self.components.append(vce)

        do_service = DeploymentOrchestrator(bus, cvs, pg_dsn=settings.prod_dsn, pg_bin=settings.pg_bin)
        await do_service.start()
        self.components.append(do_service)

        rrc = RollbackRegressionController(
            bus, cvs, pg_bin=settings.pg_bin, pg_port=settings.prod_port, pg_db=settings.prod_db
        )
        await rrc.start()
        self.components.append(rrc)

        app = create_app(cvs, bus)
        config = uvicorn.Config(app, host=settings.api_host, port=settings.api_port, log_level="info")
        server = uvicorn.Server(config)
        self.components.append(server)

        print(f"[sedbms] All services started. API at http://{settings.api_host}:{settings.api_port}")
        self._running = True
        await server.serve()

    async def shutdown(self):
        print("[sedbms] Shutting down...")
        for comp in reversed(self.components):
            try:
                if hasattr(comp, "stop"):
                    await comp.stop()
                elif hasattr(comp, "close"):
                    comp.close()
            except Exception as e:
                print(f"[sedbms] shutdown error: {e}")
        self._running = False
        print("[sedbms] Shutdown complete.")


async def main():
    orch = SEDBMSOrchestrator()
    try:
        await orch.startup()
    except KeyboardInterrupt:
        await orch.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
