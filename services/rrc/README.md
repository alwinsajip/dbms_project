# Rollback & Regression Controller

## Role

Monitors live post-deployment workload behavior against baseline metrics and automatically reverts candidates that regress.

## Inputs

- deployment completion events
- ongoing workload updates
- rollback SQL stored with each candidate

## Outputs

- rollback records in CVS
- `Topic.ROLLBACK_TRIGGERED`
- `Topic.ROLLBACK_COMPLETED`

## Failure modes

- no baseline captured: the first post-deployment sample is used to initialize baseline
- rollback SQL failure: rollback is attempted but may complete with warnings
- noisy telemetry: false positives can trigger rollback if thresholds are too aggressive
