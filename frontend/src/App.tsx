import { useEffect, useState } from 'react';
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import { Activity, AlertTriangle, LogOut, Server } from 'lucide-react';
import { clearStoredToken, fetchCurrentUser, getStoredToken } from './lib/api';
import { DashboardPage } from './pages/DashboardPage';
import { IncidentsPage } from './pages/IncidentsPage';
import { LoginPage } from './pages/LoginPage';
import { ServiceExplorerPage } from './pages/ServiceExplorerPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 5000 },
  },
});

function OpsMindShell() {
  const [hasToken, setHasToken] = useState<boolean>(() => Boolean(getStoredToken()));
  const [activeTab, setActiveTab] = useState<'dashboard' | 'services' | 'incidents'>('dashboard');
  const [timeRange, setTimeRange] = useState<string>('24h');
  const [environment, setEnvironment] = useState<string>('');
  const [serviceId, setServiceId] = useState<string>('');

  const meQuery = useQuery({
    queryKey: ['current-user'],
    queryFn: fetchCurrentUser,
    enabled: hasToken,
  });

  useEffect(() => {
    if (meQuery.isError) {
      clearStoredToken();
      setHasToken(false);
    }
  }, [meQuery.isError]);

  if (!hasToken) {
    return <LoginPage onSuccess={() => setHasToken(true)} />;
  }

  function handleLogout() {
    clearStoredToken();
    setHasToken(false);
    queryClient.clear();
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <header className="border-b border-slate-800 bg-slate-900/90 px-4 py-3 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="font-semibold text-base tracking-tight text-white">OpsMind AI</span>
          <span className="text-[11px] px-2 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-800/70">
            SIMULATED ENVIRONMENT
          </span>
        </div>

        <nav className="flex items-center gap-2">
          <button
            onClick={() => setActiveTab('dashboard')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              activeTab === 'dashboard'
                ? 'bg-sky-500 text-slate-950'
                : 'text-slate-300 hover:bg-slate-800'
            }`}
          >
            <Activity className="h-3.5 w-3.5" />
            Operations Dashboard
          </button>
          <button
            onClick={() => setActiveTab('services')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              activeTab === 'services'
                ? 'bg-sky-500 text-slate-950'
                : 'text-slate-300 hover:bg-slate-800'
            }`}
          >
            <Server className="h-3.5 w-3.5" />
            Service Explorer
          </button>
          <button
            onClick={() => setActiveTab('incidents')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              activeTab === 'incidents'
                ? 'bg-sky-500 text-slate-950'
                : 'text-slate-300 hover:bg-slate-800'
            }`}
          >
            <AlertTriangle className="h-3.5 w-3.5" />
            Incidents
          </button>
        </nav>

        <div className="flex items-center gap-3 text-xs">
          {meQuery.data && (
            <span className="text-slate-300">
              {meQuery.data.full_name}{' '}
              <span className="text-slate-400">({meQuery.data.role_names.join(', ')})</span>
            </span>
          )}
          <button
            onClick={handleLogout}
            className="flex items-center gap-1 rounded-lg border border-slate-700 px-2.5 py-1.5 text-slate-300 hover:bg-slate-800"
          >
            <LogOut className="h-3.5 w-3.5" />
            Sign out
          </button>
        </div>
      </header>

      <main className="flex-1 max-w-7xl w-full mx-auto p-4 md:p-6">
        {activeTab === 'dashboard' && (
          <DashboardPage
            timeRange={timeRange}
            environment={environment}
            serviceId={serviceId}
            onTimeRangeChange={setTimeRange}
            onEnvironmentChange={setEnvironment}
            onServiceIdChange={setServiceId}
          />
        )}
        {activeTab === 'services' && <ServiceExplorerPage environment={environment} />}
        {activeTab === 'incidents' && <IncidentsPage environment={environment} />}
      </main>
    </div>
  );
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <OpsMindShell />
    </QueryClientProvider>
  );
}

export default App;