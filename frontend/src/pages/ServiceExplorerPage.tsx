import { useQuery } from '@tanstack/react-query';
import { fetchServices } from '../lib/api';

interface ServiceExplorerPageProps {
  environment: string;
}

export function ServiceExplorerPage({ environment }: ServiceExplorerPageProps) {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['service-explorer', environment],
    queryFn: () => fetchServices(environment || undefined),
  });

  if (isLoading) {
    return <div className="text-sm text-slate-400">Loading simulated services...</div>;
  }

  if (isError) {
    return (
      <div className="rounded-xl border border-rose-800 bg-rose-950/50 p-4 text-sm text-rose-200">
        Error loading services: {error instanceof Error ? error.message : 'Unknown error'}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-white">Service Explorer</h2>
        <p className="text-xs text-slate-400">
          Simulated services, resource bindings, and health telemetry
        </p>
      </div>

      <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900">
        <table className="w-full text-left text-xs">
          <thead className="border-b border-slate-800 bg-slate-950/70 text-slate-400">
            <tr>
              <th className="py-3 px-4">Service</th>
              <th className="py-3 px-4">Env</th>
              <th className="py-3 px-4">Status</th>
              <th className="py-3 px-4">Availability</th>
              <th className="py-3 px-4">CPU</th>
              <th className="py-3 px-4">Memory</th>
              <th className="py-3 px-4">p95 Latency</th>
              <th className="py-3 px-4">Error Rate</th>
              <th className="py-3 px-4">Active Scenario</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800 text-slate-200">
            {(data ?? []).map((svc) => (
              <tr key={svc.id} className="hover:bg-slate-800/40">
                <td className="py-3 px-4">
                  <div className="font-medium text-white">{svc.name}</div>
                  <div className="text-[11px] text-slate-400">{svc.description}</div>
                </td>
                <td className="py-3 px-4 font-mono text-[11px]">{svc.environment}</td>
                <td className="py-3 px-4">
                  <span
                    className={`px-2 py-0.5 rounded text-[11px] ${
                      svc.status === 'healthy'
                        ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                        : svc.status === 'degraded'
                        ? 'bg-amber-950 text-amber-300 border border-amber-800'
                        : 'bg-rose-950 text-rose-300 border border-rose-800'
                    }`}
                  >
                    {svc.status}
                  </span>
                </td>
                <td className="py-3 px-4">{svc.availability_pct.toFixed(2)}%</td>
                <td className="py-3 px-4">{svc.cpu_pct.toFixed(1)}%</td>
                <td className="py-3 px-4">{svc.memory_pct.toFixed(1)}%</td>
                <td className="py-3 px-4">{svc.latency_p95_ms.toFixed(0)} ms</td>
                <td className="py-3 px-4">{svc.error_rate_pct.toFixed(2)}%</td>
                <td className="py-3 px-4 font-mono text-[11px] text-amber-300">
                  {svc.active_scenario
                    ? `${svc.active_scenario}${svc.scenario_paused ? ' (paused)' : ''}`
                    : 'none'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}