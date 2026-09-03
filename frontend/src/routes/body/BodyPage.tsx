import { useMemo, useState } from "react";
import { useComposition, useTimeseries } from "../../api/body/hooks";
import { mergeTimeseries } from "../../api/body/mapping";
import { usePhases } from "../../api/phases/hooks";
import { DomainCard } from "../../components/domain-card/DomainCard";
import { LineSeriesCard } from "../../components/charts/LineSeriesCard";
import { phaseBands } from "../../lib/phase-bands";

function isoDaysAgo(days: number): string {
  const date = new Date();
  date.setDate(date.getDate() - days);
  return date.toISOString().slice(0, 10);
}

export function BodyPage() {
  const [from, setFrom] = useState(() => isoDaysAgo(90));
  const [to, setTo] = useState(() => isoDaysAgo(0));

  const timeseries = useTimeseries({ from, to, metrics: "weight,body_fat,muscle", resolution: "daily" });
  const composition = useComposition({ from, to });
  const phases = usePhases();

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
        <div className="flex items-center gap-2 text-sm">
          <label className="flex items-center gap-1 text-text-mid">
            Du
            <input
              type="date"
              value={from}
              onChange={(e) => setFrom(e.target.value)}
              className="rounded-card border border-line bg-surface px-2 py-1 text-text-high"
            />
          </label>
          <label className="flex items-center gap-1 text-text-mid">
            Au
            <input
              type="date"
              value={to}
              onChange={(e) => setTo(e.target.value)}
              className="rounded-card border border-line bg-surface px-2 py-1 text-text-high"
            />
          </label>
        </div>
      </div>

      <DomainCard variant="body" title="Poids, masse grasse et masse musculaire (%)">
        {timeseries.isLoading ? (
          <p className="text-sm text-text-mid">Chargement…</p>
        ) : (
          <LineSeriesCard
            data={percentSeries}
            xKey="at"
            phaseBands={percentBands}
            series={[
              { key: "weight", label: "Poids (kg)" },
              { key: "body_fat", label: "Masse grasse (%)" },
              { key: "muscle", label: "Muscle (%)" },
            ]}
          />
        )}
      </DomainCard>

      <DomainCard variant="body" title="Masses en kilogrammes">
        {composition.isLoading ? (
          <p className="text-sm text-text-mid">Chargement…</p>
        ) : (
          <LineSeriesCard
            data={compositionSeries}
            xKey="at"
            phaseBands={compositionBands}
            series={[
              { key: "body_fat_mass_kg", label: "Masse grasse (kg)" },
              { key: "fat_free_mass_kg", label: "Masse maigre (kg)" },
              { key: "skeletal_muscle_mass_kg", label: "Muscle (kg)" },
              { key: "total_body_water_kg", label: "Eau (kg)" },
            ]}
          />
        )}
      </DomainCard>
    </div>
  );
}
