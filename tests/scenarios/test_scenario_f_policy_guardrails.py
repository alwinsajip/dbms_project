import tempfile
import pytest
import yaml
from schemas import Candidate, DDLStatement, ModificationDomain
from services.policy import PolicyEngine


@pytest.mark.asyncio
async def test_scenario_f():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({"rules": [{
            "name": "block-sensitive-tables",
            "enabled": True,
            "rule_type": "block_table",
            "config": {"tables": ["public.orders"]},
        }]}, f)
        path = f.name

    policy = PolicyEngine(path)

    blocked = Candidate(
        domain=ModificationDomain.indexing, title="Blocked",
        description="Should be blocked",
        ddl_statements=[DDLStatement(sql="CREATE INDEX ON public.orders (id)", rollback_sql="DROP INDEX", order=0)],
        correlation_id="test",
    )
    allowed, reason = policy.check_candidate_allowed(blocked)
    assert not allowed, f"Blocked table should be rejected: {reason}"
    assert "orders" in reason

    ok = Candidate(
        domain=ModificationDomain.indexing, title="OK",
        description="Should be allowed",
        ddl_statements=[DDLStatement(sql="CREATE INDEX ON public.customers (id)", rollback_sql="DROP INDEX", order=0)],
        correlation_id="test",
    )
    allowed2, _ = policy.check_candidate_allowed(ok)
    assert allowed2
