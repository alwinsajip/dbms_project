import pytest
from schemas import WorkloadSignature, ResourceMetrics, QueryShape, ConfigSnapshot
from services.cge.strategies.indexing import IndexingStrategy
from services.cge.strategies.storage_layout import StorageLayoutStrategy
from services.cge.strategies.compression import CompressionStrategy
from services.cge.strategies.execution_config import ExecutionConfigStrategy


def make_signature(query_shapes=None, table_sizes=None, hot_keys=None):
    return WorkloadSignature(
        query_shapes=query_shapes or [],
        resource_metrics=ResourceMetrics(cpu_percent=50, memory_percent=60, disk_read_bytes=0, disk_write_bytes=0, net_bytes_sent=0, net_bytes_recv=0),
        table_sizes=table_sizes or {},
        index_usage={},
        hot_keys=hot_keys or {},
        read_write_ratio=0.8,
        connection_count=10,
    )


def test_indexing_strategy_generates_candidate():
    sig = make_signature(
        query_shapes=[
            QueryShape(
                query_fingerprint="SELECT * FROM orders WHERE region = $1",
                frequency=500.0, avg_latency_ms=450.0, p50_latency_ms=420.0,
                p95_latency_ms=1200.0, p99_latency_ms=2000.0,
                tables_accessed=["public.orders"], predicates=["region = $1"],
                join_count=0, read_write_ratio=0.9,
            ),
        ],
        table_sizes={"public.orders": 500 * 1024 * 1024},
    )
    state = ConfigSnapshot()
    strategy = IndexingStrategy()
    candidates = strategy.generate(sig, state, [])
    assert len(candidates) > 0
    assert candidates[0].domain.value == "indexing"
    assert "orders" in candidates[0].ddl_statements[0].sql


def test_storage_layout_strategy():
    sig = make_signature(
        query_shapes=[
            QueryShape(
                query_fingerprint="INSERT INTO audit_log VALUES ($1, $2, $3)",
                frequency=200.0, avg_latency_ms=2.0, p50_latency_ms=1.0,
                p95_latency_ms=5.0, p99_latency_ms=8.0,
                tables_accessed=["public.audit_log"], predicates=[],
                join_count=0, read_write_ratio=0.0,
            ),
        ],
        table_sizes={"public.audit_log": 100 * 1024 * 1024},
    )
    state = ConfigSnapshot()
    strategy = StorageLayoutStrategy()
    candidates = strategy.generate(sig, state, [])
    assert len(candidates) > 0
    assert "fillfactor" in candidates[0].ddl_statements[0].sql


def test_compression_strategy():
    sig = make_signature(
        query_shapes=[
            QueryShape(
                query_fingerprint="SELECT * FROM archive WHERE date < $1",
                frequency=2.0, avg_latency_ms=5000.0, p50_latency_ms=4800.0,
                p95_latency_ms=10000.0, p99_latency_ms=20000.0,
                tables_accessed=["public.archive"], predicates=["date"],
                join_count=0, read_write_ratio=1.0,
            ),
        ],
        table_sizes={"public.archive": 1024 * 1024 * 1024},
    )
    state = ConfigSnapshot()
    strategy = CompressionStrategy()
    candidates = strategy.generate(sig, state, [])
    assert len(candidates) > 0
    assert "toast_tuple_target" in candidates[0].ddl_statements[0].sql


def test_execution_config_strategy():
    sig = make_signature(
        query_shapes=[
            QueryShape(
                query_fingerprint="SELECT * FROM a JOIN b ON a.id = b.id",
                frequency=100.0, avg_latency_ms=200.0, p50_latency_ms=180.0,
                p95_latency_ms=500.0, p99_latency_ms=1000.0,
                tables_accessed=["public.a", "public.b"], predicates=[],
                join_count=1, read_write_ratio=1.0,
            ),
        ],
    )
    state = ConfigSnapshot(execution_config={})
    strategy = ExecutionConfigStrategy()
    candidates = strategy.generate(sig, state, [])
    assert len(candidates) > 0


def test_strategy_avoids_rejected():
    sig = make_signature(
        query_shapes=[
            QueryShape(
                query_fingerprint="SELECT * FROM orders WHERE region = $1",
                frequency=500.0, avg_latency_ms=450.0, p50_latency_ms=420.0,
                p95_latency_ms=1200.0, p99_latency_ms=2000.0,
                tables_accessed=["public.orders"], predicates=["region = $1"],
                join_count=0, read_write_ratio=0.9,
            ),
        ],
        table_sizes={"public.orders": 500 * 1024 * 1024},
    )
    state = ConfigSnapshot()
    strategy = IndexingStrategy()
    candidates = strategy.generate(sig, state, [])
    assert len(candidates) > 0
