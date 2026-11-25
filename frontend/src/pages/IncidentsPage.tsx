import { useState, type FormEvent } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  createIncidentApi,
  fetchIncidentDetail,
  fetchIncidents,
  fetchIncidentStages,
  generatePostmortemApi,
  linkIncidentEvidenceApi,
  updateIncidentStatusApi,
} from '../lib/api';

interface IncidentsPageProps {
  environment: string;
}

export function IncidentsPage({ environment }: IncidentsPageProps) {
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [severity, setSeverity] = useState('high');
  const [nextStage, setNextStage] = useState('incident_acknowledged');
  const [stageNote, setStageNote] = useState('');
  const [refId, setRefId] = useState('');
  const [evType, setEvType] = useState('log');
  const [stance, setStance] = useState('supporting');
  const [evNotes, setEvNotes] = useState('');

  const incidentsQuery = useQuery({
    queryKey: ['incidents', environment],
    queryFn: () => fetchIncidents(environment || undefined),
  });

  const stagesQuery = useQuery({
    queryKey: ['incident-stages'],
    queryFn: fetchIncidentStages,
  });

  const activeId = selectedId ?? incidentsQuery.data?.[0]?.id ?? null;

  const detailQuery = useQuery({
    queryKey: ['incident-detail', activeId],
    queryFn: () => fetchIncidentDetail(activeId!),
    enabled: Boolean(activeId),
  });

  const createMut = useMutation({
    mutationFn: createIncidentApi,
    onSuccess: (created) => {
      setTitle('');
      setDescription('');
      setSelectedId(created.id);
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
    },
  });

  const statusMut = useMutation({
    mutationFn: ({ id, status, note }: { id: string; status: string; note?: string }) =>
      updateIncidentStatusApi(id, { status, note }),
    onSuccess: () => {
      setStageNote('');
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
      queryClient.invalidateQueries({ queryKey: ['incident-detail', activeId] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
    },
  });

  const evidenceMut = useMutation({
    mutationFn: ({
      id,
      evidence_type,
      reference_id,
      stance,
      notes,
    }: {
      id: string;
      evidence_type: string;
      reference_id: string;
      stance: string;
      notes: string;
    }) => linkIncidentEvidenceApi(id, { evidence_type, reference_id, stance, notes }),
    onSuccess: () => {
      setRefId('');
      setEvNotes('');
      queryClient.invalidateQueries({ queryKey: ['incident-detail', activeId] });
    },
  });

  const postmortemMut = useMutation({
    mutationFn: (id: string) => generatePostmortemApi(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
      queryClient.invalidateQueries({ queryKey: ['incident-detail', activeId] });
    },
  });

  function handleCreate(e: FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    createMut.mutate({
      title,
      description,
      severity,
      environment: environment || 'prod-sim',
    });
  }

  const detail = detailQuery.data;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-white">Incident Management &amp; Timeline</h2>
        <p className="text-xs text-slate-400">
          13-stage incident lifecycle, linked telemetry evidence, and post-incident reports
        </p>
      </div>

      <form
        onSubmit={handleCreate}
        className="rounded-xl border border-slate-800 bg-slate-900 p-4 grid grid-cols-1 md:grid-cols-4 gap-3"
      >
        <input
          type="text"
          placeholder="Incident title (e.g., DB pool exhaustion)"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
          className="md:col-span-2 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-white"
        />
        <select
          value={severity}
          onChange={(e) => setSeverity(e.target.value)}
          className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-200"
        >
          <option value="low">low</option>
          <option value="medium">medium</option>
          <option value="high">high</option>
          <option value="critical">critical</option>
        </select>
        <button
          type="submit"
          disabled={createMut.isPending}
          className="rounded-lg bg-sky-500 hover:bg-sky-400 px-4 py-2 text-xs font-medium text-slate-950"
        >
          {createMut.isPending ? 'Creating...' : 'Create Incident'}
        </button>
        <input
          type="text"
          placeholder="Optional description..."
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className="md:col-span-4 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-200"
        />
      </form>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        <div className="lg:col-span-5 rounded-xl border border-slate-800 bg-slate-900 p-4 space-y-2">
          <h3 className="text-sm font-medium text-slate-200 mb-2">Incidents</h3>
          {(incidentsQuery.data ?? []).length === 0 ? (
            <p className="text-xs text-slate-400 py-4">No incidents created yet.</p>
          ) : (
            (incidentsQuery.data ?? []).map((inc) => (
              <button
                key={inc.id}
                onClick={() => setSelectedId(inc.id)}
                className={`w-full text-left rounded-lg border p-3 transition ${
                  inc.id === activeId
                    ? 'border-sky-500 bg-slate-800/70'
                    : 'border-slate-800 bg-slate-950/60 hover:bg-slate-800/40'
                }`}
              >
                <div className="flex items-center justify-between text-xs">
                  <span className="font-mono text-sky-400">{inc.incident_code}</span>
                  <span className="uppercase text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-200">
                    {inc.severity}
                  </span>
                </div>
                <p className="text-xs font-medium text-white mt-1">{inc.title}</p>
                <p className="text-[11px] text-slate-400 mt-1 font-mono">{inc.status}</p>
              </button>
            ))
          )}
        </div>

        <div className="lg:col-span-7 rounded-xl border border-slate-800 bg-slate-900 p-4 space-y-4">
          {!detail ? (
            <p className="text-xs text-slate-400">Select or create an incident to view details.</p>
          ) : (
            <>
              <div className="flex flex-wrap items-start justify-between gap-2 border-b border-slate-800 pb-3">
                <div>
                  <span className="font-mono text-xs text-sky-400">{detail.incident_code}</span>
                  <h3 className="text-base font-semibold text-white">{detail.title}</h3>
                  <p className="text-xs text-slate-400 mt-0.5">{detail.description}</p>
                </div>
                <button
                  onClick={() => postmortemMut.mutate(detail.id)}
                  disabled={postmortemMut.isPending}
                  className="rounded-lg border border-slate-700 bg-slate-800 hover:bg-slate-700 px-3 py-1.5 text-xs text-slate-100"
                >
                  Generate Postmortem
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                <select
                  value={nextStage}
                  onChange={(e) => setNextStage(e.target.value)}
                  className="rounded-lg border border-slate-700 bg-slate-950 px-2.5 py-1.5 text-xs text-slate-200"
                >
                  {(stagesQuery.data ?? []).map((st) => (
                    <option key={st} value={st}>
                      {st}
                    </option>
                  ))}
                </select>
                <input
                  type="text"
                  placeholder="Transition note..."
                  value={stageNote}
                  onChange={(e) => setStageNote(e.target.value)}
                  className="rounded-lg border border-slate-700 bg-slate-950 px-2.5 py-1.5 text-xs text-slate-200"
                />
                <button
                  onClick={() =>
                    statusMut.mutate({ id: detail.id, status: nextStage, note: stageNote })
                  }
                  disabled={statusMut.isPending}
                  className="rounded-lg bg-sky-500 hover:bg-sky-400 px-3 py-1.5 text-xs font-medium text-slate-950"
                >
                  Update Stage
                </button>
              </div>

              <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-3 space-y-2">
                <p className="text-xs font-medium text-slate-200">Link Telemetry Evidence</p>
                <div className="grid grid-cols-1 sm:grid-cols-4 gap-2">
                  <select
                    value={evType}
                    onChange={(e) => setEvType(e.target.value)}
                    className="rounded border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-slate-200"
                  >
                    <option value="log">log</option>
                    <option value="metric">metric</option>
                    <option value="event">event</option>
                    <option value="trace">trace</option>
                    <option value="deployment">deployment</option>
                  </select>
                  <input
                    type="text"
                    placeholder="Correlation / Ref ID"
                    value={refId}
                    onChange={(e) => setRefId(e.target.value)}
                    className="rounded border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-slate-200"
                  />
                  <select
                    value={stance}
                    onChange={(e) => setStance(e.target.value)}
                    className="rounded border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-slate-200"
                  >
                    <option value="supporting">supporting</option>
                    <option value="contradicting">contradicting</option>
                    <option value="neutral">neutral</option>
                  </select>
                  <button
                    onClick={() => {
                      if (!refId.trim()) return;
                      evidenceMut.mutate({
                        id: detail.id,
                        evidence_type: evType,
                        reference_id: refId,
                        stance,
                        notes: evNotes,
                      });
                    }}
                    className="rounded bg-slate-800 hover:bg-slate-700 border border-slate-600 px-2 py-1 text-xs text-white"
                  >
                    Link Evidence
                  </button>
                </div>
                <input
                  type="text"
                  placeholder="Evidence note..."
                  value={evNotes}
                  onChange={(e) => setEvNotes(e.target.value)}
                  className="w-full rounded border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-slate-200"
                />
                <ul className="space-y-1 text-xs pt-1">
                  {detail.evidence_items.map((ev) => (
                    <li key={ev.id} className="text-slate-300 font-mono text-[11px]">
                      [{ev.stance}] {ev.evidence_type}: {ev.reference_id} — {ev.notes}
                    </li>
                  ))}
                </ul>
              </div>

              <div>
                <h4 className="text-xs font-medium text-slate-200 mb-2">Timeline</h4>
                <ul className="space-y-1.5 text-xs max-h-48 overflow-y-auto">
                  {detail.timeline_entries.map((t) => (
                    <li
                      key={t.id}
                      className="rounded border border-slate-800 bg-slate-950/70 px-3 py-2"
                    >
                      <span className="font-mono text-[11px] text-sky-400 mr-2">[{t.stage}]</span>
                      <span className="text-slate-200">{t.summary}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {detail.postmortem_markdown && (
                <pre className="rounded-lg border border-slate-800 bg-slate-950 p-3 text-[11px] text-slate-300 overflow-x-auto whitespace-pre-wrap">
                  {detail.postmortem_markdown}
                </pre>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}