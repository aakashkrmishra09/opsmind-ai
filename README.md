# OpsMind AI

OpsMind AI is a simulated hybrid-cloud IT operations, observability, and AI-assisted incident response platform built as a modular monolith.

> **Simulation Notice:** All infrastructure nodes, telemetry streams (logs, metrics, events, traces), and remediation actions in OpsMind AI are simulated locally. No external cloud accounts or real infrastructure are modified.

## Core Capabilities
- **Operations Dashboard & Service Health:** Tracks service availability, incident counts, MTTA, MTTR, recent deployments, and infrastructure status.
- **Simulated Infrastructure & Fault Engine:** Models services, hosts, containers, databases, queues, networks, and dependencies across `dev`, `staging`, and `prod-sim`, with trigger, pause, and reset controls.
- **Observability Engine:** Queries logs, metrics, events, and traces by service, environment, severity, time range, incident, and correlation ID.
- **Incident Lifecycle & AI Investigation:** Manages incidents across all lifecycle stages, ranks root-cause hypotheses with supporting and contradicting evidence, and grounds guidance in a `pgvector` knowledge base with source citations.
- **MCP-Style Tools, Human Approval & Audit Trail:** Enforces role-based permissions (`Admin`, `Operations Engineer`, `Viewer`), human sign-off before simulated remediation runs, and full audit logging with CSV/PDF export.

## Repository Status
- **Milestone 1 (Current):** Repository setup, baseline configuration, architecture documentation, and initial Git workflow.

## Local Setup (Milestone 1)
1. Clone the repository and open it in VS Code.
2. Copy `.env.example` to `.env` and fill in local values.
3. Follow the milestone guides in `docs/ARCHITECTURE.md` and `CONTRIBUTING.md`.