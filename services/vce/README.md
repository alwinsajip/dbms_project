# Validation & Correctness Engine

## Role

Runs correctness and performance gates against a candidate inside a digital twin and produces a persisted `ValidationReport`.

## Inputs

- `Topic.CANDIDATE_PROPOSED`
- twin orchestration from DTO
- validation thresholds and baseline assumptions

## Outputs

- CVS validation reports
- `Topic.VALIDATION_COMPLETE`

## Failure modes

- twin provisioning failure: validation fails closed
- correctness rule failure: candidate is rejected before deployment
- performance regression: candidate is marked failed even if correctness passes
