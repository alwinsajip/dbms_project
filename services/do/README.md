# Deployment Orchestrator

## Role

Consumes only passing validation reports, snapshots the current configuration, applies production changes, and records deployment outcomes.

## Inputs

- passing `ValidationReport`
- candidate DDL and config deltas
- local PostgreSQL control binaries

## Outputs

- `DeploymentEvent` records in CVS
- `Topic.DEPLOYMENT_STARTED`
- `Topic.DEPLOYMENT_COMPLETED`
- `Topic.DEPLOYMENT_FAILED`

## Failure modes

- snapshot capture failure: deployment should abort before mutation
- DDL execution failure: deployment is marked failed
- health-check failure: deployment is recorded as failed and becomes eligible for rollback logic
