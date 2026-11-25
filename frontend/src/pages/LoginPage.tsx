import { useState, type FormEvent } from 'react';
import { ShieldCheck } from 'lucide-react';
import { loginUser } from '../lib/api';

interface LoginPageProps {
  onSuccess: () => void;
}

export function LoginPage({ onSuccess }: LoginPageProps) {
  const [email, setEmail] = useState('admin@opsmind.local');
  const [password, setPassword] = useState('Admin123!');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await loginUser(email, password);
      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Sign-in failed');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-4">
      <div className="w-full max-w-md rounded-xl border border-slate-800 bg-slate-900 p-6 shadow-xl">
        <div className="flex items-center gap-2.5 mb-2">
          <ShieldCheck className="h-6 w-6 text-sky-400" />
          <h1 className="text-xl font-semibold tracking-tight">OpsMind AI</h1>
        </div>
        <p className="text-xs text-amber-300/90 bg-amber-950/50 border border-amber-800/60 rounded-lg px-3 py-2 mb-5">
          Simulated Hybrid-Cloud Control Center — All telemetry and actions are synthetic.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-sky-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-sky-500 focus:outline-none"
            />
          </div>

          {error && (
            <div className="rounded-lg border border-rose-800 bg-rose-950/60 px-3 py-2 text-xs text-rose-200">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-lg bg-sky-500 hover:bg-sky-400 disabled:opacity-50 px-4 py-2 text-sm font-medium text-slate-950 transition"
          >
            {submitting ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <div className="mt-5 border-t border-slate-800 pt-3 text-xs text-slate-400 space-y-1">
          <p className="font-medium text-slate-300">Local Seed Accounts:</p>
          <p>Admin: <span className="text-slate-200">admin@opsmind.local</span> / <span className="text-slate-200">Admin123!</span></p>
          <p>SRE: <span className="text-slate-200">sre@opsmind.local</span> / <span className="text-slate-200">OpsEng123!</span></p>
          <p>Viewer: <span className="text-slate-200">viewer@opsmind.local</span> / <span className="text-slate-200">Viewer123!</span></p>
        </div>
      </div>
    </div>
  );
}