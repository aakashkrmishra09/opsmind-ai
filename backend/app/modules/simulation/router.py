import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth_rbac.dependencies import get_current_user, require_roles
from app.modules.auth_rbac.models import User
from app.modules.simulation.engine import SCENARIOS, apply_scenario_action
from app.modules.simulation.models import (
    Deployment,
    Service,
    ServiceDependency,
    TelemetryEvent,
    TelemetryLog,
    TelemetryMetric,
    TelemetryTrace,
)
from app.modules.simulation.schemas import (
    DependencyEdgeRead,
    DeploymentRead,
    ScenarioInfo,
    ServiceRead,
    TelemetryEventRead,
    TelemetryLogRead,
    TelemetryMetricRead,
    TelemetryTraceRead,
    TopologyResponse,
)

router = APIRouter(tags=["Simulation & Observability"])


@router.get("/services", response_model=list[ServiceRead])
async def list_services(
    environment: str | None = None,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Service]:
    stmt = select(Service).order_by(Service.name.asc())
    if environment:
        stmt = stmt.where(Service.environment == environment)
    return list((await db.execute(stmt)).scalars().all())


@router.get("/services/{service_id}", response_model=ServiceRead)
async def get_service(
    service_id: uuid.UUID,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Service:
    svc = (await db.execute(select(Service).where(Service.id == service_id))).scalar_one_or_none()
    if svc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    return svc


@router.get("/services/{service_id}/dependencies", response_model=list[DependencyEdgeRead])
async def get_service_dependencies(
    service_id: uuid.UUID,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ServiceDependency]:
    stmt = select(ServiceDependency).where(
        (ServiceDependency.source_service_id == service_id)
        | (ServiceDependency.target_service_id == service_id)
    )
    return list((await db.execute(stmt)).scalars().all())


@router.get("/infrastructure/topology", response_model=TopologyResponse)
async def get_topology(
    environment: str | None = None,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TopologyResponse:
    stmt = select(Service).order_by(Service.name.asc())
    if environment:
        stmt = stmt.where(Service.environment == environment)
    services = list((await db.execute(stmt)).scalars().all())
    deps = list((await db.execute(select(ServiceDependency))).scalars().all())
    return TopologyResponse(simulated=True, services=services, dependencies=deps)


@router.get("/deployments", response_model=list[DeploymentRead])
async def list_deployments(
    environment: str | None = None,
    service_id: uuid.UUID | None = None,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Deployment]:
    stmt = select(Deployment).order_by(Deployment.deployed_at.desc())
    if environment:
        stmt = stmt.where(Deployment.environment == environment)
    if service_id:
        stmt = stmt.where(Deployment.service_id == service_id)
    return list((await db.execute(stmt)).scalars().all())


@router.get("/simulation/scenarios", response_model=list[ScenarioInfo])
async def list_scenarios(
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ScenarioInfo]:
    services = list((await db.execute(select(Service))).scalars().all())
    items: list[ScenarioInfo] = []
    for key, sc in SCENARIOS.items():
        active_names = [s.name for s in services if s.active_scenario == key and not s.scenario_paused]
        paused_names = [s.name for s in services if s.active_scenario == key and s.scenario_paused]
        items.append(
            ScenarioInfo(
                key=sc.key,
                name=sc.name,
                target_service=sc.target_service,
                default_severity=sc.default_severity,
                description=sc.description,
                active_on_services=active_names,
                paused_on_services=paused_names,
            )
        )
    return items


@router.post("/simulation/scenarios/{scenario_key}/{action}", response_model=ServiceRead)
async def run_scenario_action(
    scenario_key: str,
    action: str,
    current_user: User = Depends(require_roles("Admin", "Operations Engineer")),
    db: AsyncSession = Depends(get_db),
) -> Service:
    try:
        return await apply_scenario_action(db, scenario_key, action, actor_user_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/telemetry/logs", response_model=list[TelemetryLogRead])
async def query_logs(
    service_id: uuid.UUID | None = None,
    environment: str | None = None,
    severity: str | None = None,
    correlation_id: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[TelemetryLog]:
    stmt = select(TelemetryLog).order_by(TelemetryLog.recorded_at.desc()).limit(limit)
    if service_id:
        stmt = stmt.where(TelemetryLog.service_id == service_id)
    if environment:
        stmt = stmt.where(TelemetryLog.environment == environment)
    if severity:
        stmt = stmt.where(TelemetryLog.severity == severity.upper())
    if correlation_id:
        stmt = stmt.where(TelemetryLog.correlation_id == correlation_id)
    if start_time:
        stmt = stmt.where(TelemetryLog.recorded_at >= start_time)
    if end_time:
        stmt = stmt.where(TelemetryLog.recorded_at <= end_time)
    return list((await db.execute(stmt)).scalars().all())


@router.get("/telemetry/metrics", response_model=list[TelemetryMetricRead])
async def query_metrics(
    service_id: uuid.UUID | None = None,
    environment: str | None = None,
    correlation_id: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = Query(default=200, ge=1, le=1000),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[TelemetryMetric]:
    stmt = select(TelemetryMetric).order_by(TelemetryMetric.recorded_at.desc()).limit(limit)
    if service_id:
        stmt = stmt.where(TelemetryMetric.service_id == service_id)
    if environment:
        stmt = stmt.where(TelemetryMetric.environment == environment)
    if correlation_id:
        stmt = stmt.where(TelemetryMetric.correlation_id == correlation_id)
    if start_time:
        stmt = stmt.where(TelemetryMetric.recorded_at >= start_time)
    if end_time:
        stmt = stmt.where(TelemetryMetric.recorded_at <= end_time)
    return list((await db.execute(stmt)).scalars().all())


@router.get("/telemetry/events", response_model=list[TelemetryEventRead])
async def query_events(
    service_id: uuid.UUID | None = None,
    environment: str | None = None,
    severity: str | None = None,
    correlation_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[TelemetryEvent]:
    stmt = select(TelemetryEvent).order_by(TelemetryEvent.recorded_at.desc()).limit(limit)
    if service_id:
        stmt = stmt.where(TelemetryEvent.service_id == service_id)
    if environment:
        stmt = stmt.where(TelemetryEvent.environment == environment)
    if severity:
        stmt = stmt.where(TelemetryEvent.severity == severity.upper())
    if correlation_id:
        stmt = stmt.where(TelemetryEvent.correlation_id == correlation_id)
    return list((await db.execute(stmt)).scalars().all())


@router.get("/telemetry/traces", response_model=list[TelemetryTraceRead])
async def query_traces(
    service_id: uuid.UUID | None = None,
    environment: str | None = None,
    correlation_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[TelemetryTrace]:
    stmt = select(TelemetryTrace).order_by(TelemetryTrace.recorded_at.desc()).limit(limit)
    if service_id:
        stmt = stmt.where(TelemetryTrace.service_id == service_id)
    if environment:
        stmt = stmt.where(TelemetryTrace.environment == environment)
    if correlation_id:
        stmt = stmt.where(TelemetryTrace.correlation_id == correlation_id)
    return list((await db.execute(stmt)).scalars().all())