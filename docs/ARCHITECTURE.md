# OpsMind AI Architecture

## Overview
OpsMind AI uses a **modular monolith** backend (FastAPI + SQLAlchemy + Pydantic) paired with a **React + TypeScript** frontend, **PostgreSQL (`pgvector`)**, and **Redis**.

## Planned Backend Modules (`backend/app/modules`)
- `auth_rbac`: Authentication, JWT/session handling, role enforcement (`Admin`, `Operations Engineer`, `Viewer`), and secret redaction.
- `simulation`: Simulated topology and fault scenario runner (trigger, pause, reset).
- `observability`: Logs, metrics, events, and traces ingestion, filtering, and dashboard metric queries.
- `incidents`: Incident lifecycle transitions, timelines, evidence links, and postmortems.
- `ai_engine`: Structured investigation generator separating facts, hypotheses, evidence, and approval requirements.
- `rag_kb`: Document ingestion, chunking, embedding provider abstraction with fallback, and `pgvector` retrieval with citations.
- `mcp_tools`: Schema-validated, permission-checked, audit-logged operational tools.
- `remediation`: Approval queue, simulated execution, before/after health check, and verification records.
- `audit_reporting`: Audit log recording, reliability analytics, and CSV/PDF report exports.