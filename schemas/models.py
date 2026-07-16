from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

def _utcnow():
    return datetime.now(timezone.utc)

from pydantic import BaseModel, Field


class ModificationDomain(str, Enum):
    storage_layout = "storage_layout"
    indexing = "indexing"
    partitioning = "partitioning"
    compression = "compression"
    execution_config = "execution_config"


class CandidateStatus(str, Enum):
    proposed = "proposed"
    evaluating = "evaluating"
    validated = "validated"
    failed = "failed"
    deploying = "deploying"
    deployed = "deployed"
    reverted = "reverted"
    rejected = "rejected"


class QueryShape(BaseModel):
    query_fingerprint: str
    frequency: float
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    tables_accessed: List[str]
    predicates: List[str]
    join_count: int
    read_write_ratio: float


class ResourceMetrics(BaseModel):
    cpu_percent: float
    memory_percent: float
    disk_read_bytes: int
    disk_write_bytes: int
    net_bytes_sent: int
    net_bytes_recv: int
    timestamp: datetime = Field(default_factory=_utcnow)


class WorkloadSignature(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=_utcnow)
    query_shapes: List[QueryShape]
    resource_metrics: ResourceMetrics
    table_sizes: Dict[str, int]
    index_usage: Dict[str, float]
    hot_keys: Dict[str, int]
    read_write_ratio: float
    connection_count: int
    anomaly_flags: List[str] = []


class DDLStatement(BaseModel):
    sql: str
    rollback_sql: str
    order: int = 0


class ConfigDelta(BaseModel):
    parameter: str
    old_value: Any
    new_value: Any


class Candidate(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    correlation_id: str
    timestamp: datetime = Field(default_factory=_utcnow)
    domain: ModificationDomain
    title: str
    description: str = ""
    ddl_statements: List[DDLStatement] = []
    config_deltas: List[ConfigDelta] = []
    predicted_improvement: Optional[float] = None
    predicted_risk: Optional[float] = None
    confidence_score: Optional[float] = None
    status: CandidateStatus = CandidateStatus.proposed
    rejection_reason: Optional[str] = None


class CorrectnessCriterion(str, Enum):
    result_set_equivalence = "result_set_equivalence"
    constraint_integrity = "constraint_integrity"
    transaction_isolation = "transaction_isolation"
    schema_validity = "schema_validity"


class PerformanceCriterion(str, Enum):
    p50_latency = "p50_latency"
    p95_latency = "p95_latency"
    p99_latency = "p99_latency"
    throughput = "throughput"
    cpu_usage = "cpu_usage"
    memory_usage = "memory_usage"
    storage_impact = "storage_impact"


class CriterionResult(BaseModel):
    criterion: str
    passed: bool
    baseline_value: Optional[float] = None
    candidate_value: Optional[float] = None
    delta_percent: Optional[float] = None
    threshold: Optional[float] = None
    details: Optional[str] = None


class ValidationReport(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    candidate_id: str
    correlation_id: str
    timestamp: datetime = Field(default_factory=_utcnow)
    passed: bool
    correctness_results: List[CriterionResult] = []
    performance_results: List[CriterionResult] = []
    twin_id: Optional[str] = None
    duration_seconds: float = 0.0
    details: Optional[str] = None


class DeploymentStrategy(str, Enum):
    blue_green = "blue_green"
    read_replica_first = "read_replica_first"
    canary = "canary"
    direct = "direct"


class DeploymentEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    candidate_id: str
    correlation_id: str
    timestamp: datetime = Field(default_factory=_utcnow)
    strategy: DeploymentStrategy
    status: str
    health_check_passed: Optional[bool] = None
    pre_deploy_snapshot_id: Optional[str] = None
    post_deploy_snapshot_id: Optional[str] = None
    duration_seconds: Optional[float] = None
    error: Optional[str] = None


class RollbackEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    candidate_id: str
    correlation_id: str
    timestamp: datetime = Field(default_factory=_utcnow)
    trigger_reason: str
    pre_rollback_metrics: Optional[ResourceMetrics] = None
    post_rollback_metrics: Optional[ResourceMetrics] = None
    duration_seconds: Optional[float] = None
    success: bool = True
    diagnostic_bundle: Optional[Dict[str, Any]] = None


class ConfigSnapshot(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=_utcnow)
    correlation_id: Optional[str] = None
    schema_ddl: Dict[str, str] = {}
    index_definitions: Dict[str, str] = {}
    partition_map: Dict[str, str] = {}
    compression_settings: Dict[str, str] = {}
    execution_config: Dict[str, Any] = {}
    workload_signature_id: Optional[str] = None


class PolicyRule(BaseModel):
    name: str
    enabled: bool = True
    rule_type: str
    config: Dict[str, Any] = {}
