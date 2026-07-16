import asyncio
import pytest
from bus import MessageBus, Topic
from schemas import Candidate, CandidateStatus, DDLStatement, ModificationDomain
from services.cvs import ConfigVersionStore


class FakeTwin:
    def __init__(self, twin_id):
        self.twin_id = twin_id
    async def provision(self):
        pass
    async def apply_ddl(self, ddl):
        pass
    async def destroy(self):
        pass


class FakeDTO:
    def __init__(self):
        self._count = 0
    async def provision_twin(self, candidate):
        self._count += 1
        return FakeTwin(f"twin-{self._count}")
    async def apply_to_twin(self, twin, candidate):
        pass
    async def destroy_twin(self, twin):
        pass


@pytest.mark.asyncio
async def test_scenario_e():
    bus = MessageBus()
    await bus.start("test")
    cvs = ConfigVersionStore(":memory:")
    cvs.connect()
    dto = FakeDTO()
    from services.vce import ValidationCorrectnessEngine
    vce = ValidationCorrectnessEngine(bus, cvs, dto)
    await vce.start()

    bad_candidate = Candidate(
        title="Bad constraint",
        description="Intentionally bad",
        domain=ModificationDomain.storage_layout,
        ddl_statements=[DDLStatement(
            sql="ALTER TABLE orders ADD CONSTRAINT bad_check CHECK (quantity > 0);",
            rollback_sql="ALTER TABLE orders DROP CONSTRAINT IF EXISTS bad_check;",
            order=0,
        )],
        correlation_id="scenario-e",
        status=CandidateStatus.proposed,
    )
    cvs.save_candidate(bad_candidate.model_dump(mode="json"))

    reports = []
    async def on_validation(msg):
        reports.append(msg.payload)
    bus.subscribe(Topic.VALIDATION_COMPLETE, on_validation)

    await bus.publish(Topic.CANDIDATE_PROPOSED, bad_candidate.model_dump(mode="json"), "scenario-e")
    await asyncio.sleep(1.0)

    assert len(reports) > 0, "No validation report"
    assert not reports[0]["passed"], "Bad candidate should fail validation"
    deployments = cvs.get_deployment_events(bad_candidate.id)
    assert len(deployments) == 0, "Bad candidate must not be deployed"
    await bus.stop()
