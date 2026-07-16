# SEDBMS - Self-Evolving Database Management System

A closed-loop control plane that continuously observes query workload and hardware telemetry, generates candidate structural reconfigurations, validates each candidate inside a digital-twin replica, and autonomously deploys or reverts changes without requiring manual reconfiguration or administrative intervention.

Patent support artifacts live under `patent/`.

## Architecture

`TWM -> CGE -> DTO -> VCE -> DO -> RRC -> Production DB`

Each stage writes audit state into CVS, consults policy guardrails, and can be inspected through the API and dashboard.

The local prototype keeps the service boundaries from the original design while using an in-process async bus so the system can run on one machine with no Docker dependency. See `docs/architecture.md` for the rationale and deviation notes.

## Services

| Service | Role |
|---|---|
| `twm` | Telemetry and Workload Monitor |
| `cge` | Candidate Generation Engine |
| `dto` | Digital Twin Orchestrator |
| `vce` | Validation and Correctness Engine |
| `do` | Deployment Orchestrator |
| `rrc` | Rollback and Regression Controller |
| `cvs` | Configuration Version Store |
| `policy` | Policy and Constraint Engine |
| `api` | Control-plane API |

Each service directory now includes its own `README.md` covering inputs, outputs, and failure modes.

## Local Run

### Prerequisites

- Python 3.12+
- PostgreSQL 16+ available locally
- `psql`, `pg_basebackup`, `pg_ctl`, and `pg_isready` available locally
- No Docker required

### Setup

```bash
python -m venv .venv
```

Activate the virtual environment before installing dependencies:

```bash
# Windows PowerShell
.venv\Scripts\Activate.ps1

# Windows cmd
.venv\Scripts\activate.bat

# macOS / Linux
source .venv/bin/activate
```

Then install the project dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install --no-build-isolation -e .
```

### Smoke validation

This verifies that the package imports and wiring are intact before you try to start PostgreSQL-backed services:

```bash
python scripts/run_local_validation.py
```

### Start the control plane

```bash
python main.py
```

The API is served at `http://127.0.0.1:8080`.

The local project-owned PostgreSQL instances default to:

- production: `localhost:5542`
- twin: `localhost:5543`

### Generate workload

```bash
python scripts/generate_workload.py --duration 10 --drift-after 2
```

### Run automated tests

```bash
python -m pytest tests/unit tests/integration tests/scenarios -v
```

### Run the long-form evolution harness

```bash
python scripts/continuous_evolution_test.py --duration 10 --interval 15 --drift 2
```

Results are written to `loadtest_result.json`.

## Scenario coverage

The repository includes the six scenario suites requested in the handoff:

- Scenario A: index autogeneration under workload drift
- Scenario B: repartitioning under data skew
- Scenario C: compression reconfiguration for cold data
- Scenario D: forced regression followed by automatic rollback
- Scenario E: correctness failure rejected before deployment
- Scenario F: policy guardrail enforcement

These live under `tests/scenarios/` and are intended to provide the reduction-to-practice evidence trail used by the patent support documents.

## Repository layout

```text
sedbms/
|-- apps/dashboard/
|-- bus/
|-- docs/
|-- patent/
|-- schemas/
|-- scripts/
|-- services/
|-- tests/
|-- main.py
|-- policy.yaml
`-- pyproject.toml
```

## Notes

- The current message transport is intentionally local and in-process for prototype simplicity.
- The DTO, deployment, and rollback paths are structured so they can later be moved to separate processes and a real external bus without changing the core contracts.
- The API bug in candidate listing has been fixed so control-plane queries now return rows correctly from SQLite.
