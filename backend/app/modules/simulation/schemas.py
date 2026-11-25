import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ResourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    service_id: uuid.UUID
    resource_type: str
    name: str
    environment: str
    status: str
    specs_json: dict
    updated_at: datetime


class DeploymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    service_id: uuid.UUID
    environment: str
    version: str
    status: str
    triggered_by: str
    deployed_at: datetime


class ServiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str
    environment: str
    status: str
    availability_pct: float
    cpu_pct: float
    memory_pct: float
    request_rate_rps: float
    error_rate_pct: float
    latency_p95_ms: float
    active_scenario: str | None
    scenario_paused: bool
    updated_at: datetime
    resources: list[ResourceRead] = []


class DependencyEdgeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_service_id: uuid.UUID
    target_service_id: uuid.UUID
    dependency_type: str
    is_critical: bool


class TopologyResponse(BaseModel):
    simulated: bool = True
    services: list[ServiceRead]
    dependencies: list[DependencyEdgeRead]


class ScenarioInfo(BaseModel):
    key: str
    name: str
    target_service: str
    default_severity: str
    description: str
    active_on_services: list[str]
    paused_on_services: list[str]


class TelemetryLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    service_id: uuid.UUID
    environment: str
    severity: str
    correlation_id: str
    message: str
    metadata_json: dict
    recorded_at: datetime


class TelemetryMetricRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    service_id: uuid.UUID
    environment: str
    metric_name: str
    metric_value: float
    unit: str
    correlation_id: str
    recorded_at: datetime


class TelemetryEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    service_id: uuid.UUID
    environment: str
    event_type: str
    severity: str
    correlation_id: str
    summary: str
    payload_json: dict
    recorded_at: datetime


class TelemetryTraceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    trace_id: str
    span_id: str
    parent_span_id: str | None
    service_id: uuid.UUID
    environment: str
    correlation_id: str
    operation_name: str
    duration_ms: float
    status_code: str
    http_status: int
    recorded_at: datetime