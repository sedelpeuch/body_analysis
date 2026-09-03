import { useParams } from "react-router-dom";
import {
  useWorkout,
  useWorkoutSamples,
  useWorkoutTrack,
  useWorkoutSplits,
  useWorkoutHrZones,
  useWorkoutCardiacDrift,
} from "../../api/workouts/hooks";
import { DomainCard } from "../../components/domain-card/DomainCard";
import { StatTile } from "../../components/charts/StatTile";
import { LineSeriesCard } from "../../components/charts/LineSeriesCard";
import { EmptyValue } from "../../components/empty-state/EmptyValue";
import { formatDuration, formatPace } from "../../lib/format";
import { WorkoutMap } from "./WorkoutMap";
import { SwimSection } from "./SwimSection";
import { StrengthSection } from "./StrengthSection";

export function WorkoutDetailPage() {
  const { id } = useParams();
  const workoutId = Number(id);

  const workout = useWorkout(workoutId);
  const samples = useWorkoutSamples(workoutId);
  const track = useWorkoutTrack(workoutId);
  const splits = useWorkoutSplits(workoutId);
  const hrZones = useWorkoutHrZones(workoutId);
  const cardiacDrift = useWorkoutCardiacDrift(workoutId);

  if (workout.isLoading) return <p className="text-sm text-text-mid">Chargement…</p>;
  if (!workout.data) return <p className="text-sm text-text-mid">Séance introuvable.</p>;

  const w = workout.data;

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl">{w.sport}</h1>
        <p className="tabular text-text-mid">{new Date(w.started_at).toLocaleString("fr-FR")}</p>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
        <DomainCard variant="training" title="Durée">
          <StatTile label="Durée" value={w.duration_ms !== null ? formatDuration(w.duration_ms) : null} />
        </DomainCard>
        <DomainCard variant="training" title="Distance">
          <StatTile label="Distance" value={w.distance_m !== null ? Math.round(w.distance_m / 1000 * 100) / 100 : null} unit="km" />
        </DomainCard>
        <DomainCard variant="training" title="Calories">
          <StatTile label="Calories" value={w.calories_kcal !== null ? Math.round(w.calories_kcal) : null} unit="kcal" />
        </DomainCard>
        <DomainCard variant="training" title="FC moyenne">
          <StatTile label="FC moyenne" value={w.mean_heart_rate !== null ? Math.round(w.mean_heart_rate) : null} unit="bpm" />
        </DomainCard>
        <DomainCard variant="training" title="FC max">
          <StatTile label="FC max" value={w.max_heart_rate !== null ? Math.round(w.max_heart_rate) : null} unit="bpm" />
        </DomainCard>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <DomainCard variant="training" title="FC min">
          <StatTile label="FC min" value={w.min_heart_rate !== null ? Math.round(w.min_heart_rate) : null} unit="bpm" />
        </DomainCard>
        <DomainCard variant="training" title="FC de repos">
          <StatTile label="FC de repos" value={w.resting_hr} unit="bpm" />
        </DomainCard>
        <DomainCard variant="training" title="Dénivelé positif">
          <StatTile label="D+" value={w.altitude_gain_m !== null ? Math.round(w.altitude_gain_m) : null} unit="m" />
        </DomainCard>
        <DomainCard variant="training" title="Dénivelé négatif">
          <StatTile label="D-" value={w.altitude_loss_m !== null ? Math.round(w.altitude_loss_m) : null} unit="m" />
        </DomainCard>
      </div>

      {w.has_samples && (
        // Un graphique par mesure : bpm, m/s et mètres n'ont rien de
        // comparable sur un même axe, ça écraserait les deux plus petites.
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <DomainCard variant="training" title="FC (bpm)">
            {samples.isLoading ? (
              <p className="text-sm text-text-mid">Chargement…</p>
            ) : (
              <LineSeriesCard data={samples.data ?? []} xKey="at" series={[{ key: "heart_rate", label: "FC (bpm)" }]} />
            )}
          </DomainCard>
          <DomainCard variant="training" title="Vitesse (m/s)">
            {samples.isLoading ? (
              <p className="text-sm text-text-mid">Chargement…</p>
            ) : (
              <LineSeriesCard data={samples.data ?? []} xKey="at" series={[{ key: "speed_mps", label: "Vitesse (m/s)" }]} />
            )}
          </DomainCard>
          <DomainCard variant="training" title="Altitude (m)">
            {samples.isLoading ? (
              <p className="text-sm text-text-mid">Chargement…</p>
            ) : (
              <LineSeriesCard data={samples.data ?? []} xKey="at" series={[{ key: "altitude_m", label: "Altitude (m)" }]} />
            )}
          </DomainCard>
        </div>
      )}

      {w.has_locations && (
        <DomainCard variant="training" title="Trace GPS">
          {track.data ? <WorkoutMap track={track.data} /> : <p className="text-sm text-text-mid">Chargement…</p>}
        </DomainCard>
      )}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <DomainCard variant="training" title="Dérive cardiaque">
          {cardiacDrift.isLoading ? (
            <p className="text-sm text-text-mid">Chargement…</p>
          ) : cardiacDrift.data?.drift_pct === null || cardiacDrift.data?.drift_pct === undefined ? (
            <p className="text-sm text-text-mid">Pas assez d'échantillons FC.</p>
          ) : (
            <div className="flex flex-col gap-2">
              <p className="tabular text-sm text-text-mid">
                1ère moitié : <span className="text-text-high">{Math.round(cardiacDrift.data.first_half_mean_hr!)} bpm</span>
              </p>
              <p className="tabular text-sm text-text-mid">
                2e moitié : <span className="text-text-high">{Math.round(cardiacDrift.data.second_half_mean_hr!)} bpm</span>
              </p>
              <p className="tabular text-lg text-text-high">
                {cardiacDrift.data.drift_pct > 0 ? "+" : ""}
                {Math.round(cardiacDrift.data.drift_pct * 10) / 10}%
              </p>
              <p className="text-xs text-text-mid">
                Écart de FC moyenne entre la 1ère et la 2e moitié de la séance, à effort comparable. Une dérive
                positive signifie que le cœur travaille plus pour le même effort au fil de la séance (fatigue,
                chaleur, déshydratation).{" "}
                {cardiacDrift.data.drift_pct > 5
                  ? "Au-delà de +5 %, c'est un signal de fatigue ou de sous-récupération à surveiller."
                  : "Sous +5 %, c'est le signe d'un bon état de forme et d'un pacing maîtrisé."}
              </p>
            </div>
          )}
        </DomainCard>

        <DomainCard variant="training" title="Temps par zone cardiaque">
          {hrZones.isError ? (
            <p className="text-sm text-text-mid">FC max indisponible pour cette séance.</p>
          ) : hrZones.isLoading ? (
            <p className="text-sm text-text-mid">Chargement…</p>
          ) : (
            <ul className="flex flex-col gap-2">
              {hrZones.data?.map((z) => (
                <li key={z.zone} className="tabular flex justify-between text-sm">
                  <span className="text-text-mid">{z.label}</span>
                  <span className="text-text-high">{formatDuration(z.seconds * 1000)}</span>
                </li>
              ))}
            </ul>
          )}
        </DomainCard>

        <DomainCard variant="training" title="Splits au kilomètre">
          {splits.isLoading ? (
            <p className="text-sm text-text-mid">Chargement…</p>
          ) : splits.data?.length === 0 ? (
            <p className="text-sm text-text-mid">Aucun split disponible.</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-text-mid">
                  <th className="pb-2 font-normal">Km</th>
                  <th className="pb-2 font-normal">Allure</th>
                  <th className="pb-2 font-normal">FC moyenne</th>
                </tr>
              </thead>
              <tbody className="tabular">
                {splits.data?.map((s) => (
                  <tr key={s.index} className="border-t border-line">
                    <td className="py-2 text-text-high">{s.index}</td>
                    <td className="py-2">{formatPace(s.pace_s_per_km)}</td>
                    <td className="py-2">{s.mean_heart_rate !== null ? Math.round(s.mean_heart_rate) : <EmptyValue />}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </DomainCard>
      </div>

      {w.has_swim_lengths && <SwimSection workoutId={workoutId} />}
      {w.has_strength_sets && <StrengthSection workoutId={workoutId} />}
    </div>
  );
}
