import asyncio
import pytest
from bus import MessageBus, Topic
from schemas import RollbackEvent
from services.cvs import ConfigVersionStore
from services.rrc import RollbackRegressionController


@pytest.mark.asyncio
async def test_scenario_d():
    bus = MessageBus()
    await bus.start("test")
    cvs = ConfigVersionStore(":memory:")
    cvs.connect()
    rrc = RollbackRegressionController(bus, cvs, regression_p95_threshold=1.3)
    await rrc.start()

    cvs.save_deployment_event({
        "id": "dep-rollback-test",
        "candidate_id": "cand-rollback",
        "correlation_id": "scenario-d",
        "strategy": "blue_green",
        "status": "completed",
    })

    rrc._deployed_candidates["cand-rollback"] = {
        "id": "cand-rollback",
        "correlation_id": "scenario-d",
        "ddl_statements": [{"sql": "CREATE INDEX...", "rollback_sql": "DROP INDEX...", "order": 0}],
    }
    rrc._baselines["cand-rollback"] = {"p95": 5.0, "errors": 0}

    rollbacks = []
    async def on_rollback(msg):
        rollbacks.append(RollbackEvent(**msg.payload))
    bus.subscribe(Topic.ROLLBACK_TRIGGERED, on_rollback)

    regressed_workload = {"query_shapes": [{
        "query_fingerprint": "SELECT * FROM orders WHERE order_id = $1",
        "frequency": 1000.0, "avg_latency_ms": 15.0, "p50_latency_ms": 12.0,
        "p95_latency_ms": 50.0, "p99_latency_ms": 100.0,
        "tables_accessed": ["public.orders"], "predicates": ["order_id"],
        "join_count": 0, "read_write_ratio": 1.0,
    }], "resource_metrics": None, "table_sizes": {}, "index_usage": {},
      "hot_keys": {}, "read_write_ratio": 0.9, "connection_count": 50, "id": "w-1", "timestamp": "2024-01-01"}

    await bus.publish(Topic.WORKLOAD_UPDATE, regressed_workload, "scenario-d-regressed")
    await asyncio.sleep(1.0)

    assert len(rollbacks) > 0, "No rollback triggered"
    assert "p95_ratio" in rollbacks[0].trigger_reason
    await bus.stop()
