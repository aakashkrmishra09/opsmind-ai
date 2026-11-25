import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth_rbac.dependencies import get_current_user, require_roles
from app.modules.auth_rbac.models import User
from app.modules.incidents.models import INCIDENT_STAGES, Incident, IncidentEvidence, IncidentTimeline
from app.modules.incidents.schemas import (
    IncidentCreate,
    IncidentDetailRead,
    IncidentEvidenceCreate,
    IncidentEvidenceRead,
    IncidentStatusUpdate,
    IncidentSummaryRead,
    IncidentTimelineCreate,
    IncidentTimelineRead,
)
from app.modules.incidents.service import (
    add_timeline_note,
    create_incident_record,
    generate_postmortem_report,
    get_incident_or_none,
    link_incident_evidence,
    transition_incident_status,
)

router = APIRouter(tags=["Incidents"])


@router.get("/incidents/stages", response_model=list[str])
async def list_incident_stages(_: User = Depends(get_current_user)) -> list[str]:
    return INCIDENT_STAGES


@router.get("/incidents", response_model=list[IncidentSummaryRead])
async def list_incidents(
    environment: str | None = None,
    severity: str | None = None,
    status_filter: str | None = None,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Incident]:
    stmt = select(Incident).order_by(Incident.detected_at.desc())
    if environment:
        stmt = stmt.where(Incident.environment == environment)
    if severity:
        stmt = stmt.where(Incident.severity == severity)
    if status_filter:
        stmt = stmt.where(Incident.status == status_filter)
    return list((await db.execute(stmt)).scalars().all())


@router.post("/incidents", response_model=IncidentDetailRead, status_code=status.HTTP_201_CREATED)
async def create_incident(
    payload: IncidentCreate,
    current_user: User = Depends(require_roles("Admin", "Operations Engineer")),
    db: AsyncSession = Depends(get_db),
) -> Incident:
    return await create_incident_record(db, payload, actor_user_id=current_user.id)


@router.get("/incidents/{incident_id}", response_model=IncidentDetailRead)
async def get_incident_detail(
    incident_id: uuid.UUID,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Incident:
    incident = await get_incident_or_none(db, incident_id)
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    return incident


@router.patch("/incidents/{incident_id}/status", response_model=IncidentDetailRead)
async def update_incident_status(
    incident_id: uuid.UUID,
    payload: IncidentStatusUpdate,
    current_user: User = Depends(require_roles("Admin", "Operations Engineer")),
    db: AsyncSession = Depends(get_db),
) -> Incident:
    incident = await get_incident_or_none(db, incident_id)
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    try:
        return await transition_incident_status(db, incident, payload, actor_user_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post(
    "/incidents/{incident_id}/timeline",
    response_model=IncidentTimelineRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_incident_timeline_entry(
    incident_id: uuid.UUID,
    payload: IncidentTimelineCreate,
    current_user: User = Depends(require_roles("Admin", "Operations Engineer")),
    db: AsyncSession = Depends(get_db),
) -> IncidentTimeline:
    incident = await get_incident_or_none(db, incident_id)
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    return await add_timeline_note(db, incident, payload, actor_user_id=current_user.id)


@router.post(
    "/incidents/{incident_id}/evidence",
    response_model=IncidentEvidenceRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_incident_evidence(
    incident_id: uuid.UUID,
    payload: IncidentEvidenceCreate,
    current_user: User = Depends(require_roles("Admin", "Operations Engineer")),
    db: AsyncSession = Depends(get_db),
) -> IncidentEvidence:
    incident = await get_incident_or_none(db, incident_id)
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    return await link_incident_evidence(db, incident, payload, actor_user_id=current_user.id)


@router.post("/incidents/{incident_id}/postmortem", response_model=IncidentDetailRead)
async def create_incident_postmortem(
    incident_id: uuid.UUID,
    current_user: User = Depends(require_roles("Admin", "Operations Engineer")),
    db: AsyncSession = Depends(get_db),
) -> Incident:
    incident = await get_incident_or_none(db, incident_id)
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    return await generate_postmortem_report(db, incident, actor_user_id=current_user.id)