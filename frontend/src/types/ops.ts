export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  role_names: string[];
  created_at: string;
}

export interface InfrastructureResource {
  id: string;
  service_id: string;
  resource_type: string;
  name: string;
  environment: string;
  status: string;
  specs_json: Record<string, unknown>;
  updated_at: string;
}

export interface ServiceItem {
  id: string;
  name: string;
  description: string;
  environment: string;
  status: 'healthy' | 'degraded' | 'unavailable' | string;
  availability_pct: number;
  cpu_pct: number;
  memory_pct: number;
  request_rate_rps: number;
  error_rate_pct: number;
  latency_p95_ms: number;
  active_scenario: string | null;
  scenario_paused: boolean;
  updated_at: string;
  resources: InfrastructureResource[];
}

export interface DeploymentItem {
  id: string;
  service_id: string;
  environment: string;
  version: string;
  status: string;
  triggered_by: string;
  deployed_at: string;
}

export interface AlertEventItem {
  id: number;
  service_id: string;
  environment: string;
  event_type: string;
  severity: string;
  correlation_id: string;
  summary: string;
  recorded_at: string;
}

export interface MetricPoint {
  time: string;
  cpu_pct: number | null;
  latency_p95_ms: number | null;
}

export interface MetricFormula {
  metric: string;
  formula: string;
  unit: string;
}

export interface DashboardSummary {
  simulated: boolean;
  time_range: string;
  environment: string | null;
  total_monitored_services: number;
  healthy_services: number;
  degraded_services: number;
  unavailable_services: number;
  active_incidents: number;
  critical_high_incidents: number;
  mtta_minutes: number | null;
  mttr_minutes: number | null;
  incident_frequency_per_day: number;
  service_availability_pct: number;
  recent_deployments: DeploymentItem[];
  recent_alerts: AlertEventItem[];
  metric_series: MetricPoint[];
  formulas: MetricFormula[];
}

export interface IncidentTimelineEntry {
  id: string;
  incident_id: string;
  actor_user_id: string | null;
  stage: string;
  entry_type: string;
  summary: string;
  created_at: string;
}

export interface IncidentEvidenceItem {
  id: string;
  incident_id: string;
  evidence_type: string;
  reference_id: string;
  stance: string;
  notes: string;
  collected_at: string;
}

export interface IncidentSummary {
  id: string;
  incident_code: string;
  title: string;
  description: string;
  severity: string;
  status: string;
  environment: string;
  detected_at: string;
  acknowledged_at: string | null;
  resolved_at: string | null;
}

export interface IncidentDetail extends IncidentSummary {
  postmortem_markdown: string | null;
  timeline_entries: IncidentTimelineEntry[];
  evidence_items: IncidentEvidenceItem[];
}