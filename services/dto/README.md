# Digital Twin Orchestrator

## Role

Creates an executable replica of the production database, applies a candidate change, and tears the replica down after evaluation.

## Inputs

- candidate DDL and configuration deltas
- local PostgreSQL binaries and connectivity to the source instance

## Outputs

- twin lifecycle transitions used by VCE
- isolated twin environment for validation

## Failure modes

- PostgreSQL binaries missing: twin creation fails immediately
- base backup failure: candidate cannot be evaluated
- DDL apply failure: evaluation aborts and VCE records a failed validation
- teardown failure: orphaned twin directories may remain and need cleanup
