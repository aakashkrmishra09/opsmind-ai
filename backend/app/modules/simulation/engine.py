import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth_rbac.models import AuditLog
from app.modules.simulation.models import (
    Deployment,
    InfrastructureResource,
    Service,
    ServiceDependency,
    TelemetryEvent,
    TelemetryLog,
    TelemetryMetric,
    TelemetryTrace,
)


@dataclass(frozen=True)
class ScenarioDefinition:
    key: str
    name: str
    target_service: str
    default_severity: str
    description: str


SCENARIOS: dict[str, ScenarioDefinition] = {
    "db_connection_exhaustion": ScenarioDefinition(
        key="db_connection_exhaustion",
        name="Database Connection Exhaustion",
        target_service="primary-postgres",
        default_severity="critical",
        description="Simulates saturated connection pool slots causing checkout timeouts.",
    ),
    "high_cpu": ScenarioDefinition(
        key="high_cpu",
        name="High CPU Utilization",
        target_service="order-api",
        default_severity="high",
        description="Simulates CPU saturation from unthrottled serialization loops.",
    ),
    "memory_leak": ScenarioDefinition(
        key="memory_leak",
        name="Memory Leak",
        target_service="payment-worker",
        default_severity="high",
        description="Simulates steady heap growth and GC thrashing in payment workers.",
    ),
    "api_latency_spike": ScenarioDefinition(
        key="api_latency_spike",
        name="API Latency Increase",
        target_service="order-api",
        default_severity="high",
        description="Simulates elevated p95 response latency on order endpoints.",
    ),
    "failed_deployment": ScenarioDefinition(
        key="failed_deployment",
        name="Failed Deployment",
        target_service="auth-service",
        default_severity="critical",
        description="Simulates a bad release rolling out with elevated 5xx error rates.",
    ),
    "queue_backlog": ScenarioDefinition(
        key="queue_backlog",
        name="Queue Backlog",
        target_service="inventory-queue",
        default_severity="high",
        description="Simulates consumer lag and growing message queue depth.",
    ),
    "service_dependency_failure": ScenarioDefinition(
        key="service_dependency_failure",
        name="Service Dependency Failure",
        target_service="payment-worker",
        default_severity="critical",
        description="Simulates downstream dependency timeout propagation across services.",
    ),
    "db_unavailable": ScenarioDefinition(
        key="db_unavailable",
        name="Database Unavailable",
        target_service="primary-postgres",
        default_severity="critical",
        description="Simulates simulated primary database failover/unavailability.",
    ),
}

BASELINE_SERVICES = [
    {
        "name": "order-api",
        "description": "Simulates customer order intake and REST gateway endpoints.",
        "environment": "prod-sim",
        "cpu_pct": 28.0,
        "memory_pct": 44.0,
        "request_rate_rps": 240.0,
        "error_rate_pct": 0.15,
        "latency_p95_ms": 92.0,
        "availability_pct": 99.95,
        "resources": [
            ("vm", "vm-order-api-01", {"vcpu": 4, "ram_gb": 16, "region": "ca-central-sim-1a"}),
            ("container", "ctr-order-api-pod1", {"image": "opsmind/order-api:1.4.2"}),
            ("api", "gw-order-rest", {"protocol": "HTTPS", "port": 8080}),
        ],
    },
    {
        "name": "auth-service",
        "description": "Simulates identity token validation and session management.",
        "environment": "prod-sim",
        "cpu_pct": 19.0,
        "memory_pct": 36.0,
        "request_rate_rps": 310.0,
        "error_rate_pct": 0.08,
        "latency_p95_ms": 48.0,
        "availability_pct": 99.98,
        "resources": [
            ("container", "ctr-auth-service-pod1", {"image": "opsmind/auth-service:2.1.0"}),
            ("network", "vnet-identity-sim", {"cidr": "10.20.1.0/24"}),
        ],
    },
    {
        "name": "payment-worker",
        "description": "Simulates asynchronous payment settlement workers.",
        "environment": "prod-sim",
        "cpu_pct": 31.0,
        "memory_pct": 49.0,
        "request_rate_rps": 95.0,
        "error_rate_pct": 0.12,
        "latency_p95_ms": 130.0,
        "availability_pct": 99.92,
        "resources": [
            ("vm", "vm-payment-worker-01", {"vcpu": 4, "ram_gb": 16, "region": "ca-central-sim-1b"}),
            ("container", "ctr-payment-worker-01", {"image": "opsmind/payment-worker:1.8.0"}),
        ],
    },
    {
        "name": "inventory-queue",
        "description": "Simulates message broker queue for stock reservation events.",
        "environment": "staging",
        "cpu_pct": 22.0,
        "memory_pct": 40.0,
        "request_rate_rps": 180.0,
        "error_rate_pct": 0.05,
        "latency_p95_ms": 35.0,
        "availability_pct": 99.96,
        "resources": [
            ("queue", "q-inventory-reservations", {"partitions": 6, "retention_hours": 72}),
            ("container", "ctr-inventory-broker-01", {"image": "opsmind/queue-broker:3.2.1"}),
        ],
    },
    {
        "name": "primary-postgres",
        "description": "Simulates primary transactional relational database cluster.",
        "environment": "prod-sim",
        "cpu_pct": 26.0,
        "memory_pct": 54.0,
        "request_rate_rps": 420.0,
        "error_rate_pct": 0.04,
        "latency_p95_ms": 22.0,
        "availability_pct": 99.99,
        "resources": [
            ("database", "pg-sim-primary-01", {"engine": "PostgreSQL-Sim", "max_connections": 200}),
            ("vm", "vm-db-node-01", {"vcpu": 8, "ram_gb": 32, "region": "ca-central-sim-1a"}),
        ],
    },
    {
        "name": "redis-cache",
        "description": "Simulates low-latency session and rate-limit cache node.",
        "environment": "dev",
        "cpu_pct": 14.0,
        "memory_pct": 31.0,
        "request_rate_rps": 510.0,
        "error_rate_pct": 0.02,
        "latency_p95_ms": 11.0,
        "availability_pct": 99.97,
        "resources": [
            ("container", "ctr-redis-sim-01", {"image": "opsmind/cache-sim:7.2"}),
            ("network", "vnet-cache-sim", {"cidr": "10.20.4.0/24"}),
        ],
    },
]


async def seed_simulation_data(db: AsyncSession) -> None:
    existing_services = list((await db.execute(select(Service))).scalars().all())
    by_name = {svc.name: svc for svc in existing_services}

    for item in BASELINE_SERVICES:
        if item["name"] in by_name:
            continue
        svc = Service(
            name=item["name"],
            description=item["description"],
            environment=item["environment"],
            status="healthy",
            availability_pct=item["availability_pct"],
            cpu_pct=item["cpu_pct"],
            memory_pct=item["memory_pct"],
            request_rate_rps=item["request_rate_rps"],
            error_rate_pct=item["error_rate_pct"],
            latency_p95_ms=item["latency_p95_ms"],
        )
        db.add(svc)
        await db.flush()
        by_name[svc.name] = svc

        for res_type, res_name, specs in item["resources"]:
            db.add(
                InfrastructureResource(
                    service_id=svc.id,
                    resource_type=res_type,
                    name=res_name,
                    environment=svc.environment,
                    status="healthy",
                    specs_json=specs,
                )
            )

        db.add(
            Deployment(
                service_id=svc.id,
                environment=svc.environment,
                version="v1.4.2-sim",
                status="succeeded",
                triggered_by="github-actions-sim",
                deployed_at=datetime.now(timezone.utc) - timedelta(hours=3),
            )
        )

    await db.flush()

    existing_deps = list((await db.execute(select(ServiceDependency))).scalars().all())
    if not existing_deps and len(by_name) >= 5:
        edges = [
            ("order-api", "auth-service", "http", True),
            ("order-api", "primary-postgres", "sql", True),
            ("order-api", "inventory-queue", "queue", False),
            ("payment-worker", "primary-postgres", "sql", True),
            ("payment-worker", "redis-cache", "cache", False),
        ]
        for src_name, dst_name, dep_type, critical in edges:
            if src_name in by_name and dst_name in by_name:
                db.add(
                    ServiceDependency(
                        source_service_id=by_name[src_name].id,
                        target_service_id=by_name[dst_name].id,
                        dependency_type=dep_type,
                        is_critical=critical,
                    )
                )

    existing_logs = (await db.execute(select(TelemetryLog.id).limit(1))).first()
    if existing_logs is None:
        now = datetime.now(timezone.utc)
        for svc in by_name.values():
            corr_id = f"corr-init-{svc.name}"
            db.add(
                TelemetryLog(
                    service_id=svc.id,
                    environment=svc.environment,
                    severity="INFO",
                    correlation_id=corr_id,
                    message=f"[SIMULATED] Baseline heartbeat healthy for {svc.name}",
                    metadata_json={"simulated": True, "rps": svc.request_rate_rps},
                    recorded_at=now - timedelta(minutes=5),
                )
            )
            db.add(
                TelemetryMetric(
                    service_id=svc.id,
                    environment=svc.environment,
                    metric_name="cpu_utilization_pct",
                    metric_value=svc.cpu_pct,
                    unit="percent",
                    correlation_id=corr_id,
                    recorded_at=now - timedelta(minutes=5),
                )
            )
            db.add(
                TelemetryMetric(
                    service_id=svc.id,
                    environment=svc.environment,
                    metric_name="latency_p95_ms",
                    metric_value=svc.latency_p95_ms,
                    unit="ms",
                    correlation_id=corr_id,
                    recorded_at=now - timedelta(minutes=5),
                )
            )
            db.add(
                TelemetryEvent(
                    service_id=svc.id,
                    environment=svc.environment,
                    event_type="health_check",
                    severity="INFO",
                    correlation_id=corr_id,
                    summary=f"[SIMULATED] {svc.name} passed baseline health check",
                    payload_json={"simulated": True, "status": svc.status},
                    recorded_at=now - timedelta(minutes=5),
                )
            )
            db.add(
                TelemetryTrace(
                    trace_id=f"trace-{svc.name}-001",
                    span_id=f"span-{svc.name}-root",
                    parent_span_id=None,
                    service_id=svc.id,
                    environment=svc.environment,
                    correlation_id=corr_id,
                    operation_name=f"{svc.name}.health_probe",
                    duration_ms=svc.latency_p95_ms,
                    status_code="OK",
                    http_status=200,
                    recorded_at=now - timedelta(minutes=5),
                )
            )

    await db.commit()


async def _record_scenario_telemetry(
    db: AsyncSession,
    service: Service,
    scenario_key: str,
    action: str,
    correlation_id: str,
) -> None:
    now = datetime.now(timezone.utc)
    severity = "INFO" if action in ("reset", "paused") else "ERROR"
    msg = (
        f"[SIMULATED] Scenario '{scenario_key}' {action} on {service.name} "
        f"(cpu={service.cpu_pct:.1f}%, mem={service.memory_pct:.1f}%, "
        f"p95={service.latency_p95_ms:.1f}ms, err={service.error_rate_pct:.2f}%)"
    )

    db.add(
        TelemetryLog(
            service_id=service.id,
            environment=service.environment,
            severity=severity,
            correlation_id=correlation_id,
            message=msg,
            metadata_json={
                "simulated": True,
                "scenario": scenario_key,
                "action": action,
                "service_status": service.status,
            },
            recorded_at=now,
        )
    )
    db.add(
        TelemetryMetric(
            service_id=service.id,
            environment=service.environment,
            metric_name="cpu_utilization_pct",
            metric_value=service.cpu_pct,
            unit="percent",
            correlation_id=correlation_id,
            recorded_at=now,
        )
    )
    db.add(
        TelemetryMetric(
            service_id=service.id,
            environment=service.environment,
            metric_name="latency_p95_ms",
            metric_value=service.latency_p95_ms,
            unit="ms",
            correlation_id=correlation_id,
            recorded_at=now,
        )
    )
    db.add(
        TelemetryEvent(
            service_id=service.id,
            environment=service.environment,
            event_type=f"simulation.{action}",
            severity=severity,
            correlation_id=correlation_id,
            summary=msg,
            payload_json={
                "simulated": True,
                "scenario": scenario_key,
                "action": action,
                "status": service.status,
            },
            recorded_at=now,
        )
    )
    db.add(
        TelemetryTrace(
            trace_id=f"trace-{uuid.uuid4().hex[:12]}",
            span_id=f"span-{uuid.uuid4().hex[:8]}",
            parent_span_id=None,
            service_id=service.id,
            environment=service.environment,
            correlation_id=correlation_id,
            operation_name=f"{service.name}.{scenario_key}.{action}",
            duration_ms=service.latency_p95_ms,
            status_code="ERROR" if service.status != "healthy" else "OK",
            http_status=503 if service.status == "unavailable" else (500 if service.error_rate_pct > 5 else 200),
            recorded_at=now,
        )
    )


async def apply_scenario_action(
    db: AsyncSession,
    scenario_key: str,
    action: str,
    actor_user_id: uuid.UUID | None = None,
) -> Service:
    if scenario_key not in SCENARIOS:
        raise ValueError(f"Unknown simulation scenario: {scenario_key}")
    if action not in ("trigger", "pause", "reset"):
        raise ValueError(f"Unsupported simulation action: {action}")

    scenario = SCENARIOS[scenario_key]
    res = await db.execute(select(Service).where(Service.name == scenario.target_service))
    service = res.scalar_one_or_none()
    if service is None:
        raise LookupError(f"Target service '{scenario.target_service}' not found")

    baseline = next((b for b in BASELINE_SERVICES if b["name"] == service.name), None)
    corr_id = f"corr-{scenario_key}-{uuid.uuid4().hex[:8]}"

    if action == "trigger":
        service.active_scenario = scenario_key
        service.scenario_paused = False

        if scenario_key == "db_connection_exhaustion":
            service.status = "degraded"
            service.error_rate_pct = 14.5
            service.latency_p95_ms = 1450.0
            service.availability_pct = 96.4
        elif scenario_key == "high_cpu":
            service.status = "degraded"
            service.cpu_pct = 94.0
            service.latency_p95_ms = 680.0
            service.availability_pct = 98.1
        elif scenario_key == "memory_leak":
            service.status = "degraded"
            service.memory_pct = 93.5
            service.error_rate_pct = 6.2
            service.availability_pct = 97.8
        elif scenario_key == "api_latency_spike":
            service.status = "degraded"
            service.latency_p95_ms = 2150.0
            service.error_rate_pct = 4.8
            service.availability_pct = 98.2
        elif scenario_key == "failed_deployment":
            service.status = "unavailable"
            service.error_rate_pct = 38.0
            service.latency_p95_ms = 1200.0
            service.availability_pct = 91.5
            db.add(
                Deployment(
                    service_id=service.id,
                    environment=service.environment,
                    version="v2.2.0-rc1-sim",
                    status="failed",
                    triggered_by="simulated-release",
                )
            )
        elif scenario_key == "queue_backlog":
            service.status = "degraded"
            service.memory_pct = 84.0
            service.latency_p95_ms = 940.0
            service.availability_pct = 97.5
        elif scenario_key == "service_dependency_failure":
            service.status = "degraded"
            service.error_rate_pct = 19.0
            service.latency_p95_ms = 1720.0
            service.availability_pct = 95.8
        elif scenario_key == "db_unavailable":
            service.status = "unavailable"
            service.error_rate_pct = 100.0
            service.request_rate_rps = 0.0
            service.latency_p95_ms = 5000.0
            service.availability_pct = 85.0

    elif action == "pause":
        service.scenario_paused = True

    elif action == "reset":
        service.active_scenario = None
        service.scenario_paused = False
        service.status = "healthy"
        if baseline:
            service.cpu_pct = baseline["cpu_pct"]
            service.memory_pct = baseline["memory_pct"]
            service.request_rate_rps = baseline["request_rate_rps"]
            service.error_rate_pct = baseline["error_rate_pct"]
            service.latency_p95_ms = baseline["latency_p95_ms"]
            service.availability_pct = baseline["availability_pct"]

    await _record_scenario_telemetry(db, service, scenario_key, action, corr_id)
    db.add(
        AuditLog(
            actor_user_id=actor_user_id,
            action=f"simulation.scenario.{action}",
            resource_type="service",
            resource_id=str(service.id),
            correlation_id=corr_id,
            metadata_json={"simulated": True, "scenario_key": scenario_key, "service": service.name},
        )
    )
    await db.commit()
    await db.refresh(service)
    return service