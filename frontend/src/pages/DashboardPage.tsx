import { useQuery } from '@tanstack/react-query';
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { fetchDashboardSummary, fetchServices } from '../lib/api';

interface DashboardPageProps {
  timeRange: string;
  environment: string;
  serviceId: string;
  onTimeRangeChange: (v: string) => void;
  onEnvironmentChange: (v: string) => void;
  onServiceIdChange: (v: string) => void;
}

export function DashboardPage({
  timeRange,
  environment,
  serviceId,
  onTimeRangeChange,
  onEnvironmentChange,
  onServiceIdChange,
}: DashboardPageProps) {
  const servicesQuery = useQuery({
    queryKey: ['services', environment],
    queryFn: () => fetchServices(environment || undefined),
  });

  const summaryQuery = useQuery({
    queryKey: ['dashboard-summary', timeRange, environment, serviceId],
    queryFn: () =>
      fetchDashboardSummary({
        timeRange,
        environment,
        serviceId,
      }),
  });

  const data = summaryQuery.data;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-white">Operations Dashboard</h2>
          <p className="text-xs text-slate-400">
            Simulated hybrid-cloud telemetry &amp; incident posture (all metrics synthetic)
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <select
            aria-label="Environment filter"
            value={environment}
            onChange={(e) => onEnvironmentChange(e.target.value)}
            className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs text-slate-200"
          >
            <option value="">All Environments</option>
            <option value="prod-sim">prod-sim</option>
            <option value="staging">staging</option>
            <option value="dev">dev</option>
          </select>

          <select
            aria-label="Service filter"
            value={serviceId}
            onChange={(e) => onServiceIdChange(e.target.value)}
            className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs text-slate-200"
          >
            <option value="">All Services</option>
            {(servicesQuery.data ?? []).map((svc) => (
              <option key={svc.id} value={svc.id}>
                {svc.name} ({svc.environment})
              </option>
            ))}
          </select>

          <select
            aria-label="Time range filter"
            value={timeRange}
            onChange={(e) => onTimeRangeChange(e.target.value)}
            className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs text-slate-200"
          >
            <option value="15m">Last 15m</option>
            <option value="1h">Last 1h</option>
            <option value="6h">Last 6h</option>
            <option value="24h">Last 24h</option>
            <option value="7d">Last 7d</option>
          </select>
        </div>
      </div>

      {summaryQuery.isLoading && (
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-6 text-sm text-slate-400">
          Loading simulated telemetry and KPIs...
        </div>
      )}

      {summaryQuery.isError && (
        <div className="rounded-xl border border-rose-800 bg-rose-950/50 p-4 text-sm text-rose-200">
          Failed to load dashboard summary:{' '}
          {summaryQuery.error instanceof Error ? summaryQuery.error.message : 'Unknown error'}
        </div>
      )}

      {data && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <KpiCard
              label="Monitored Services"
              value={String(data.total_monitored_services)}
              sub={`${data.healthy_services} healthy · ${data.degraded_services} degraded · ${data.unavailable_services} down`}
            />
            <KpiCard
              label="Active Incidents"
              value={String(data.active_incidents)}
              sub={`${data.critical_high_incidents} critical/high scenarios`}
              accent={data.active_incidents > 0 ? 'amber' : 'emerald'}
            />
            <KpiCard
              label="Service Availability"
              value={`${data.service_availability_pct.toFixed(2)}%`}
              sub={`Freq: ${data.incident_frequency_per_day}/day`}
            />
            <KpiCard
              label="MTTA / MTTR"
              value={`${data.mtta_minutes ?? '—'} / ${data.mttr_minutes ?? '—'}`}
              sub="Minutes (tracked as incidents resolve)"
            />
          </div>

          <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-medium text-slate-200">
                Simulated CPU (%) &amp; p95 Latency (ms) Trend
              </h3>
              <span className="text-[11px] text-slate-400">Source: PostgreSQL telemetry_metrics</span>
            </div>

            {data.metric_series.length === 0 ? (
              <p className="text-xs text-slate-400 py-8 text-center">
                No metric points recorded for this filter window.
              </p>
            ) : (
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={data.metric_series}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey="time" stroke="#94a3b8" fontSize={11} />
                    <YAxis stroke="#94a3b8" fontSize={11} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#0f172a',
                        borderColor: '#334155',
                        fontSize: '12px',
                      }}
                    />
                    <Line
                      type="monotone"
                      dataKey="cpu_pct"
                      name="CPU %"
                      stroke="#38bdf8"
                      dot={false}
                    />
                    <Line
                      type="monotone"
                      dataKey="latency_p95_ms"
                      name="p95 Latency (ms)"
                      stroke="#f59e0b"
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
              <h3 className="text-sm font-medium text-slate-200 mb-3">Recent Alerts (Simulated Events)</h3>
              {data.recent_alerts.length === 0 ? (
                <p className="text-xs text-slate-400">No recent alerts in this window.</p>
              ) : (
                <ul className="space-y-2 text-xs">
                  {data.recent_alerts.map((ev) => (
                    <li
                      key={ev.id}
                      className="rounded-lg border border-slate-800 bg-slate-950/70 p-2.5 flex items-start justify-between gap-2"
                    >
                      <div>
                        <span className="font-mono text-[11px] text-sky-400 mr-2">
                          [{ev.severity}]
                        </span>
                        <span className="text-slate-200">{ev.summary}</span>
                      </div>
                      <span className="text-[11px] text-slate-400 shrink-0">{ev.environment}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
              <h3 className="text-sm font-medium text-slate-200 mb-3">Recent Simulated Deployments</h3>
              {data.recent_deployments.length === 0 ? (
                <p className="text-xs text-slate-400">No deployments in this window.</p>
              ) : (
                <ul className="space-y-2 text-xs">
                  {data.recent_deployments.map((dep) => (
                    <li
                      key={dep.id}
                      className="rounded-lg border border-slate-800 bg-slate-950/70 p-2.5 flex items-center justify-between"
                    >
                      <div>
                        <span className="font-medium text-slate-100">{dep.version}</span>
                        <span className="text-slate-400 ml-2">({dep.environment})</span>
                      </div>
                      <span
                        className={`px-2 py-0.5 rounded text-[11px] ${
                          dep.status === 'failed'
                            ? 'bg-rose-950 text-rose-300 border border-rose-800'
                            : 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                        }`}
                      >
                        {dep.status}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
            <h3 className="text-sm font-medium text-slate-200 mb-2">Documented Metric Calculations</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs text-slate-300">
              {data.formulas.map((f) => (
                <div key={f.metric} className="rounded-lg bg-slate-950/70 border border-slate-800 p-2.5">
                  <p className="font-medium text-sky-300">
                    {f.metric} <span className="text-slate-400 font-normal">({f.unit})</span>
                  </p>
                  <p className="text-slate-400 font-mono text-[11px] mt-0.5">{f.formula}</p>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function KpiCard({
  label,
  value,
  sub,
  accent = 'default',
}: {
  label: string;
  value: string;
  sub: string;
  accent?: 'default' | 'amber' | 'emerald';
}) {
  const valueColor =
    accent === 'amber'
      ? 'text-amber-300'
      : accent === 'emerald'
      ? 'text-emerald-300'
      : 'text-white';

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
      <p className="text-xs text-slate-400">{label}</p>
      <p className={`text-2xl font-semibold mt-1 ${valueColor}`}>{value}</p>
      <p className="text-[11px] text-slate-400 mt-1">{sub}</p>
    </div>
  );
}