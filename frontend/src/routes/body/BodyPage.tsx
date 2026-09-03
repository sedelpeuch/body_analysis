import { useMemo, useState } from "react";
import { useComposition, useTimeseries } from "../../api/body/hooks";
import { mergeTimeseries } from "../../api/body/mapping";
import { usePhases } from "../../api/phases/hooks";
import { DomainCard } from "../../components/domain-card/DomainCard";
import { LineSeriesCard } from "../../components/charts/LineSeriesCard";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select";
import { phaseBands } from "../../lib/phase-bands";
import { METRIC_COLOR } from "../../lib/metric-config";

export function BodyPage() {
  const phases = usePhases();
  const [phaseId, setPhaseId] = useState<number | undefined>(undefined);
  const selectedPhase = phases.data?.find((p) => p.id === phaseId);
  const range = { from: selectedPhase?.starts_on, to: selectedPhase?.ends_on };

  const timeseries = useTimeseries({ ...range, metrics: "weight,body_fat,muscle", resolution: "daily" });
  const composition = useComposition(range);

  const percentSeries = useMemo(
    () => (timeseries.data ? mergeTimeseries(timeseries.data) : []),
    [timeseries.data],
  );
  const compositionSeries = useMemo(
    () => composition.data?.map((p) => ({ ...p, at: p.day })) ?? [],
    [composition.data],
  );

  const percentBands = useMemo(
    () => phaseBands(phases.data ?? [], percentSeries.map((p) => p.at as string)),
    [phases.data, percentSeries],
  );
  const compositionBands = useMemo(
    () => phaseBands(phases.data ?? [], compositionSeries.map((p) => p.at)),
    [phases.data, compositionSeries],
  );

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl">Corps</h1>
          <p className="text-text-mid">
            Poids, masse grasse, masse musculaire, masse maigre, eau — bandes de phases superposées.
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

      {/* Un graphique par métrique plutôt qu'un axe partagé : des échelles
          aussi différentes (kg contre %) lissent visuellement les séries
          aux plus petites variations quand elles sont superposées. */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <DomainCard variant="body" title="Poids (kg)">
          {timeseries.isLoading ? (
            <p className="text-sm text-text-mid">Chargement…</p>
          ) : (
            <LineSeriesCard
              data={percentSeries}
              xKey="at"
              phaseBands={percentBands}
              series={[{ key: "weight", label: "Poids (kg)", color: METRIC_COLOR.weight }]}
            />
          )}
        </DomainCard>
        <DomainCard variant="body" title="Masse grasse (%)">
          {timeseries.isLoading ? (
            <p className="text-sm text-text-mid">Chargement…</p>
          ) : (
            <LineSeriesCard
              data={percentSeries}
              xKey="at"
              phaseBands={percentBands}
              series={[{ key: "body_fat", label: "Masse grasse (%)", color: METRIC_COLOR.body_fat }]}
            />
          )}
        </DomainCard>
        <DomainCard variant="body" title="Muscle (%)">
          {timeseries.isLoading ? (
            <p className="text-sm text-text-mid">Chargement…</p>
          ) : (
            <LineSeriesCard
              data={percentSeries}
              xKey="at"
              phaseBands={percentBands}
              series={[{ key: "muscle", label: "Muscle (%)", color: METRIC_COLOR.muscle }]}
            />
          )}
        </DomainCard>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <DomainCard variant="body" title="Masse grasse (kg)">
          {composition.isLoading ? (
            <p className="text-sm text-text-mid">Chargement…</p>
          ) : (
            <LineSeriesCard
              data={compositionSeries}
              xKey="at"
              phaseBands={compositionBands}
              series={[{ key: "body_fat_mass_kg", label: "Masse grasse (kg)", color: METRIC_COLOR.body_fat }]}
            />
          )}
        </DomainCard>
        <DomainCard variant="body" title="Masse maigre (kg)">
          {composition.isLoading ? (
            <p className="text-sm text-text-mid">Chargement…</p>
          ) : (
            <LineSeriesCard
              data={compositionSeries}
              xKey="at"
              phaseBands={compositionBands}
              series={[{ key: "fat_free_mass_kg", label: "Masse maigre (kg)" }]}
            />
          )}
        </DomainCard>
        <DomainCard variant="body" title="Muscle (kg)">
          {composition.isLoading ? (
            <p className="text-sm text-text-mid">Chargement…</p>
          ) : (
            <LineSeriesCard
              data={compositionSeries}
              xKey="at"
              phaseBands={compositionBands}
              series={[{ key: "skeletal_muscle_mass_kg", label: "Muscle (kg)", color: METRIC_COLOR.muscle }]}
            />
          )}
        </DomainCard>
        <DomainCard variant="body" title="Eau (kg)">
          {composition.isLoading ? (
            <p className="text-sm text-text-mid">Chargement…</p>
          ) : (
            <LineSeriesCard
              data={compositionSeries}
              xKey="at"
              phaseBands={compositionBands}
              series={[{ key: "total_body_water_kg", label: "Eau (kg)" }]}
            />
          )}
        </DomainCard>
      </div>
    </div>
  );
}
