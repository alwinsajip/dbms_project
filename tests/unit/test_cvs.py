import pytest
from services.cvs import ConfigVersionStore


@pytest.fixture
def cvs():
    db = ConfigVersionStore(":memory:")
    db.connect()
    return db


def test_save_snapshot(cvs):
    sid = cvs.save_snapshot({
        "id": "snap-1",
        "correlation_id": "corr-1",
        "schema_ddl": {"public.t": "CREATE TABLE..."},
        "index_definitions": {},
        "partition_map": {},
        "compression_settings": {},
        "execution_config": {},
    })
    assert sid == "snap-1"
    snap = cvs.get_latest_snapshot()
    assert snap is not None
    assert snap["schema_ddl"]["public.t"] == "CREATE TABLE..."


def test_save_candidate(cvs):
    cvs.save_candidate({
        "id": "cand-1",
        "correlation_id": "corr-1",
        "domain": "indexing",
        "title": "Test",
        "ddl_statements": [],
        "config_deltas": [],
        "status": "proposed",
    })
    c = cvs.get_candidate("cand-1")
    assert c is not None
    assert c["domain"] == "indexing"


def test_save_validation_report(cvs):
    cvs.save_validation_report({
        "id": "report-1",
        "candidate_id": "cand-1",
        "correlation_id": "corr-1",
        "passed": True,
        "correctness_results": [],
        "performance_results": [],
    })
    r = cvs.get_validation_report("cand-1")
    assert r is not None
    assert r["passed"] is True


def test_save_deployment_event(cvs):
    cvs.save_deployment_event({
        "id": "dep-1",
        "candidate_id": "cand-1",
        "correlation_id": "corr-1",
        "strategy": "blue_green",
        "status": "completed",
    })
    events = cvs.get_deployment_events("cand-1")
    assert len(events) == 1


def test_save_rollback_event(cvs):
    cvs.save_rollback_event({
        "id": "rb-1",
        "candidate_id": "cand-1",
        "correlation_id": "corr-1",
        "trigger_reason": "test",
    })
    cur = cvs._conn.cursor()
    cur.execute("SELECT * FROM rollback_events WHERE id = 'rb-1'")
    assert cur.fetchone() is not None


def test_rejected_candidates(cvs):
    cvs.save_candidate({
        "id": "cand-1", "correlation_id": "c", "domain": "indexing",
        "title": "t", "ddl_statements": [], "config_deltas": [],
        "status": "rejected",
    })
    rejected = cvs.get_rejected_candidate_ids()
    assert "cand-1" in rejected
