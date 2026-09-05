import { useState } from "react";
import { Link } from "react-router-dom";
import { useQueries } from "@tanstack/react-query";
import { usePhases, usePhasesReport } from "../../api/phases/hooks";
import * as phasesApi from "../../api/phases/api";
import { DomainCard } from "../../components/domain-card/DomainCard";
import { EmptyValue } from "../../components/empty-state/EmptyValue";
import { Button } from "../../components/ui/button";
import { PhaseForm } from "./PhaseForm";
import { METRIC_LABEL, OBJECTIVE_DELTA_UNIT } from "../../lib/metric-config";
import type { Metric, PhaseKind } from "../../api/types";

const EFFICIENCY_METRICS: Metric[] = ["weight", "body_fat", "muscle"];

function round2(value: number): number {
  return Math.round(value * 100) / 100;
}

const KIND_COLOR: Record<PhaseKind, string> = {
  cut: "bg-domain-training",
  bulk: "bg-domain-body",
  maintain: "bg-domain-phase",
  free: "bg-text-low",
};

function dayOffset(from: string, to: string): number {
  return (Date.parse(to) - Date.parse(from)) / 86_400_000;
}

export function PhasesPage() {
  const phases = usePhases();
  const report = usePhasesReport();
  const [createOpen, setCreateOpen] = useState(false);

  const sorted = [...(phases.data ?? [])].sort((a, b) => a.starts_on.localeCompare(b.starts_on));
  const timelineStart = sorted[0]?.starts_on;
  const timelineEnd = sorted.reduce((max, p) => (p.ends_on > max ? p.ends_on : max), sorted[0]?.ends_on ?? "");
  const totalDays = timelineStart ? dayOffset(timelineStart, timelineEnd) || 1 : 1;

  const phaseReportQueries = useQueries({
    queries: sorted.map((p) => ({
      queryKey: ["phases", p.id, "report", undefined] as const,
      queryFn: () => phasesApi.fetchPhaseReport(p.id),
    })),
  });

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl">Phases</h1>
          <p className="text-text-mid">Liste et timeline des phases.</p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>Nouvelle phase</Button>
      </div>

      <DomainCard variant="phase" title="Timeline">
        {phases.isLoading ? (
          <p className="text-sm text-text-mid">Chargement…</p>
        ) : (
          <div className="relative h-6 w-full rounded-card bg-surface-raised">
            {sorted.map((p) => {
              const left = (dayOffset(timelineStart, p.starts_on) / totalDays) * 100;
              const width = Math.max(1, (dayOffset(p.starts_on, p.ends_on) / totalDays) * 100);
              return (
                <Link
                  key={p.id}
                  to={`/phases/${p.id}`}
                  title={p.name}
                  className={`absolute top-0 h-full rounded-card ${KIND_COLOR[p.kind]} opacity-70 hover:opacity-100`}
                  style={{ left: `${left}%`, width: `${width}%` }}
                />
              );
            })}
          </div>
        )}
      </DomainCard>

      <DomainCard variant="phase" title="Liste">
        {phases.isLoading ? (
          <p className="text-sm text-text-mid">Chargement…</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {sorted.map((p) => (
              <li key={p.id}>
                <Link to={`/phases/${p.id}`} className="flex items-center justify-between text-sm hover:text-text-high">
                  <span className="text-text-high">{p.name}</span>
                  <span className="tabular text-text-mid">
                    {p.starts_on} → {p.ends_on}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </DomainCard>

      <DomainCard variant="phase" title="Bilan transverse — taux de réussite par métrique">
        {report.isLoading ? (
          <p className="text-sm text-text-mid">Chargement…</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {report.data?.map((r) => (
              <li key={r.metric} className="flex items-center justify-between text-sm">
                <span className="text-text-mid">{r.metric}</span>
                <span className="tabular text-text-high">
                  {r.achieved_count}/{r.total_count} ({Math.round(r.success_rate * 100)}%)
                </span>
              </li>
            ))}
          </ul>
        )}
      </DomainCard>

      <DomainCard variant="phase" title="Efficacité par phase — rythme mensuel réel">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-text-mid">
              <th className="pb-2 font-normal">Phase</th>
              {EFFICIENCY_METRICS.map((m) => (
                <th key={m} className="pb-2 font-normal">
                  {METRIC_LABEL[m]}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="tabular">
            {sorted.map((p, i) => {
              const q = phaseReportQueries[i];
              return (
                <tr key={p.id} className="border-t border-line">
                  <td className="py-2 text-text-high">{p.name}</td>
                  {EFFICIENCY_METRICS.map((metric) => {
                    if (q.isLoading) return <td key={metric} className="py-2 text-text-mid">…</td>;
                    const m = q.data?.metrics.find((x) => x.metric === metric);
                    return (
                      <td key={metric} className="py-2">
                        {m?.monthly_rate !== null && m?.monthly_rate !== undefined ? (
                          `${round2(m.monthly_rate)} ${OBJECTIVE_DELTA_UNIT[metric]}/mois`
                        ) : (
                          <EmptyValue />
                        )}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </DomainCard>

      <PhaseForm open={createOpen} onOpenChange={setCreateOpen} />
    </div>
  );
}
