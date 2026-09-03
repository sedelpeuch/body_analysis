import { Link } from "react-router-dom";
import { useCurrentPhase, usePhaseReport } from "../../api/phases/hooks";
import { useBodySummary } from "../../api/body/hooks";
import { useWorkouts } from "../../api/workouts/hooks";
import { usePhotos, photoImageUrl } from "../../api/photos/hooks";
import { DomainCard } from "../../components/domain-card/DomainCard";
import { PhotoImage } from "../../components/photo/PhotoImage";
import { ProgressRing } from "../../components/charts/ProgressRing";
import { EmptyValue } from "../../components/empty-state/EmptyValue";
import { formatDelta, formatDuration } from "../../lib/format";

export function TodayPage() {
  const currentPhase = useCurrentPhase();
  const phaseId = currentPhase.data?.id;
  const phaseReport = usePhaseReport(phaseId);
  const bodySummary = useBodySummary();
  const workouts = useWorkouts({ limit: 5 });
  const photos = usePhotos();
  const lastPhoto = photos.data
    ?.slice()
    .sort((a, b) => b.taken_on.localeCompare(a.taken_on))
    .at(0);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl">Aujourd'hui</h1>
        <p className="text-text-mid">Phase en cours, progression vers les objectifs, dernières séances, dernière photo.</p>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <DomainCard variant="phase" title="Phase en cours">
          {currentPhase.isLoading ? (
            <p className="text-sm text-text-mid">Chargement…</p>
          ) : !currentPhase.data ? (
            <p className="text-sm text-text-mid">Aucune phase en cours.</p>
          ) : (
            <div className="flex flex-col gap-3">
              <div>
                <p className="text-sm text-text-high">{currentPhase.data.name}</p>
                <p className="tabular text-xs text-text-mid">
                  {currentPhase.data.starts_on} → {currentPhase.data.ends_on}
                </p>
              </div>
              <div className="flex flex-wrap gap-4">
                {phaseReport.data?.metrics
                  .filter((m) => m.objective !== null)
                  .map((m) => {
                    const objective = m.objective!;
                    const current = objective.current ?? objective.target;
                    return (
                      <ProgressRing
                        key={m.metric}
                        label={m.metric}
                        value={Math.abs(current - (m.start_value ?? current))}
                        max={Math.abs(objective.target - (m.start_value ?? objective.target)) || 1}
                      />
                    );
                  })}
              </div>
            </div>
          )}
        </DomainCard>

        <DomainCard variant="body" title="Dernières valeurs">
          {bodySummary.isLoading ? (
            <p className="text-sm text-text-mid">Chargement…</p>
          ) : (
            <div className="flex flex-col gap-2">
              <p className="tabular text-lg text-text-high">
                {bodySummary.data?.latest?.weight_kg ?? <EmptyValue />} kg
              </p>
              <div className="flex flex-col gap-1">
                {bodySummary.data?.weight_deltas.map((d) => (
                  <p key={d.window_days} className="tabular text-xs text-text-mid">
                    {d.window_days} j : {formatDelta(d.change, "kg")}
                  </p>
                ))}
              </div>
            </div>
          )}
        </DomainCard>

        <DomainCard variant="training" title="Dernières séances">
          {workouts.isLoading ? (
            <p className="text-sm text-text-mid">Chargement…</p>
          ) : (
            <ul className="flex flex-col gap-2">
              {workouts.data?.pages[0]?.items.map((w) => (
                <li key={w.id}>
                  <Link to={`/entrainement/${w.id}`} className="flex items-center justify-between text-sm hover:text-text-high">
                    <span className="text-text-mid">{w.sport}</span>
                    <span className="tabular text-text-high">{w.duration_ms !== null ? formatDuration(w.duration_ms) : <EmptyValue />}</span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </DomainCard>

        <DomainCard variant="body" title="Dernière photo">
          {photos.isLoading ? (
            <p className="text-sm text-text-mid">Chargement…</p>
          ) : !lastPhoto ? (
            <p className="text-sm text-text-mid">Aucune photo.</p>
          ) : (
            <PhotoImage
              src={photoImageUrl(lastPhoto.id, "medium", false)}
              alt={`Photo ${lastPhoto.tag} du ${lastPhoto.taken_on}`}
              className="h-40 w-full rounded-card object-cover"
            />
          )}
        </DomainCard>
      </div>
    </div>
  );
}
