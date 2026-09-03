import { useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { usePhase, usePhaseReport, useDeletePhaseMutation } from "../../api/phases/hooks";
import { useTimeseries } from "../../api/body/hooks";
import { mergeTimeseries } from "../../api/body/mapping";
import { usePhotos, photoImageUrl } from "../../api/photos/hooks";
import { DomainCard } from "../../components/domain-card/DomainCard";
import { LineSeriesCard } from "../../components/charts/LineSeriesCard";
import { PhotoImage } from "../../components/photo/PhotoImage";
import { PhotoLightbox } from "../../components/photo/PhotoLightbox";
import { ObjectiveSummary } from "../../components/objective/ObjectiveSummary";
import { Button } from "../../components/ui/button";
import { formatDelta } from "../../lib/format";
import { METRIC_COLOR, METRIC_LABEL, OBJECTIVE_UNIT, OBJECTIVE_DELTA_UNIT } from "../../lib/metric-config";
import type { PhotoOut } from "../../api/types";
import { PhaseForm } from "./PhaseForm";

function groupPhotosByTag(photos: PhotoOut[]): [string, PhotoOut[]][] {
  const byTag = new Map<string, PhotoOut[]>();
  for (const photo of photos) {
    const list = byTag.get(photo.tag) ?? [];
    list.push(photo);
    byTag.set(photo.tag, list);
  }
  for (const list of byTag.values()) list.sort((a, b) => a.taken_on.localeCompare(b.taken_on));
  return Array.from(byTag.entries()).sort(([a], [b]) => a.localeCompare(b));
}

export function PhaseDetailPage() {
  const { id } = useParams();
  const phaseId = Number(id);
  const navigate = useNavigate();

  const phase = usePhase(phaseId);
  const report = usePhaseReport(phaseId);
  const photos = usePhotos();
  const deleteMutation = useDeletePhaseMutation();
  const [editOpen, setEditOpen] = useState(false);
  const [lightbox, setLightbox] = useState<{ src: string; alt: string } | null>(null);

  const timeseries = useTimeseries({
    from: phase.data?.starts_on,
    to: phase.data?.ends_on,
    metrics: "weight,body_fat,muscle",
    resolution: "daily",
  });
  const chartData = useMemo(() => (timeseries.data ? mergeTimeseries(timeseries.data) : []), [timeseries.data]);

  const periodPhotosByTag = useMemo(() => {
    if (!phase.data || !photos.data) return [];
    const inPeriod = photos.data.filter((p) => p.taken_on >= phase.data!.starts_on && p.taken_on <= phase.data!.ends_on);
    return groupPhotosByTag(inPeriod);
  }, [phase.data, photos.data]);

  if (phase.isLoading) return <p className="text-sm text-text-mid">Chargement…</p>;
  if (!phase.data) return <p className="text-sm text-text-mid">Phase introuvable.</p>;

  function handleDelete() {
    if (!confirm(`Supprimer la phase "${phase.data!.name}" ?`)) return;
    deleteMutation.mutate(phaseId, { onSuccess: () => navigate("/phases") });
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl">{phase.data.name}</h1>
          <p className="tabular text-text-mid">
            {phase.data.starts_on} → {phase.data.ends_on}
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setEditOpen(true)}>
            Modifier
          </Button>
          <Button variant="destructive" onClick={handleDelete}>
            Supprimer
          </Button>
        </div>
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

      {/* Un graphique par métrique : mélanger kg et % sur un même axe lisse
          visuellement les séries à plus faible variation. */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <DomainCard variant="phase" title="Poids (kg)">
          {timeseries.isLoading ? (
            <p className="text-sm text-text-mid">Chargement…</p>
          ) : (
            <LineSeriesCard data={chartData} xKey="at" series={[{ key: "weight", label: "Poids (kg)", color: METRIC_COLOR.weight }]} />
          )}
        </DomainCard>
        <DomainCard variant="phase" title="Masse grasse (%)">
          {timeseries.isLoading ? (
            <p className="text-sm text-text-mid">Chargement…</p>
          ) : (
            <LineSeriesCard
              data={chartData}
              xKey="at"
              series={[{ key: "body_fat", label: "Masse grasse (%)", color: METRIC_COLOR.body_fat }]}
            />
          )}
        </DomainCard>
        <DomainCard variant="phase" title="Muscle (%)">
          {timeseries.isLoading ? (
            <p className="text-sm text-text-mid">Chargement…</p>
          ) : (
            <LineSeriesCard data={chartData} xKey="at" series={[{ key: "muscle", label: "Muscle (%)", color: METRIC_COLOR.muscle }]} />
          )}
        </DomainCard>
      </div>

      {periodPhotosByTag.length > 0 && (
        <DomainCard variant="phase" title="Photos de la période — par tag, par date">
          <div className="flex flex-col gap-4">
            {periodPhotosByTag.map(([tag, tagPhotos]) => (
              <div key={tag} className="flex flex-col gap-2">
                <span className="text-xs text-text-mid">{tag}</span>
                <div className="flex flex-wrap gap-2">
                  {tagPhotos.map((p) => (
                    <button
                      key={p.id}
                      type="button"
                      onClick={() =>
                        setLightbox({ src: photoImageUrl(p.id, "full", false), alt: `Photo ${p.tag} du ${p.taken_on}` })
                      }
                      className="flex w-40 flex-col gap-1 text-left transition-opacity hover:opacity-80"
                    >
                      <PhotoImage
                        src={photoImageUrl(p.id, "medium", false)}
                        alt={`Photo ${p.tag} du ${p.taken_on}`}
                        className="aspect-square w-full rounded-card object-cover"
                      />
                      <span className="tabular text-center text-xs text-text-mid">{p.taken_on}</span>
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </DomainCard>
      )}

      <PhaseForm open={editOpen} onOpenChange={setEditOpen} phase={phase.data} />
      <PhotoLightbox photo={lightbox} onClose={() => setLightbox(null)} />
    </div>
  );
}
