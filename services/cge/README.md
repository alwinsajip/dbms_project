# Candidate Generation Engine

## Role

Consumes workload signatures and generates ranked structural modification candidates across five domains:

- storage layout
- indexing
- partitioning
- compression
- execution configuration

## Inputs

- `WorkloadSignature`
- current `ConfigSnapshot`
- candidate history from CVS

## Outputs

- persisted `Candidate` records in CVS
- `Topic.CANDIDATE_PROPOSED`

## Failure modes

- strategy exception: one strategy may fail while the engine continues evaluating the remaining strategies
- malformed workload signature: candidate generation for that event is skipped
- stale current-state snapshot: may lead to duplicate or lower-quality proposals
