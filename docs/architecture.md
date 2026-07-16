# SEDBMS Architecture

## Local-first prototype

This repository runs locally without Docker. The original handoff prompt asked for separately deployable services on a message bus, and this implementation preserves those service boundaries in code while using a lightweight in-process transport for local development and testability.

For the prototype, the control loop is split into the same nine components described in the invention disclosure:

1. `services/twm` - Telemetry and Workload Monitor
2. `services/cge` - Candidate Generation Engine
3. `services/dto` - Digital Twin Orchestrator
4. `services/vce` - Validation and Correctness Engine
5. `services/do` - Deployment Orchestrator
6. `services/rrc` - Rollback and Regression Controller
7. `services/cvs` - Configuration Version Store
8. `services/policy` - Policy and Constraint Engine
9. `services/api` plus `apps/dashboard` - Control-plane API and dashboard

## Why the current bus is local

The handoff suggested Redis Streams or NATS. This repo currently uses `bus/message_bus.py`, an async in-process bus, for two reasons:

- It keeps the prototype runnable on one machine with no container runtime.
- It makes scenario tests deterministic and cheap to execute.

The architectural boundary is still explicit:

- producers publish typed events to `Topic`
- consumers subscribe independently
- correlation IDs are preserved across the loop

That means the bus can be swapped later for Redis Streams or NATS without collapsing the service model into a monolith. If this project is pushed toward multi-process deployment, the first recommended extraction is to replace `MessageBus` with a transport adapter interface and add a Redis Streams implementation.

## Closed-loop flow

The autonomous loop is:

1. TWM observes PostgreSQL activity and host resource metrics.
2. TWM emits a `WorkloadSignature`.
3. CGE generates ranked `Candidate` objects across five modification domains.
4. DTO provisions an isolated twin and applies the candidate.
5. VCE checks correctness and performance criteria and persists a `ValidationReport`.
6. DO deploys only validated candidates and records deployment events in CVS.
7. RRC watches post-deployment workload updates and triggers rollback on regression.
8. CVS stores snapshots, candidates, validation reports, deployments, and rollbacks as the audit backbone.
9. API and dashboard expose the full trail for inspection and evidence capture.

## Service boundaries

Each service is isolated around a single responsibility:

- TWM owns observation and normalization.
- CGE owns proposal generation only.
- DTO owns twin lifecycle only.
- VCE owns pass/fail logic only.
- DO owns rollout execution only.
- RRC owns regression detection and reversion only.
- CVS owns append-only history and retrieval.
- Policy owns operator constraints.
- API/dashboard own observability and control-plane presentation.

This mirrors the patent-oriented claim structure closely and keeps the reduction-to-practice mapping straightforward.

## Digital twin implementation note

The DTO is written around a state-driven lifecycle:

`provision -> apply -> replay/evaluate -> destroy`

The current implementation uses local PostgreSQL binaries and `pg_basebackup` for twin provisioning. That is the correct local-first path for a no-Docker setup, though the repo still treats the twin as an isolated executable replica that can be replaced by a copy-on-write snapshot approach later.

## Local deployment model

The local prototype assumes:

- a PostgreSQL instance on `localhost:5432`
- PostgreSQL client binaries available locally
- Python services started from one machine

That is a deployment choice, not an architectural limitation. The code organization keeps the door open for moving each service into its own process later.

## Known deviations from the original handoff

- No Docker compose: replaced with direct local startup and scripts.
- No Redis or NATS yet: replaced with an in-process event bus.
- Validation and deployment are partially simulated in tests and scenario harnesses to keep the loop runnable without heavy infrastructure.

These deviations should be called out in patent support materials as implementation choices for the prototype rather than claim limitations of the overall invention.
