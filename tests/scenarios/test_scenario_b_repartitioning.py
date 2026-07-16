import asyncio
import pytest
from bus import MessageBus, Topic
from schemas import WorkloadSignature, ResourceMetrics, QueryShape, Candidate
from services.cvs import ConfigVersionStore
from services.cge import CandidateGenerationEngine


@pytest.mark.asyncio
async def test_scenario_b():
    bus = MessageBus()
    await bus.start("test")
    cvs = ConfigVersionStore(":memory:")
    cvs.connect()
    cge = CandidateGenerationEngine(bus, cvs)
    await cge.start()

    candidates = []
    async def on_candidate(msg):
        candidates.append(Candidate(**msg.payload))
    bus.subscribe(Topic.CANDIDATE_PROPOSED, on_candidate)

    sig = WorkloadSignature(
        query_shapes=[QueryShape(
            query_fingerprint="SELECT * FROM orders WHERE region = $1",
            frequency=800.0, avg_latency_ms=300.0, p50_latency_ms=280.0,
            p95_latency_ms=900.0, p99_latency_ms=1500.0,
            tables_accessed=["public.orders"], predicates=["region"],
            join_count=0, read_write_ratio=0.9,
        )],
        resource_metrics=ResourceMetrics(cpu_percent=60.0, memory_percent=70.0, disk_read_bytes=0, disk_write_bytes=0, net_bytes_sent=0, net_bytes_recv=0),
        table_sizes={"public.orders": 2 * 1024 * 1024 * 1024},
        index_usage={"public.orders_pkey": 100.0},
        hot_keys={"public.orders": 500000},
        read_write_ratio=0.5,
        connection_count=15,
    )
    await bus.publish(Topic.WORKLOAD_UPDATE, sig.model_dump(mode="json"), "scenario-b")
    await asyncio.sleep(1.0)

    partition_candidates = [c for c in candidates if c.domain.value == "partitioning"]
    assert len(partition_candidates) > 0, "No partitioning candidates generated"
    await bus.stop()
