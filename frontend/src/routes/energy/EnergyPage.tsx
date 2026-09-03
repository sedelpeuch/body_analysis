import { useMemo, useState } from "react";
import { usePhases } from "../../api/phases/hooks";
import { useEnergyBalance, useTdee } from "../../api/analytics/hooks";
import { useComposition } from "../../api/body/hooks";
import { DomainCard } from "../../components/domain-card/DomainCard";
import { StatTile } from "../../components/charts/StatTile";
import { LineSeriesCard } from "../../components/charts/LineSeriesCard";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select";

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
                value={tdee.data?.weight_slope_kg_per_day ?? null}
                unit="kg/j"
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
    </div>
  );
}
