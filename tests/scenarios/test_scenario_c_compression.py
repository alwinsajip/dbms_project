import asyncio
import pytest
from bus import MessageBus, Topic
from schemas import WorkloadSignature, ResourceMetrics, QueryShape, Candidate
from services.cvs import ConfigVersionStore
from services.cge import CandidateGenerationEngine


@pytest.mark.asyncio
async def test_scenario_c():
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
        query_shapes=[
            QueryShape(
                query_fingerprint="SELECT * FROM archive_log WHERE created_at < $1",
                frequency=2.0, avg_latency_ms=5000.0, p50_latency_ms=4800.0,
                p95_latency_ms=12000.0, p99_latency_ms=20000.0,
                tables_accessed=["public.archive_log"], predicates=["created_at"],
                join_count=0, read_write_ratio=1.0,
            ),
        ],
        resource_metrics=ResourceMetrics(cpu_percent=30.0, memory_percent=50.0, disk_read_bytes=0, disk_write_bytes=0, net_bytes_sent=0, net_bytes_recv=0),
        table_sizes={"public.archive_log": 5 * 1024 * 1024 * 1024},
        index_usage={},
        hot_keys={},
        read_write_ratio=0.1,
        connection_count=5,
    )
    await bus.publish(Topic.WORKLOAD_UPDATE, sig.model_dump(mode="json"), "scenario-c")
    await asyncio.sleep(1.0)

    compression_candidates = [c for c in candidates if c.domain.value == "compression"]
    assert len(compression_candidates) > 0, "No compression candidates generated"
    await bus.stop()
