# Evidence Appendix — SEDBMS Reduction to Practice

## Test Results

- **Total tests:** 28 (22 unit + 6 scenarios)
- **Passed:** 28
- **Failed:** 0
- **Date:** July 15, 2026

## Scenario Evidence

### Scenario A — Index Autogeneration (Workload Drift)
- **File:** `tests/scenarios/test_scenario_a_index_autogen.py`
- **Assertions passed:**
  - Candidates generated from workload signature with drift
  - Index candidates target the drifted query's predicate column (orders.region)
  - DDL statements contain CREATE INDEX on target table
  - Validation report shows passing correctness and performance
- **Zero manual interventions:** ✓

### Scenario B — Repartitioning (Data Skew)
- **File:** `tests/scenarios/test_scenario_b_repartitioning.py`
- **Assertions passed:**
  - Partitioning candidates generated for skewed large table
  - Detection of hot-key skew triggers rebalancing proposal
- **Zero manual interventions:** ✓

### Scenario C — Compression (Cold Data)
- **File:** `tests/scenarios/test_scenario_c_compression.py`
- **Assertions passed:**
  - Compression candidates generated for cold, infrequently-read table
  - TOAST compression adjustments proposed
- **Zero manual interventions:** ✓

### Scenario D — Forced Regression → Automatic Rollback
- **File:** `tests/scenarios/test_scenario_d_auto_rollback.py`
- **Assertions passed:**
  - Deployment recorded in CVS
  - RRC monitors post-deployment workload
  - p95 regression (10x above baseline) detected
  - Rollback triggered with p95_ratio in trigger reason
  - Rollback event recorded in CVS
- **Zero manual interventions:** ✓
- **This is the strongest evidence for the "automatically revert upon detection of performance regression" claim element.**

### Scenario E — Correctness-Failure Rejection
- **File:** `tests/scenarios/test_scenario_e_correctness_rejection.py`
- **Assertions passed:**
  - Bad candidate (CHECK constraint without NOT VALID) submitted
  - VCE detects safety issue via SQL pattern analysis
  - Validation report shows failure
  - No deployment events created for the bad candidate
- **Zero manual interventions:** ✓

### Scenario F — Policy Guardrail Enforcement
- **File:** `tests/scenarios/test_scenario_f_policy_guardrails.py`
- **Assertions passed:**
  - Blocked-table policy prevents candidate on protected table
  - Non-blocked table candidate allowed
- **Zero manual interventions:** ✓

## Raw Logs

- `test_results.xml` — JUnit XML output from pytest run
- Individual scenario evidence files stored in scenario subdirectories

## How to Reproduce

```bash
cd sedbms
pip install -e ".[dev]"
py -3.12 -m pytest tests/unit tests/scenarios -v
```
