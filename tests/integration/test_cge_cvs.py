import pytest
from bus import MessageBus, Topic
from schemas import WorkloadSignature, ResourceMetrics, QueryShape
from services.cvs import ConfigVersionStore
from services.cge import CandidateGenerationEngine


@pytest.mark.asyncio
async def test_cge_produces_candidates_in_cvs():
    bus = MessageBus.get_instance()
    await bus.start("test")
    cvs = ConfigVersionStore(":memory:")
    cvs.connect()
    cge = CandidateGenerationEngine(bus, cvs)
    await cge.start()

    sig = WorkloadSignature(
        query_shapes=[
            QueryShape(
                query_fingerprint="SELECT * FROM orders WHERE region = $1",
                frequency=500.0, avg_latency_ms=450.0, p50_latency_ms=420.0,
                p95_latency_ms=1200.0, p99_latency_ms=2000.0,
                tables_accessed=["public.orders"], predicates=["region = $1"],
                join_count=0, read_write_ratio=0.9,
            ),
        ],
        resource_metrics=ResourceMetrics(cpu_percent=50, memory_percent=60, disk_read_bytes=0, disk_write_bytes=0, net_bytes_sent=0, net_bytes_recv=0),
        table_sizes={"public.orders": 500 * 1024 * 1024},
        index_usage={},
        hot_keys={},
        read_write_ratio=0.8,
        connection_count=10,
    )

    await bus.publish(Topic.WORKLOAD_UPDATE, sig.model_dump(mode="json"), "test-int")
    import asyncio
    await asyncio.sleep(0.5)

    cur = cvs._conn.cursor()
    cur.execute("SELECT COUNT(*) FROM candidates")
    count = cur.fetchone()[0]
    assert count > 0, "CGE should produce candidates in CVS"

    await bus.stop()
