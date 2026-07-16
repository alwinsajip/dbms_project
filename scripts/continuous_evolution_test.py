"""
Multi-hour continuous-evolution test for SEDBMS.
Injects synthetic workload signatures, measures pipeline throughput,
and reports evolution metrics.
"""
import argparse
import asyncio
import random
import time
from datetime import datetime, timezone
from typing import Any, Dict, List

from bus import MessageBus, Topic
from schemas import (
    WorkloadSignature, ResourceMetrics, QueryShape, ValidationReport,
    DeploymentEvent, RollbackEvent,
)
from services.cvs import ConfigVersionStore
from services.cge import CandidateGenerationEngine
from services.vce import ValidationCorrectnessEngine

from services.do.deployer import DeploymentOrchestrator
from services.rrc import RollbackRegressionController
from services.policy import PolicyEngine


class EvolutionMetrics:
    def __init__(self):
        self.bus_messages = 0
        self.candidates_proposed = 0
        self.candidates_validated = 0
        self.candidates_passed = 0
        self.deployments_attempted = 0
        self.deployments_succeeded = 0
        self.rollbacks_triggered = 0
        self.policy_violations = 0
        self.start_time = time.time()
        self.candidate_latencies: List[float] = []
        self.deployment_latencies: List[float] = []

    def report(self, elapsed_minutes: float):
        print(f"[{elapsed_minutes:.0f}m] "
              f"candidates={self.candidates_proposed} "
              f"validated={self.candidates_validated} "
              f"passed={self.candidates_passed} "
              f"deployed={self.deployments_succeeded} "
              f"rollbacks={self.rollbacks_triggered} "
              f"violations={self.policy_violations}")


class FakeDTO:
    """In-memory twin that simulates DTO lifecycle without PG."""
    def __init__(self):
        self._fault = True
        self._ready = True

    async def provision_twin(self, ddl: List[Dict[str, Any]]) -> bool:
        return True

    async def replay_workload(self) -> Dict[str, Any]:
        return {
            "baseline": {"p95": random.uniform(1.0, 10.0)},
            "candidate": {"p95": random.uniform(1.0, 10.0)},
        }

    async def destroy_twin(self):
        pass

    @property
    def available(self) -> bool:
        return self._ready


async def generate_workload() -> WorkloadSignature:
    fingerprints = [
        "SELECT * FROM orders WHERE order_id = $1",
        "SELECT * FROM orders WHERE customer_id = $1 ORDER BY order_date DESC LIMIT 20",
        "SELECT region, COUNT(*), SUM(total_amount) FROM orders GROUP BY region",
        "SELECT c.name, o.total_amount FROM customers c JOIN orders o ON c.customer_id = o.customer_id WHERE o.total_amount > $1",
        "SELECT * FROM orders WHERE order_date > NOW() - INTERVAL '1 day' AND region = $1",
        "SELECT * FROM products WHERE category = $1 ORDER BY price DESC",
        "SELECT customer_id, COUNT(*) FROM orders GROUP BY customer_id ORDER BY COUNT(*) DESC LIMIT 10",
        "SELECT * FROM orders WHERE total_amount > $1 AND status = $2",
    ]
    base_tables = ["public.orders", "public.customers", "public.products"]
    return WorkloadSignature(
        query_shapes=[
            QueryShape(
                query_fingerprint=random.choice(fingerprints),
                frequency=random.uniform(10, 1000),
                avg_latency_ms=random.uniform(0.5, 50),
                p50_latency_ms=random.uniform(0.5, 30),
                p95_latency_ms=random.uniform(1.0, 100),
                p99_latency_ms=random.uniform(2.0, 500),
                tables_accessed=[random.choice(base_tables)],
                predicates=[],
                join_count=random.randint(0, 3),
                read_write_ratio=random.uniform(0.3, 0.95),
            )
        ],
        resource_metrics=ResourceMetrics(
            cpu_percent=random.uniform(10, 90),
            memory_percent=random.uniform(30, 85),
            disk_read_bytes=random.randint(1_000_000, 100_000_000),
            disk_write_bytes=random.randint(100_000, 10_000_000),
            net_bytes_sent=random.randint(10_000, 1_000_000),
            net_bytes_recv=random.randint(100_000, 5_000_000),
        ),
        table_sizes={t: random.randint(1000, 500000) for t in base_tables},
        index_usage={"public.orders_pkey": random.uniform(100, 10000)},
        hot_keys={"region": 5000},
        read_write_ratio=random.uniform(0.3, 0.95),
        connection_count=random.randint(5, 200),
    )


async def run_loop(
    duration_minutes: float = 30,
    workload_interval_seconds: float = 30.0,
    drift_events: int = 0,
):
    print(f"[loadtest] Starting {duration_minutes}min continuous evolution test...")
    print(f"[loadtest] Workload interval: {workload_interval_seconds}s, drift events: {drift_events}")
    metrics = EvolutionMetrics()
    drift_done = 0

    bus = MessageBus()
    cvs = ConfigVersionStore(":memory:")
    dto = FakeDTO()

    await bus.start("loadtest")
    cvs.connect()
    policy = PolicyEngine("policy.yaml")

    cge = CandidateGenerationEngine(bus, cvs)
    await cge.start()
    vce = ValidationCorrectnessEngine(bus, cvs, dto)
    await vce.start()
    do_ = DeploymentOrchestrator(bus, cvs)
    await do_.start()
    rrc = RollbackRegressionController(bus, cvs)
    await rrc.start()

    collected: Dict[str, Any] = {
        "candidates": [], "deployments": [], "rollbacks": [],
    }

    async def on_candidate(msg):
        metrics.candidates_proposed += 1
        metrics.candidate_latencies.append(time.time())
        cand_id = msg.payload.get("id", "?")
        print(f"  [candidate] #{metrics.candidates_proposed}: {msg.payload.get('title', '?')} (id={cand_id[:12]}...)")
        collected["candidates"].append(msg.payload)

    async def on_deployment(msg):
        metrics.deployments_attempted += 1
        dep = DeploymentEvent(**msg.payload)
        if dep.status in ("completed", "deployed"):
            metrics.deployments_succeeded += 1
        metrics.deployment_latencies.append(time.time())
        print(f"  [deploy] #{metrics.deployments_attempted}: {dep.status} (id={dep.id[:12]}...)")
        collected["deployments"].append(msg.payload)

    async def on_rollback(msg):
        metrics.rollbacks_triggered += 1
        rb = RollbackEvent(**msg.payload)
        print(f"  [rollback] #{metrics.rollbacks_triggered}: {rb.trigger_reason} (id={rb.id[:12]}...)")
        collected["rollbacks"].append(msg.payload)

    async def on_validation(msg):
        metrics.candidates_validated += 1
        vr = ValidationReport(**msg.payload)
        if vr.passed:
            metrics.candidates_passed += 1

    async def on_policy(msg):
        metrics.policy_violations += 1

    bus.subscribe(Topic.CANDIDATE_PROPOSED, on_candidate)
    bus.subscribe(Topic.DEPLOYMENT_COMPLETED, on_deployment)
    bus.subscribe(Topic.DEPLOYMENT_FAILED, on_deployment)
    bus.subscribe(Topic.ROLLBACK_TRIGGERED, on_rollback)
    bus.subscribe(Topic.VALIDATION_COMPLETE, on_validation)
    bus.subscribe(Topic.POLICY_DECISION, on_policy)

    # Prime CVS with a deployment to make RRC aware
    cvs.save_deployment_event({
        "id": "dep-initial",
        "candidate_id": "cand-initial",
        "correlation_id": "loadtest-init",
        "strategy": "blue_green",
        "status": "completed",
    })

    start = time.time()
    cycle = 0

    try:
        while True:
            elapsed = (time.time() - start) / 60.0
            if elapsed > duration_minutes:
                break

            cycle += 1
            workload = await generate_workload()

            # Inject drift periodically
            if drift_events > 0 and drift_done < drift_events and cycle % max(1, int((60 * duration_minutes / workload_interval_seconds / drift_events))) == 0:
                drift_done += 1
                print(f"  [drift #{drift_done}] Injecting hot-region drift into workload")
                workload.hot_keys = {"region": 50000}
                workload.query_shapes[0].query_fingerprint = "SELECT * FROM orders WHERE region = $1 AND order_date > NOW() - INTERVAL '1 day'"
                workload.query_shapes[0].frequency = 5000

            # Simulate TWM publishing workload
            await bus.publish(Topic.WORKLOAD_UPDATE, workload.model_dump(), f"loadtest-c{cycle}")
            metrics.bus_messages += 1

            await asyncio.sleep(workload_interval_seconds)

            if cycle % 5 == 0:
                metrics.report(elapsed)

    except asyncio.CancelledError:
        print("[loadtest] Cancelled.")
    finally:
        elapsed_actual = (time.time() - start) / 60.0
        print("\n" + "=" * 60)
        print(f"LOAD TEST COMPLETE ({elapsed_actual:.1f} minutes)")
        print("=" * 60)
        print(f"  Bus messages:    {metrics.bus_messages}")
        print(f"  Candidates:      {metrics.candidates_proposed} proposed, "
              f"{metrics.candidates_passed} validated/passed")
        print(f"  Deployments:     {metrics.deployments_attempted} attempted, "
              f"{metrics.deployments_succeeded} succeeded")
        print(f"  Rollbacks:       {metrics.rollbacks_triggered}")
        print(f"  Policy viol.:    {metrics.policy_violations}")
        print(f"\n  Candidates/sec:  {metrics.candidates_proposed / elapsed_actual:.2f}")
        print(f"  Deployments/sec: {metrics.deployments_attempted / elapsed_actual:.2f}")
        if collected["candidates"]:
            print(f"\n  Last candidate:  {collected['candidates'][-1].get('title', '?')}")
        if collected["rollbacks"]:
            print(f"  Last rollback:   {collected['rollbacks'][-1].get('trigger_reason', '?')}")

        # Save metrics
        summary = {
            "duration_minutes": round(elapsed_actual, 1),
            "cycles": cycle,
            "candidates_proposed": metrics.candidates_proposed,
            "candidates_passed": metrics.candidates_passed,
            "deployments_attempted": metrics.deployments_attempted,
            "deployments_succeeded": metrics.deployments_succeeded,
            "rollbacks": metrics.rollbacks_triggered,
            "policy_violations": metrics.policy_violations,
            "throughput_candidates_per_min": round(metrics.candidates_proposed / elapsed_actual, 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        import json
        with open("loadtest_result.json", "w") as f:
            json.dump(summary, f, indent=2)
        print(f"\n  Results saved to loadtest_result.json")

        await bus.stop()


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=float, default=10.0, help="Minutes to run")
    parser.add_argument("--interval", type=float, default=15.0, help="Seconds between workload injections")
    parser.add_argument("--drift", type=int, default=0, help="Number of drift events to inject")
    args = parser.parse_args()

    await run_loop(
        duration_minutes=args.duration,
        workload_interval_seconds=args.interval,
        drift_events=args.drift,
    )


if __name__ == "__main__":
    asyncio.run(main())
