import tempfile
import yaml
from schemas import Candidate, DDLStatement, ModificationDomain
from services.policy import PolicyEngine


def test_block_table_policy():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({"rules": [{
            "name": "block-orders",
            "enabled": True,
            "rule_type": "block_table",
            "config": {"tables": ["public.orders"]},
        }]}, f)
        path = f.name

    policy = PolicyEngine(path)
    blocked = Candidate(
        domain=ModificationDomain.indexing,
        title="Blocked",
        ddl_statements=[DDLStatement(sql="CREATE INDEX ON public.orders (id)", rollback_sql="DROP INDEX", order=0)],
        correlation_id="test",
    )
    allowed, reason = policy.check_candidate_allowed(blocked)
    assert not allowed
    assert "orders" in reason

    ok_candidate = Candidate(
        domain=ModificationDomain.indexing,
        title="OK",
        ddl_statements=[DDLStatement(sql="CREATE INDEX ON public.customers (id)", rollback_sql="DROP INDEX", order=0)],
        correlation_id="test",
    )
    allowed2, _ = policy.check_candidate_allowed(ok_candidate)
    assert allowed2


def test_max_risk_policy():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({"rules": [{
            "name": "max-risk",
            "enabled": True,
            "rule_type": "max_risk",
            "config": {"value": 0.5},
        }]}, f)
        path = f.name

    policy = PolicyEngine(path)
    risky = Candidate(
        domain=ModificationDomain.partitioning, title="Risky",
        predicted_risk=0.9, correlation_id="test",
    )
    allowed, reason = policy.check_candidate_allowed(risky)
    assert not allowed
    assert "risk" in reason.lower()

    safe = Candidate(
        domain=ModificationDomain.indexing, title="Safe",
        predicted_risk=0.1, correlation_id="test",
    )
    allowed2, _ = policy.check_candidate_allowed(safe)
    assert allowed2


def test_no_rules():
    policy = PolicyEngine()
    c = Candidate(domain=ModificationDomain.indexing, title="Test", correlation_id="test")
    allowed, reason = policy.check_candidate_allowed(c)
    assert allowed is True
    assert reason is None
