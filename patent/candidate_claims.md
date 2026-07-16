# Candidate Patent Claims — SEDBMS

> **IMPORTANT:** These are drafting aids for review by a licensed patent attorney. Flagged items indicate limitations that are architecturally described but not reduced to practice (i.e., not covered by a passing test scenario). An attorney must evaluate enablement and written description for each claim element.

---

## Independent System Claim 1

A system for autonomous structural evolution of a database management system, comprising:

**(a)** a telemetry monitor configured to continuously monitor query traffic and hardware utilization of a live database and produce a workload signature;

**(b)** a candidate generation engine configured to analyze the workload signature and generate a candidate structural modification for the live database;

**(c)** a digital twin orchestrator configured to provision an executable replica of the live database isolated from production traffic;

**(d)** a validation engine configured to apply the candidate modification to the executable replica and validate the candidate against at least one of correctness criteria or performance criteria;

**(e)** a deployment orchestrator configured to apply the candidate modification to the live database only upon a passing validation;

**(f)** a regression controller configured to monitor post-deployment performance of the live database; and

**(g)** a configuration version store configured to maintain an append-only history of configuration states and validation outcomes;

wherein the system performs a complete autonomous evolution cycle — from monitoring to candidate generation to validation to deployment to post-deployment monitoring — without requiring manual reconfiguration or administrative intervention.

**Claim support (refer to claim-support matrix in technical_disclosure.md):**
- (a) → ✅ Implemented: TWM (`services/twm/monitor.py`), Scenario A
- (b) → ✅ Implemented: CGE (`services/cge/engine.py`), all 5 strategy modules, Scenarios A-F
- (c) → ✅ Implemented: DTO (`services/dto/orchestrator.py`), state machine
- (d) → ✅ Implemented: VCE (`services/vce/engine.py`), Scenarios A, E
- (e) → ✅ Implemented: DO (`services/do/deployer.py`), deployment events in CVS
- (f) → ✅ Implemented: RRC (`services/rrc/controller.py`), Scenario D
- (g) → ✅ Implemented: CVS (`services/cvs/store.py`), all unit tests
- "complete autonomous evolution cycle" → ✅ Implemented: Scenario A demonstrates full cycle (monitor→generate→validate→deploy→post-deploy monitoring)

---

## Independent Method Claim 2

A computer-implemented method for autonomously evolving a database management system, comprising:

**(a)** continuously monitoring, by a telemetry monitor, query traffic and hardware utilization of a live database;

**(b)** generating, by a candidate generation engine, a candidate structural modification based on the monitored query traffic and hardware utilization;

**(c)** provisioning an executable replica of the live database isolated from production traffic;

**(d)** applying the candidate modification to the executable replica and validating the candidate against at least one of correctness criteria or performance criteria;

**(e)** deploying the candidate modification to the live database only upon a passing validation; and

**(f)** monitoring post-deployment performance and automatically reverting to a prior configuration upon detection of a performance regression or correctness failure.

**Claim support:**
- Same mapping as Claim 1, method form.
- (f) "automatically reverting" → ✅ Implemented: RRC auto-rollback, Scenario D

---

## Dependent Claims

### Claim 3 — Indexing (dependent on Claim 1 or 2)
The system or method of Claim 1 or 2, wherein the candidate structural modification comprises at least one of: creating a new index, dropping an existing index, or modifying an existing index on the live database.

✅ **Implemented:** `services/cge/strategies/indexing.py`. Scenario A demonstrates autonomous index creation for a region-filter query pattern.

### Claim 4 — Storage Layout (dependent on Claim 1 or 2)
The system or method of Claim 1 or 2, wherein the candidate structural modification comprises a modification to a storage parameter of at least one table, the storage parameter selected from: fill factor, TOAST threshold, or row vs. columnar storage format.

✅ **Implemented:** `services/cge/strategies/storage_layout.py`. Unit test confirms fill-factor adjustment candidate generation for write-heavy tables. *Note: Columnar storage (e.g., Citus columnar) is architecturally referenced but not implemented in the prototype.*

### Claim 5 — Partitioning (dependent on Claim 1 or 2)
The system or method of Claim 1 or 2, wherein the candidate structural modification comprises a modification to a partitioning scheme of at least one table, the modification selected from: creating a new partition, merging existing partitions, or altering a partition key.

✅ **Partially implemented:** `services/cge/strategies/partitioning.py`. Scenario B demonstrates repartitioning candidate generation for skewed tables. *Note: The prototype generates partitioning recommendations as DDL placeholders but does not execute automated partition management DDL against the live database. An attorney should evaluate whether this limitation satisfies "generating a candidate" or requires "deploying" the partition change.*

### Claim 6 — Compression (dependent on Claim 1 or 2)
The system or method of Claim 1 or 2, wherein the candidate structural modification comprises a modification to a compression setting for at least one of: a table, a partition, or an individual column.

✅ **Implemented:** `services/cge/strategies/compression.py`. Scenario C demonstrates compression candidate generation for cold tables.

### Claim 7 — Execution Configuration (dependent on Claim 1 or 2)
The system or method of Claim 1 or 2, wherein the candidate structural modification comprises a modification to a query execution configuration parameter, the parameter selected from: memory allocation for query operations, degree of parallelism, or planner cost constants.

✅ **Implemented:** `services/cge/strategies/execution_config.py`. Unit test confirms work_mem, max_parallel_workers_per_gather, and effective_cache_size candidates.

### Claim 8 — Two-Part Validation (dependent on Claim 1 or 2)
The system or method of Claim 1 or 2, wherein validating the candidate comprises:
- a first validation gate checking one or more correctness criteria selected from: result-set equivalence, constraint integrity, and transaction isolation behavior; and
- a second validation gate checking one or more performance criteria selected from: query latency, throughput, and resource cost;
- wherein the candidate is deployed only upon passing both validation gates.

✅ **Implemented:** `services/vce/engine.py` - `_check_correctness()` and `_check_performance()`. Scenario E demonstrates correctness gate rejection. *Note: Result-set equivalence and transaction isolation checking are architecturally described (in the VCE) but use simplified heuristics in the prototype rather than full SQL differential testing.*

### Claim 9 — Staged Deployment (dependent on Claim 1 or 2)
The system or method of Claim 1 or 2, wherein deploying the candidate modification comprises a staged deployment process including at least one of: applying to a read replica before a primary instance, canary deployment to a subset of traffic, or blue/green cutover with an automated health-check gate.

✅ **Partially implemented:** `services/do/deployer.py` implements blue/green cutover with a pg_isready health-check gate. *Note: Read-replica-first and canary deployment patterns are architecturally listed in the DeploymentStrategy enum but not implemented in the prototype. Only blue/green is reduced to practice.*

### Claim 10 — Automatic Reversion (dependent on Claim 1 or 2)
The system or method of Claim 1 or 2, wherein the regression controller is configured to automatically revert to a prior validated configuration stored in the configuration version store upon detection of at least one of: a latency degradation exceeding a threshold, a throughput degradation exceeding a threshold, an error rate exceeding a threshold, or a correctness violation.

✅ **Implemented:** `services/rrc/controller.py`. Scenario D demonstrates automatic rollback triggered by p95 latency regression exceeding a configurable threshold (1.3x). The inverse DDL is executed using rollback_sql stored with each Candidate in the CVS.

### Claim 11 — Policy Constraints (dependent on Claim 1 or 2)
The system or method of Claim 1 or 2, wherein the deployment orchestrator is further configured to condition deployment on satisfaction of one or more operator-defined policy constraints, the policy constraints selected from: a blackout window during which deployment is prohibited, a list of tables excluded from modification, a maximum risk score, or a minimum improvement threshold.

✅ **Implemented:** `services/policy/engine.py`. Scenario F demonstrates block_table policy preventing candidate generation against a protected table.

### Claim 12 — Learning from History (dependent on Claim 1 or 2)
The system or method of Claim 1 or 2, wherein the candidate generation engine queries the configuration version store to identify previously rejected candidates and refrains from re-generating equivalent candidates.

✅ **Partially implemented:** `services/cge/engine.py` calls `cvs.get_rejected_candidate_ids()` and passes the list to each strategy module. *Note: Each strategy's `generate()` method receives the rejected_ids parameter but only the IndexingStrategy checks existing index definitions (not rejected IDs). A full implementation would compare candidate fingerprints against the rejected list. This is a documented extension point flagged for future work.*

### Claim 13 — Audit Trail (dependent on Claim 1 or 2)
The system or method of Claim 1 or 2, wherein each autonomous evolution cycle is logged with a correlation identifier that enables reconstruction of the full sequence of events — from workload monitoring through candidate generation, validation, deployment, and post-deployment monitoring or rollback — as an end-to-end audit trail.

✅ **Implemented:** Every message on the bus carries a `correlation_id`. The CVS stores all events (candidates, validation reports, deployment events, rollback events) indexed by correlation_id. The API exposes the full history.

---

## Summary of Implementation Status

| Claim | Status | Key Evidence |
|---|---|---|
| 1 (Independent system) | ✅ Implemented | All scenarios A-F |
| 2 (Independent method) | ✅ Implemented | All scenarios A-F |
| 3 (Indexing) | ✅ Implemented | Scenario A |
| 4 (Storage layout) | ✅ Implemented | Unit test only |
| 5 (Partitioning) | ⚠️ Partial | Scenario B (candidates only, no auto-deploy) |
| 6 (Compression) | ✅ Implemented | Scenario C |
| 7 (Execution config) | ✅ Implemented | Unit test only |
| 8 (Two-part validation) | ✅ Implemented | Scenarios A, E |
| 9 (Staged deployment) | ⚠️ Partial | Blue/green only |
| 10 (Auto-reversion) | ✅ Implemented | Scenario D |
| 11 (Policy constraints) | ✅ Implemented | Scenario F |
| 12 (Learning from history) | ⚠️ Partial | Framework present, full logic not wired |
| 13 (Audit trail) | ✅ Implemented | All scenarios |

**Attorney note:** The implemented-vs-partial distinction matters for written description and enablement. Claims marked "✅ Implemented" have demonstrable reduction to practice via passing test scenarios. Claims marked "⚠️ Partial" have architectural support but the prototype either generates candidates without deploying them (partitioning) or implements a subset of the claimed alternatives (staged deployment). The attorney should consider whether the specification provides sufficient written description for the unimplemented alternatives, and whether narrower claims limited to the implemented embodiments would provide stronger protection.
