import uuid
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth_rbac.dependencies import get_current_user
from app.modules.auth_rbac.models import User
from app.modules.incidents.models import Incident
from app.modules.simulation.models import Deployment, Service, TelemetryEvent, TelemetryMetric
from app.modules.simulation.schemas import DeploymentRead, TelemetryEventRead

router = APIRouter(tags=["Dashboard"])


class MetricFormula(BaseModel):
    metric: str
    formula: str
    unit: str


class DashboardSummaryResponse(BaseModel):
    simulated: bool = True
    time_range: str
    environment: str | None
    total_monitored_services: int
    healthy_services: int
    degraded_services: int
    unavailable_services: int
    active_incidents: int
    critical_high_incidents: int
    mtta_minutes: float | None
    mttr_minutes: float | None
    incident_frequency_per_day: float
    service_availability_pct: float
    recent_deployments: list[DeploymentRead]
    recent_alerts: list[TelemetryEventRead]
    metric_series: list[dict]
    formulas: list[MetricFormula]


def _parse_window(time_range: str) -> timedelta:
    mapping = {
        "15m": timedelta(minutes=15),
        "1h": timedelta(hours=1),
        "6h": timedelta(hours=6),
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
    }
    return mapping.get(time_range, timedelta(hours=24))


@router.get("/dashboard/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    time_range: str = Query(default="24h"),
    environment: str | None = Query(default=None),
    service_id: uuid.UUID | None = Query(default=None),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardSummaryResponse:
    window = _parse_window(time_range)
    cutoff = datetime.now(timezone.utc) - window

    svc_stmt = select(Service).order_by(Service.name.asc())
    if environment:
        svc_stmt = svc_stmt.where(Service.environment == environment)
    if service_id:
        svc_stmt = svc_stmt.where(Service.id == service_id)
    services = list((await db.execute(svc_stmt)).scalars().all())

    total_services = len(services)
    healthy_count = sum(1 for s in services if s.status == "healthy")
    degraded_count = sum(1 for s in services if s.status == "degraded")
    unavailable_count = sum(1 for s in services if s.status == "unavailable")

    inc_stmt = select(Incident).where(Incident.detected_at >= cutoff)
    if environment:
        inc_stmt = inc_stmt.where(Incident.environment == environment)
    incidents = list((await db.execute(inc_stmt)).scalars().all())

    open_incidents = [
        i for i in incidents if i.status not in {"incident_resolved", "postmortem_generated"}
    ]
    active_sim_services = [s for s in services if s.active_scenario is not None]
    active_incidents = max(len(open_incidents), len(active_sim_services))
    critical_high_incidents = sum(
        1 for i in open_incidents if i.severity in {"critical", "high"}
    ) or len(active_sim_services)

    ack_durations = [
        (i.acknowledged_at - i.detected_at).total_seconds() / 60.0
        for i in incidents
        if i.acknowledged_at is not None and i.acknowledged_at >= i.detected_at
    ]
    res_durations = [
        (i.resolved_at - i.detected_at).total_seconds() / 60.0
        for i in incidents
        if i.resolved_at is not None and i.resolved_at >= i.detected_at
    ]

    mtta_minutes = round(sum(ack_durations) / len(ack_durations), 2) if ack_durations else None
    mttr_minutes = round(sum(res_durations) / len(res_durations), 2) if res_durations else None

    avg_availability = (
        round(sum(s.availability_pct for s in services) / total_services, 2)
        if total_services > 0
        else 100.0
    )

    days = max(window.total_seconds() / 86400.0, 1.0 / 24.0)
    incident_freq = round(max(len(incidents), active_incidents) / days, 2)

    dep_stmt = (
        select(Deployment)
        .where(Deployment.deployed_at >= cutoff)
        .order_by(Deployment.deployed_at.desc())
        .limit(8)
    )
    if environment:
        dep_stmt = dep_stmt.where(Deployment.environment == environment)
    if service_id:
        dep_stmt = dep_stmt.where(Deployment.service_id == service_id)
    recent_deployments = list((await db.execute(dep_stmt)).scalars().all())

    alert_stmt = (
        select(TelemetryEvent)
        .where(TelemetryEvent.recorded_at >= cutoff)
        .order_by(TelemetryEvent.recorded_at.desc())
        .limit(10)
    )
    if environment:
        alert_stmt = alert_stmt.where(TelemetryEvent.environment == environment)
    if service_id:
        alert_stmt = alert_stmt.where(TelemetryEvent.service_id == service_id)
    recent_alerts = list((await db.execute(alert_stmt)).scalars().all())

    metric_stmt = (
        select(TelemetryMetric)
        .where(TelemetryMetric.recorded_at >= cutoff)
        .order_by(TelemetryMetric.recorded_at.asc())
        .limit(60)
    )
    if environment:
        metric_stmt = metric_stmt.where(TelemetryMetric.environment == environment)
    if service_id:
        metric_stmt = metric_stmt.where(TelemetryMetric.service_id == service_id)
    metrics = list((await db.execute(metric_stmt)).scalars().all())

    series_by_bucket: dict[str, dict] = {}
    for m in metrics:
        label = m.recorded_at.strftime("%H:%M:%S")
        row = series_by_bucket.setdefault(
            label, {"time": label, "cpu_pct": None, "latency_p95_ms": None}
        )
        if m.metric_name == "cpu_utilization_pct":
            row["cpu_pct"] = round(m.metric_value, 1)
        elif m.metric_name == "latency_p95_ms":
            row["latency_p95_ms"] = round(m.metric_value, 1)

    formulas = [
        MetricFormula(
            metric="Service Availability",
            formula="mean(service.availability_pct) across filtered simulated services",
            unit="%",
        ),
        MetricFormula(
            metric="Active Incidents",
            formula="max(count(unresolved incidents in window), count(active fault scenarios))",
            unit="count",
        ),
        MetricFormula(
            metric="Incident Frequency",
            formula="incidents_in_window / max(window_hours / 24, 1/24)",
            unit="incidents/day",
        ),
        MetricFormula(
            metric="MTTA / MTTR",
            formula="mean(acknowledged_at - detected_at) / mean(resolved_at - detected_at)",
            unit="minutes",
        ),
    ]

    return DashboardSummaryResponse(
        simulated=True,
        time_range=time_range,
        environment=environment,
        total_monitored_services=total_services,
        healthy_services=healthy_count,
        degraded_services=degraded_count,
        unavailable_services=unavailable_count,
        active_incidents=active_incidents,
        critical_high_incidents=critical_high_incidents,
        mtta_minutes=mtta_minutes,
        mttr_minutes=mttr_minutes,
        incident_frequency_per_day=incident_freq,
        service_availability_pct=avg_availability,
        recent_deployments=recent_deployments,
        recent_alerts=recent_alerts,
        metric_series=list(series_by_bucket.values()),
        formulas=formulas,
    )