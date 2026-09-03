import { useMemo, useState } from "react";
import { useQueries } from "@tanstack/react-query";
import { usePhases } from "../../api/phases/hooks";
import { useEnergyBalance, useTdee } from "../../api/analytics/hooks";
import * as analyticsApi from "../../api/analytics/api";
import { useComposition } from "../../api/body/hooks";
import { DomainCard } from "../../components/domain-card/DomainCard";
import { StatTile } from "../../components/charts/StatTile";
import { LineSeriesCard } from "../../components/charts/LineSeriesCard";
import { EmptyValue } from "../../components/empty-state/EmptyValue";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select";

const DAYS_PER_MONTH = 30.44;

function monthlySlope(kgPerDay: number | null): number | null {
  return kgPerDay !== null ? Math.round(kgPerDay * DAYS_PER_MONTH * 100) / 100 : null;
}

export function EnergyPage() {
  const phases = usePhases();
  const [phaseId, setPhaseId] = useState<number | undefined>(undefined);
  const selectedPhase = phases.data?.find((p) => p.id === phaseId);

  const tdee = useTdee({ phase_id: phaseId });
  const energyBalance = useEnergyBalance({ from: selectedPhase?.starts_on, to: selectedPhase?.ends_on });
  const composition = useComposition({ from: selectedPhase?.starts_on, to: selectedPhase?.ends_on });

  const balanceData = useMemo(
    () => (energyBalance.data ?? []).map((d) => ({ ...d, at: d.day })),
    [energyBalance.data],
  );

  const sortedPhases = useMemo(
    () => [...(phases.data ?? [])].sort((a, b) => a.starts_on.localeCompare(b.starts_on)),
    [phases.data],
  );
  const phaseTdeeQueries = useQueries({
    queries: sortedPhases.map((p) => ({
      queryKey: ["analytics", "tdee", { phase_id: p.id }] as const,
      queryFn: () => analyticsApi.fetchTdee({ phase_id: p.id }),
    })),
  });
  const bmrData = useMemo(
    () => (composition.data ?? []).map((d) => ({ at: d.day, basal_metabolic_rate_kcal: d.basal_metabolic_rate_kcal })),
    [composition.data],
  );

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl">Énergie</h1>
          <p className="text-text-mid">
            Dépense énergétique mesurée par phase, apport contre dépense, métabolisme de base.
          </p>
        </div>
        <Select value={phaseId?.toString() ?? "all"} onValueChange={(v) => setPhaseId(v === "all" ? undefined : Number(v))}>
          <SelectTrigger className="w-56">
            <SelectValue placeholder="Toutes les données" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Toutes les données</SelectItem>
            {phases.data?.map((p) => (
              <SelectItem key={p.id} value={p.id.toString()}>
                {p.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <DomainCard variant="phase" title="Dépense énergétique estimée (TDEE)">
        {tdee.isLoading ? (
          <p className="text-sm text-text-mid">Chargement…</p>
        ) : tdee.data && !tdee.data.is_valid ? (
          <p className="text-sm text-text-mid">{tdee.data.reason}</p>
        ) : (
          <div className="flex flex-col gap-3">
            <div className="flex gap-6">
              <StatTile
                label="Dépense estimée"
                value={tdee.data?.tdee_kcal !== null && tdee.data?.tdee_kcal !== undefined ? Math.round(tdee.data.tdee_kcal) : null}
                unit="kcal/j"
              />
              <StatTile
                label="Apport moyen"
                value={
                  tdee.data?.mean_intake_kcal !== null && tdee.data?.mean_intake_kcal !== undefined
                    ? Math.round(tdee.data.mean_intake_kcal)
                    : null
                }
                unit="kcal/j"
              />
              <StatTile
                label="Pente du poids"
                value={monthlySlope(tdee.data?.weight_slope_kg_per_day ?? null)}
                unit="kg/mois"
              />
            </div>
            <p className="text-xs text-text-mid">{tdee.data?.uncertainty_note}</p>
          </div>
        )}
      </DomainCard>

      <DomainCard variant="nutrition" title="Apport contre dépense">
        <LineSeriesCard
          data={balanceData}
          xKey="at"
          series={[
            { key: "intake_kcal", label: "Apport (kcal)" },
            { key: "expenditure_kcal", label: "Dépense (kcal)" },
          ]}
        />
      </DomainCard>

      <DomainCard variant="body" title="Métabolisme de base">
        <LineSeriesCard
          data={bmrData}
          xKey="at"
          series={[{ key: "basal_metabolic_rate_kcal", label: "Métabolisme de base (kcal)" }]}
        />
      </DomainCard>

      <DomainCard variant="phase" title="Comparaison entre phases — données réelles">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-text-mid">
              <th className="pb-2 font-normal">Phase</th>
              <th className="pb-2 font-normal">Dépense estimée</th>
              <th className="pb-2 font-normal">Apport moyen</th>
              <th className="pb-2 font-normal">Pente</th>
            </tr>
          </thead>
          <tbody className="tabular">
            {sortedPhases.map((p, i) => {
              const q = phaseTdeeQueries[i];
              if (q.isLoading) {
                return (
                  <tr key={p.id} className="border-t border-line">
                    <td className="py-2 text-text-high">{p.name}</td>
                    <td className="py-2 text-text-mid" colSpan={3}>
                      Chargement…
                    </td>
                  </tr>
                );
              }
              if (!q.data || !q.data.is_valid) {
                return (
                  <tr key={p.id} className="border-t border-line">
                    <td className="py-2 text-text-high">{p.name}</td>
                    <td className="py-2 text-text-mid" colSpan={3}>
                      {q.data?.reason ?? "Indisponible"}
                    </td>
                  </tr>
                );
              }
              return (
                <tr key={p.id} className="border-t border-line">
                  <td className="py-2 text-text-high">{p.name}</td>
                  <td className="py-2">
                    {q.data.tdee_kcal !== null ? `${Math.round(q.data.tdee_kcal)} kcal/j` : <EmptyValue />}
                  </td>
                  <td className="py-2">
                    {q.data.mean_intake_kcal !== null ? `${Math.round(q.data.mean_intake_kcal)} kcal/j` : <EmptyValue />}
                  </td>
                  <td className="py-2">
                    {monthlySlope(q.data.weight_slope_kg_per_day) !== null
                      ? `${monthlySlope(q.data.weight_slope_kg_per_day)} kg/mois`
                      : <EmptyValue />}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </DomainCard>
    </div>
  );
}
