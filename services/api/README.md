# Control-plane API

## Role

Exposes current state, candidate history, validation results, deployments, rollbacks, and trigger endpoints for local demos and dashboard use.

## Inputs

- CVS history
- optional live bus access for trigger actions

## Outputs

- REST endpoints under `/api/*`

## Failure modes

- CVS unavailable: read endpoints fail
- malformed persisted rows: serialization may fail for individual records
- missing bus: trigger endpoints are unavailable while read endpoints continue to work
