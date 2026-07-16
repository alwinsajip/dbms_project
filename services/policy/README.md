# Policy & Constraint Engine

## Role

Evaluates operator-defined guardrails before autonomous actions proceed.

## Inputs

- `policy.yaml`
- candidate metadata
- runtime action context

## Outputs

- allow or deny decisions with human-readable reasons

## Failure modes

- malformed policy file: rules may not load as expected
- missing policy file: engine falls back to permissive behavior
- incomplete action context: some blackout or safety rules may not trigger
