import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class IncidentTimelineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    incident_id: uuid.UUID
    actor_user_id: uuid.UUID | None
    stage: str
    entry_type: str
    summary: str
    details_json: dict
    created_at: datetime


class IncidentEvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    incident_id: uuid.UUID
    evidence_type: str
    reference_id: str
    stance: str
    notes: str
    collected_at: datetime


class IncidentSummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    incident_code: str
    title: str
    description: str
    severity: str
    status: str
    environment: str
    assigned_to_id: uuid.UUID | None
    affected_service_ids: list[str]
    detected_at: datetime
    acknowledged_at: datetime | None
    resolved_at: datetime | None
    updated_at: datetime


class IncidentDetailRead(IncidentSummaryRead):
    postmortem_markdown: str | None
    timeline_entries: list[IncidentTimelineRead] = []
    evidence_items: list[IncidentEvidenceRead] = []


class IncidentCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(default="", max_length=4000)
    severity: str = Field(default="high", pattern="^(low|medium|high|critical)$")
    environment: str = Field(default="prod-sim", min_length=2, max_length=40)
    affected_service_ids: list[uuid.UUID] = Field(default_factory=list)
    assigned_to_id: uuid.UUID | None = None


class IncidentStatusUpdate(BaseModel):
    status: str = Field(min_length=3, max_length=50)
    severity: str | None = Field(default=None, pattern="^(low|medium|high|critical)$")
    note: str = Field(default="", max_length=1000)


class IncidentTimelineCreate(BaseModel):
    summary: str = Field(min_length=2, max_length=2000)
    stage: str | None = None
    details_json: dict = Field(default_factory=dict)


class IncidentEvidenceCreate(BaseModel):
    evidence_type: str = Field(pattern="^(log|metric|event|trace|deployment|note)$")
    reference_id: str = Field(min_length=1, max_length=140)
    stance: str = Field(default="supporting", pattern="^(supporting|contradicting|neutral)$")
    notes: str = Field(default="", max_length=2000)