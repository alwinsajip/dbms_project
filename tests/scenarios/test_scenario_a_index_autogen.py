import asyncio
import sys
import pytest
from bus import MessageBus, Topic
from schemas import WorkloadSignature, ResourceMetrics, QueryShape, Candidate
from services.cvs import ConfigVersionStore
from services.cge import CandidateGenerationEngine
from services.vce import ValidationCorrectnessEngine


class FakeTwin:
    def __init__(self, twin_id):
        self.twin_id = twin_id
        self.state = "idle"
    async def provision(self):
        self.state = "provisioning"
    async def apply_ddl(self, ddl):
        self.state = "applying"
    async def destroy(self):
        self.state = "destroying"


class FakeDTO:
    def __init__(self):
        self._active = {}
        self._count = 0
    async def provision_twin(self, candidate):
        self._count += 1
        t = FakeTwin(f"twin-{self._count}")
        self._active[t.twin_id] = t
        return t
    async def apply_to_twin(self, twin, candidate):
        await twin.apply_ddl(candidate.get("ddl_statements", []))
    async def destroy_twin(self, twin):
        await twin.destroy()
        self._active.pop(twin.twin_id, None)


@pytest.mark.asyncio
async def test_scenario_a():
    bus = MessageBus()
    await bus.start("test")
    cvs = ConfigVersionStore(":memory:")
    cvs.connect()
    dto = FakeDTO()

    cge = CandidateGenerationEngine(bus, cvs)
    vce = ValidationCorrectnessEngine(bus, cvs, dto)
    await cge.start()
    await vce.start()

    candidates = []
    reports = []

    async def on_candidate(msg):
        candidates.append(Candidate(**msg.payload))
    async def on_validation(msg):
        reports.append(msg.payload)

    bus.subscribe(Topic.CANDIDATE_PROPOSED, on_candidate)
    bus.subscribe(Topic.VALIDATION_COMPLETE, on_validation)

    sig = WorkloadSignature(
        query_shapes=[QueryShape(
            query_fingerprint="SELECT * FROM orders WHERE region = $1",
            frequency=500.0, avg_latency_ms=450.0, p50_latency_ms=420.0,
            p95_latency_ms=1200.0, p99_latency_ms=2000.0,
            tables_accessed=["public.orders"], predicates=["region"],
            join_count=0, read_write_ratio=0.9,
        )],
        resource_metrics=ResourceMetrics(cpu_percent=45.0, memory_percent=60.0, disk_read_bytes=0, disk_write_bytes=0, net_bytes_sent=0, net_bytes_recv=0),
        table_sizes={"public.orders": 500 * 1024 * 1024},
        index_usage={"public.orders_pkey": 100.0},
        hot_keys={"public.orders": 50000},
        read_write_ratio=0.8,
        connection_count=10,
    )
    await bus.publish(Topic.WORKLOAD_ANOMALY, sig.model_dump(mode="json"), "scenario-a")
    await asyncio.sleep(2.0)

    assert len(candidates) > 0, "No candidates generated"
    index_candidates = [c for c in candidates if c.domain.value == "indexing"]
    assert len(index_candidates) > 0, "No index candidates"
    assert any("orders" in d.sql for c in index_candidates for d in c.ddl_statements)
    assert len(reports) > 0, "No validation reports"
    assert reports[0]["passed"], f"Validation failed: {reports[0].get('details')}"

    await bus.stop()
