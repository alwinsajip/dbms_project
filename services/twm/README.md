# Telemetry & Workload Monitor

## Role

Continuously samples database and host behavior, normalizes it into `WorkloadSignature`, and emits workload updates and anomalies into the control loop.

## Inputs

- PostgreSQL statistics views and statement activity
- Host resource metrics from `psutil`

## Outputs

- `Topic.WORKLOAD_UPDATE`
- `Topic.WORKLOAD_ANOMALY`

## Failure modes

- PostgreSQL unavailable: monitor keeps running and emits an empty or degraded signature.
- Stats views unavailable: query-shape fields may be partial.
- Host metric collection failure: resource fields may degrade to zero values or defaults.
