import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth_rbac.models import AuditLog
from app.modules.incidents.models import (
    INCIDENT_STAGES,
    Incident,
    IncidentEvidence,
    IncidentTimeline,
)
from app.modules.incidents.schemas import (
    IncidentCreate,
    IncidentEvidenceCreate,
    IncidentStatusUpdate,
    IncidentTimelineCreate,
)


async def create_incident_record(
    db: AsyncSession,
    payload: IncidentCreate,
    actor_user_id: uuid.UUID,
) -> Incident:
    now = datetime.now(timezone.utc)
    code = f"INC-{uuid.uuid4().hex[:6].upper()}"
    service_ids_str = [str(sid) for sid in payload.affected_service_ids]

    incident = Incident(
        incident_code=code,
        title=payload.title.strip(),
        description=payload.description.strip(),
        severity=payload.severity,
        status="incident_created",
        environment=payload.environment,
        assigned_to_id=payload.assigned_to_id or actor_user_id,
        affected_service_ids=service_ids_str,
        detected_at=now,
    )
    db.add(incident)
    await db.flush()

    db.add(
        IncidentTimeline(
            incident_id=incident.id,
            actor_user_id=actor_user_id,
            stage="alert_detected",
            entry_type="lifecycle",
            summary="Simulated alert signal detected and correlated.",
            details_json={"environment": payload.environment, "simulated": True},
            created_at=now,
        )
    )
    db.add(
        IncidentTimeline(
            incident_id=incident.id,
            actor_user_id=actor_user_id,
            stage="incident_created",
            entry_type="lifecycle",
            summary=f"Incident {code} created with severity '{payload.severity}'.",
            details_json={"affected_service_ids": service_ids_str},
            created_at=now,
        )
    )
    db.add(
        AuditLog(
            actor_user_id=actor_user_id,
            action="incident.create",
            resource_type="incident",
            resource_id=str(incident.id),
            metadata_json={"incident_code": code, "severity": payload.severity},
        )
    )
    await db.commit()
    await db.refresh(incident)
    return incident


async def transition_incident_status(
    db: AsyncSession,
    incident: Incident,
    payload: IncidentStatusUpdate,
    actor_user_id: uuid.UUID,
) -> Incident:
    if payload.status not in INCIDENT_STAGES:
        raise ValueError(
            f"Invalid incident stage '{payload.status}'. "
            f"Must be one of: {', '.join(INCIDENT_STAGES)}"
        )

    now = datetime.now(timezone.utc)
    previous_status = incident.status
    incident.status = payload.status

    if payload.severity:
        incident.severity = payload.severity

    if payload.status == "incident_acknowledged" and incident.acknowledged_at is None:
        incident.acknowledged_at = now

    if payload.status == "incident_resolved" and incident.resolved_at is None:
        if incident.acknowledged_at is None:
            incident.acknowledged_at = now
        incident.resolved_at = now

    note_suffix = f" — {payload.note.strip()}" if payload.note.strip() else ""
    db.add(
        IncidentTimeline(
            incident_id=incident.id,
            actor_user_id=actor_user_id,
            stage=payload.status,
            entry_type="lifecycle",
            summary=f"Stage changed from '{previous_status}' to '{payload.status}'{note_suffix}.",
            details_json={
                "previous_status": previous_status,
                "new_status": payload.status,
                "severity": incident.severity,
            },
            created_at=now,
        )
    )
    db.add(
        AuditLog(
            actor_user_id=actor_user_id,
            action="incident.transition",
            resource_type="incident",
            resource_id=str(incident.id),
            metadata_json={"from": previous_status, "to": payload.status},
        )
    )
    await db.commit()
    await db.refresh(incident)
    return incident


async def add_timeline_note(
    db: AsyncSession,
    incident: Incident,
    payload: IncidentTimelineCreate,
    actor_user_id: uuid.UUID,
) -> IncidentTimeline:
    stage = payload.stage if payload.stage in INCIDENT_STAGES else incident.status
    entry = IncidentTimeline(
        incident_id=incident.id,
        actor_user_id=actor_user_id,
        stage=stage,
        entry_type="operator_note",
        summary=payload.summary.strip(),
        details_json=payload.details_json,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


async def link_incident_evidence(
    db: AsyncSession,
    incident: Incident,
    payload: IncidentEvidenceCreate,
    actor_user_id: uuid.UUID,
) -> IncidentEvidence:
    evidence = IncidentEvidence(
        incident_id=incident.id,
        evidence_type=payload.evidence_type,
        reference_id=payload.reference_id.strip(),
        stance=payload.stance,
        notes=payload.notes.strip(),
    )
    db.add(evidence)
    db.add(
        IncidentTimeline(
            incident_id=incident.id,
            actor_user_id=actor_user_id,
            stage=incident.status,
            entry_type="evidence_linked",
            summary=(
                f"Linked {payload.evidence_type} '{payload.reference_id.strip()}' "
                f"({payload.stance})."
            ),
            details_json={
                "evidence_type": payload.evidence_type,
                "reference_id": payload.reference_id.strip(),
                "stance": payload.stance,
            },
        )
    )
    await db.commit()
    await db.refresh(evidence)
    return evidence


async def generate_postmortem_report(
    db: AsyncSession,
    incident: Incident,
    actor_user_id: uuid.UUID,
) -> Incident:
    timeline_lines = [
        f"- [{t.created_at.isoformat()}] ({t.stage}) {t.summary}"
        for t in incident.timeline_entries
    ] or ["- No timeline entries recorded."]

    evidence_lines = [
        f"- [{e.stance.upper()}] {e.evidence_type}:{e.reference_id} — {e.notes or 'No notes'}"
        for e in incident.evidence_items
    ] or ["- No telemetry evidence explicitly linked."]

    ack_text = incident.acknowledged_at.isoformat() if incident.acknowledged_at else "Pending"
    res_text = incident.resolved_at.isoformat() if incident.resolved_at else "Open"

    report = (
        f"# Post-Incident Report: {incident.incident_code} — {incident.title}\n\n"
        f"**Environment:** {incident.environment} (Simulated)  \n"
        f"**Severity:** {incident.severity}  \n"
        f"**Current Lifecycle Stage:** {incident.status}  \n"
        f"**Detected At:** {incident.detected_at.isoformat()}  \n"
        f"**Acknowledged At:** {ack_text}  \n"
        f"**Resolved At:** {res_text}  \n\n"
        f"## Summary\n{incident.description or 'Simulated operational incident.'}\n\n"
        f"## Linked Evidence\n" + "\n".join(evidence_lines) + "\n\n"
        f"## Chronological Timeline\n" + "\n".join(timeline_lines) + "\n"
    )

    incident.postmortem_markdown = report
    if incident.status == "incident_resolved":
        incident.status = "postmortem_generated"

    db.add(
        IncidentTimeline(
            incident_id=incident.id,
            actor_user_id=actor_user_id,
            stage="postmortem_generated",
            entry_type="postmortem",
            summary=f"Generated post-incident report for {incident.incident_code}.",
            details_json={"incident_code": incident.incident_code},
        )
    )
    await db.commit()
    await db.refresh(incident)
    return incident


async def get_incident_or_none(db: AsyncSession, incident_id: uuid.UUID) -> Incident | None:
    res = await db.execute(select(Incident).where(Incident.id == incident_id))
    return res.scalar_one_or_none()