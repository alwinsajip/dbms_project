from schemas import (
    WorkloadSignature, ResourceMetrics, QueryShape, Candidate,
    ValidationReport, DeploymentEvent, RollbackEvent, ConfigSnapshot,
    DDLStatement, ConfigDelta, ModificationDomain, CandidateStatus,
)


def test_workload_signature_creation():
    sig = WorkloadSignature(
        query_shapes=[
            QueryShape(
                query_fingerprint="SELECT * FROM t WHERE id = $1",
                frequency=100.0, avg_latency_ms=5.0, p50_latency_ms=4.0,
                p95_latency_ms=10.0, p99_latency_ms=20.0,
                tables_accessed=["public.t"], predicates=["id"],
                join_count=0, read_write_ratio=1.0,
            ),
        ],
        resource_metrics=ResourceMetrics(
            cpu_percent=50.0, memory_percent=60.0,
            disk_read_bytes=1000, disk_write_bytes=500,
            net_bytes_sent=100, net_bytes_recv=200,
        ),
        table_sizes={"public.t": 1024 * 1024},
        index_usage={"public.t_pkey": 100.0},
        hot_keys={},
        read_write_ratio=0.8,
        connection_count=10,
    )
    assert sig.id is not None
    assert len(sig.query_shapes) == 1
    assert sig.query_shapes[0].frequency == 100.0


def test_candidate_creation():
    c = Candidate(
        domain=ModificationDomain.indexing,
        title="Test index",
        description="Test",
        ddl_statements=[DDLStatement(sql="CREATE INDEX...", rollback_sql="DROP INDEX...", order=0)],
        correlation_id="corr-1",
    )
    assert c.id is not None
    assert c.status == CandidateStatus.proposed
    assert c.ddl_statements[0].sql == "CREATE INDEX..."


def test_validation_report():
    r = ValidationReport(
        candidate_id="cand-1",
        correlation_id="corr-1",
        passed=True,
    )
    assert r.passed is True
    assert r.candidate_id == "cand-1"


def test_deployment_event():
    e = DeploymentEvent(
        candidate_id="cand-1",
        correlation_id="corr-1",
        strategy="blue_green",
        status="completed",
    )
    assert e.status == "completed"


def test_rollback_event():
    r = RollbackEvent(
        candidate_id="cand-1",
        correlation_id="corr-1",
        trigger_reason="p95_regression",
    )
    assert r.success is True


def test_config_snapshot():
    s = ConfigSnapshot()
    assert s.id is not None
