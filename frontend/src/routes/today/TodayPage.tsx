import { useMemo, useState } from "react";
import { useCurrentPhase, usePhaseReport, usePhases } from "../../api/phases/hooks";
import { useTimeseries } from "../../api/body/hooks";
import { mergeTimeseries } from "../../api/body/mapping";
import { usePhotos, photoImageUrl } from "../../api/photos/hooks";
import { DomainCard } from "../../components/domain-card/DomainCard";
import { LineSeriesCard } from "../../components/charts/LineSeriesCard";
import { PhotoImage } from "../../components/photo/PhotoImage";
import { PhotoLightbox } from "../../components/photo/PhotoLightbox";
import { ObjectiveSummary } from "../../components/objective/ObjectiveSummary";
import { formatDelta } from "../../lib/format";
import { pickPhaseComparisonPhotos } from "../../lib/phase-comparison-photos";
import { METRIC_COLOR, METRIC_LABEL, OBJECTIVE_UNIT, OBJECTIVE_DELTA_UNIT } from "../../lib/metric-config";

const PHOTO_TAGS = ["face", "profil", "dos", "bras", "epaule"] as const;

function daysRemaining(endsOn: string): number {
  const today = new Date();
  const end = new Date(endsOn);
  return Math.round((end.getTime() - Date.UTC(today.getFullYear(), today.getMonth(), today.getDate())) / 86_400_000);
}

export function TodayPage() {
  const [lightbox, setLightbox] = useState<{ src: string; alt: string } | null>(null);
  const currentPhase = useCurrentPhase();
  const phases = usePhases();
  const phaseId = currentPhase.data?.id;
  const report = usePhaseReport(phaseId);
  const photos = usePhotos();

  const previousPhase = useMemo(() => {
    if (!phases.data || !currentPhase.data) return undefined;
    const sorted = [...phases.data].sort((a, b) => a.starts_on.localeCompare(b.starts_on));
    const index = sorted.findIndex((p) => p.id === currentPhase.data!.id);
    return index > 0 ? sorted[index - 1] : undefined;
  }, [phases.data, currentPhase.data]);

  const timeseries = useTimeseries(
    {
      from: currentPhase.data?.starts_on,
      to: currentPhase.data?.ends_on,
      metrics: "weight,body_fat,muscle",
      resolution: "daily",
    },
    { enabled: currentPhase.data !== undefined },
  );
  const chartData = useMemo(() => (timeseries.data ? mergeTimeseries(timeseries.data) : []), [timeseries.data]);

  const comparisonPhotos = useMemo(
    () =>
      currentPhase.data
        ? pickPhaseComparisonPhotos(photos.data ?? [], PHOTO_TAGS, previousPhase, currentPhase.data)
        : [],
    [photos.data, previousPhase, currentPhase.data],
  );

  if (currentPhase.isLoading) return <p className="text-sm text-text-mid">Chargement…</p>;

  if (!currentPhase.data) {
    return (
      <div>
        <h1 className="text-2xl">Phase en cours</h1>
        <p className="text-text-mid">Aucune phase en cours. Créez-en une depuis /phases.</p>
      </div>
    );
  }

  const phase = currentPhase.data;
  const remaining = daysRemaining(phase.ends_on);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl">{phase.name}</h1>
        <p className="tabular text-text-mid">
          {phase.starts_on} → {phase.ends_on} · {remaining >= 0 ? `${remaining} j restants` : "terminée"}
        </p>
      </div>

      <DomainCard variant="phase" title="Objectifs">
        {report.isLoading ? (
          <p className="text-sm text-text-mid">Chargement…</p>
        ) : (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
            {report.data?.metrics
              .filter((m) => m.objective !== null)
              .map((m) => (
                <ObjectiveSummary
                  key={m.metric}
                  label={METRIC_LABEL[m.metric]}
                  color={METRIC_COLOR[m.metric]}
                  unit={OBJECTIVE_UNIT[m.metric]}
                  deltaUnit={OBJECTIVE_DELTA_UNIT[m.metric]}
                  start={m.start_value}
                  current={m.objective!.current}
                  target={m.objective!.target}
                  direction={m.objective!.direction}
                  changeAbs={m.change}
                  monthlyRateAbs={m.monthly_rate}
                />
              ))}
          </div>
        )}
      </DomainCard>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <DomainCard variant="phase" title="Calories moyennes">
          <p className="tabular text-xl text-text-high">
            {report.data?.average_calories_kcal !== null && report.data?.average_calories_kcal !== undefined
              ? `${Math.round(report.data.average_calories_kcal)} kcal`
              : "—"}
          </p>
        </DomainCard>
        <DomainCard variant="phase" title="Recomposition corporelle">
          <div className="flex gap-6">
            <p className="tabular text-sm text-text-high">
              Masse grasse : {formatDelta(report.data?.recomposition.fat_mass_delta_kg ?? null, "kg")}
            </p>
            <p className="tabular text-sm text-text-high">
              Masse maigre : {formatDelta(report.data?.recomposition.lean_mass_delta_kg ?? null, "kg")}
            </p>
          </div>
        </DomainCard>
      </div>

      {/* Un graphique par métrique : kg et % sur un même axe lisseraient
          visuellement les séries à plus faible variation. */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <DomainCard variant="body" title="Poids (kg)">
          {timeseries.isLoading ? (
            <p className="text-sm text-text-mid">Chargement…</p>
          ) : (
            <LineSeriesCard data={chartData} xKey="at" series={[{ key: "weight", label: "Poids (kg)", color: METRIC_COLOR.weight }]} />
          )}
        </DomainCard>
        <DomainCard variant="body" title="Masse grasse (%)">
          {timeseries.isLoading ? (
            <p className="text-sm text-text-mid">Chargement…</p>
          ) : (
            <LineSeriesCard data={chartData} xKey="at" series={[{ key: "body_fat", label: "Masse grasse (%)", color: METRIC_COLOR.body_fat }]} />
          )}
        </DomainCard>
        <DomainCard variant="body" title="Muscle (%)">
          {timeseries.isLoading ? (
            <p className="text-sm text-text-mid">Chargement…</p>
          ) : (
            <LineSeriesCard data={chartData} xKey="at" series={[{ key: "muscle", label: "Muscle (%)", color: METRIC_COLOR.muscle }]} />
          )}
        </DomainCard>
      </div>

      <DomainCard variant="body" title={previousPhase ? "Avant / après — phase précédente contre phase en cours" : "Photos de la phase en cours"}>
        {photos.isLoading ? (
          <p className="text-sm text-text-mid">Chargement…</p>
        ) : (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3">
            {comparisonPhotos
              .filter((entry) => entry.before || entry.after)
              .map((entry) => (
                <div key={entry.tag} className="flex flex-col gap-2">
                  <span className="text-xs text-text-mid">{entry.tag}</span>
                  <div className="grid grid-cols-2 gap-2">
                    {entry.before ? (
                      <button
                        type="button"
                        onClick={() =>
                          setLightbox({
                            src: photoImageUrl(entry.before!.id, "full", false),
                            alt: `${entry.tag} avant, ${entry.before!.taken_on}`,
                          })
                        }
                        className="transition-opacity hover:opacity-80"
                      >
                        <PhotoImage
                          src={photoImageUrl(entry.before.id, "medium", false)}
                          alt={`${entry.tag} avant, ${entry.before.taken_on}`}
                          className="aspect-square w-full rounded-card object-cover"
                        />
                      </button>
                    ) : (
                      <div className="flex aspect-square items-center justify-center rounded-card bg-surface-raised text-xs text-text-mid">
                        —
                      </div>
                    )}
                    {entry.after ? (
                      <button
                        type="button"
                        onClick={() =>
                          setLightbox({
                            src: photoImageUrl(entry.after!.id, "full", false),
                            alt: `${entry.tag} après, ${entry.after!.taken_on}`,
                          })
                        }
                        className="transition-opacity hover:opacity-80"
                      >
                        <PhotoImage
                          src={photoImageUrl(entry.after.id, "medium", false)}
                          alt={`${entry.tag} après, ${entry.after.taken_on}`}
                          className="aspect-square w-full rounded-card object-cover"
                        />
                      </button>
                    ) : (
                      <div className="flex aspect-square items-center justify-center rounded-card bg-surface-raised text-xs text-text-mid">
                        —
                      </div>
                    )}
                  </div>
                </div>
              ))}
          </div>
        )}
      </DomainCard>
      <PhotoLightbox photo={lightbox} onClose={() => setLightbox(null)} />
    </div>
  );
}
