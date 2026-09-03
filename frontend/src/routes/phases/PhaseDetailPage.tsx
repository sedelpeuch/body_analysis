import { useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { usePhase, usePhaseReport, useDeletePhaseMutation } from "../../api/phases/hooks";
import { useTimeseries } from "../../api/body/hooks";
import { mergeTimeseries } from "../../api/body/mapping";
import { usePhotos, photoImageUrl } from "../../api/photos/hooks";
import { DomainCard } from "../../components/domain-card/DomainCard";
import { ProgressRing } from "../../components/charts/ProgressRing";
import { LineSeriesCard } from "../../components/charts/LineSeriesCard";
import { PhotoImage } from "../../components/photo/PhotoImage";
import { Button } from "../../components/ui/button";
import { formatDelta } from "../../lib/format";
import { PhaseForm } from "./PhaseForm";

export function PhaseDetailPage() {
  const { id } = useParams();
  const phaseId = Number(id);
  const navigate = useNavigate();

  const phase = usePhase(phaseId);
  const report = usePhaseReport(phaseId);
  const photos = usePhotos();
  const deleteMutation = useDeletePhaseMutation();
  const [editOpen, setEditOpen] = useState(false);

  const timeseries = useTimeseries({
    from: phase.data?.starts_on,
    to: phase.data?.ends_on,
    metrics: "weight,body_fat,muscle",
    resolution: "daily",
  });
  const chartData = useMemo(() => (timeseries.data ? mergeTimeseries(timeseries.data) : []), [timeseries.data]);

  const periodPhotos = useMemo(() => {
    if (!phase.data || !photos.data) return [];
    return photos.data.filter((p) => p.taken_on >= phase.data!.starts_on && p.taken_on <= phase.data!.ends_on);
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
          <div className="flex flex-wrap gap-6">
            {report.data?.metrics
              .filter((m) => m.objective !== null)
              .map((m) => {
                const objective = m.objective!;
                const current = objective.current ?? objective.target;
                const start = m.start_value ?? current;
                return (
                  <ProgressRing
                    key={m.metric}
                    label={m.metric}
                    value={Math.abs(current - start)}
                    max={Math.abs(objective.target - start) || 1}
                  />
                );
              })}
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

      <DomainCard variant="phase" title="Courbes de la période">
        {timeseries.isLoading ? (
          <p className="text-sm text-text-mid">Chargement…</p>
        ) : (
          <LineSeriesCard
            data={chartData}
            xKey="at"
            series={[
              { key: "weight", label: "Poids (kg)" },
              { key: "body_fat", label: "Masse grasse (%)" },
              { key: "muscle", label: "Muscle (%)" },
            ]}
          />
        )}
      </DomainCard>

      {periodPhotos.length > 0 && (
        <DomainCard variant="phase" title="Photos de la période">
          <div className="grid grid-cols-4 gap-2">
            {periodPhotos.map((p) => (
              <PhotoImage
                key={p.id}
                src={photoImageUrl(p.id, "thumb", false)}
                alt={`Photo ${p.tag} du ${p.taken_on}`}
                className="aspect-square w-full rounded-card object-cover"
              />
            ))}
          </div>
        </DomainCard>
      )}

      <PhaseForm open={editOpen} onOpenChange={setEditOpen} phase={phase.data} />
    </div>
  );
}
