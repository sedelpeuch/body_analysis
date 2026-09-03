import { useState } from "react";
import {
  useSports,
  useWorkoutCalendar,
  useWorkoutRecords,
  useWorkoutStats,
  useWorkouts,
} from "../../api/workouts/hooks";
import { useTrainingLoad, useRestingHr } from "../../api/analytics/hooks";
import { usePhases } from "../../api/phases/hooks";
import { DomainCard } from "../../components/domain-card/DomainCard";
import { CalendarHeatmap } from "../../components/charts/CalendarHeatmap";
import { StatTile } from "../../components/charts/StatTile";
import { LineSeriesCard } from "../../components/charts/LineSeriesCard";
import { WorkoutList } from "./WorkoutList";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select";
import { formatDuration } from "../../lib/format";

const CURRENT_YEAR = new Date().getFullYear();

function isoDaysAgo(days: number): string {
  const date = new Date();
  date.setDate(date.getDate() - days);
  return date.toISOString().slice(0, 10);
}

// La charge aiguë (7j) / chronique (28j) et la FC de repos n'ont de sens
// que sur une fenêtre récente — et /analytics/training-load sans plage de
// dates prend ~30s sur l'historique complet (2,8M échantillons), contre
// ~5s sur 180 jours : borner ici est autant une question de pertinence que
// de temps de réponse.
const RECENT_WINDOW_DAYS = 180;

export function TrainingPage() {
  const [sport, setSport] = useState<string | undefined>(undefined);
  const [phaseId, setPhaseId] = useState<number | undefined>(undefined);

  const phases = usePhases();
  const selectedPhase = phases.data?.find((p) => p.id === phaseId);
  const phaseRange = selectedPhase ? { from: selectedPhase.starts_on, to: selectedPhase.ends_on } : {};
  // Charge et FC de repos n'ont de sens que sur une fenêtre récente, et sans
  // plage /analytics/training-load prend ~30s sur l'historique complet —
  // contrairement aux stats et à la liste, jamais bridées par défaut.
  const recentRange = { from: isoDaysAgo(RECENT_WINDOW_DAYS), to: isoDaysAgo(0) };
  const loadRange = selectedPhase ? phaseRange : recentRange;
  const rangeLabel = selectedPhase ? selectedPhase.name : "180 derniers jours";

  const sports = useSports();
  const calendar = useWorkoutCalendar({ year: CURRENT_YEAR });
  const stats = useWorkoutStats({ ...phaseRange, sport });
  const records = useWorkoutRecords(sport);
  const workouts = useWorkouts({ ...phaseRange, sport, limit: 20 });
  const trainingLoad = useTrainingLoad(loadRange);
  const restingHr = useRestingHr(loadRange);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl">Entraînement</h1>
          <p className="text-text-mid">Calendrier, volume par sport, records, charge et FC de repos.</p>
        </div>
        <div className="flex gap-2">
          <Select value={phaseId?.toString() ?? "recent"} onValueChange={(v) => setPhaseId(v === "recent" ? undefined : Number(v))}>
            <SelectTrigger className="w-56">
              <SelectValue placeholder="180 derniers jours" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="recent">180 derniers jours</SelectItem>
              {phases.data?.map((p) => (
                <SelectItem key={p.id} value={p.id.toString()}>
                  {p.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={sport ?? "all"} onValueChange={(v) => setSport(v === "all" ? undefined : v)}>
            <SelectTrigger className="w-48">
              <SelectValue placeholder="Tous les sports" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tous les sports</SelectItem>
              {sports.data?.map((s) => (
                <SelectItem key={s.sport} value={s.sport}>
                  {s.sport} ({s.workout_count})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <DomainCard variant="training" title={`Calendrier ${CURRENT_YEAR}`}>
        {calendar.isLoading ? (
          <p className="text-sm text-text-mid">Chargement…</p>
        ) : (
          <CalendarHeatmap cells={calendar.data ?? []} year={CURRENT_YEAR} />
        )}
      </DomainCard>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <DomainCard variant="training" title="Séances">
          <StatTile label="Nombre" value={stats.data?.session_count ?? null} />
        </DomainCard>
        <DomainCard variant="training" title="Durée totale">
          <StatTile label="Durée" value={stats.data ? formatDuration(stats.data.total_duration_ms) : null} />
        </DomainCard>
        <DomainCard variant="training" title="Distance totale">
          <StatTile
            label="Distance"
            value={stats.data ? Math.round(stats.data.total_distance_m / 1000) : null}
            unit="km"
          />
        </DomainCard>
        <DomainCard variant="training" title="Calories">
          <StatTile label="Calories" value={stats.data ? Math.round(stats.data.total_calories_kcal) : null} unit="kcal" />
        </DomainCard>
      </div>

      <DomainCard variant="training" title="Records">
        {records.isLoading ? (
          <p className="text-sm text-text-mid">Chargement…</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {records.data?.map((r) => (
              <li key={r.label} className="tabular flex justify-between text-sm">
                <span className="text-text-mid">{r.label}</span>
                <span className="text-text-high">{r.value}</span>
              </li>
            ))}
          </ul>
        )}
      </DomainCard>

      <DomainCard variant="training" title={`Charge aiguë contre chronique — ${rangeLabel}`}>
        <LineSeriesCard
          data={(trainingLoad.data ?? []).map((d) => ({ ...d, at: d.day }))}
          xKey="at"
          series={[
            { key: "acute_load", label: "Charge aiguë (7j)" },
            { key: "chronic_load", label: "Charge chronique (28j)" },
          ]}
        />
      </DomainCard>

      <DomainCard variant="training" title="ACWR — charge aiguë / chronique">
        <LineSeriesCard
          data={(trainingLoad.data ?? []).map((d) => ({ ...d, at: d.day }))}
          xKey="at"
          series={[{ key: "ratio", label: "ACWR" }]}
          yReferenceBands={[
            { id: "sous-entrainement", y1: 0, y2: 0.8, color: "var(--color-accent-blue)" },
            { id: "optimale", y1: 0.8, y2: 1.3, color: "var(--color-accent-green)" },
            { id: "sur-risque", y1: 1.5, color: "var(--color-danger)" },
          ]}
        />
        <ul className="mt-2 flex flex-col gap-1 text-xs text-text-mid">
          <li className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-accent-blue" />
            <span>
              <span className="text-text-high">Sous-entraînement (&lt; 0,8)</span> — charge récente trop faible : la
              condition physique baisse et le risque de blessure augmente au retour à des efforts intenses.
            </span>
          </li>
          <li className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-accent-green" />
            <span>
              <span className="text-text-high">Zone optimale (0,8 à 1,3)</span> — sollicitation cohérente avec la
              capacité du corps : progression idéale, risque de blessure faible.
            </span>
          </li>
          <li className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-destructive" />
            <span>
              <span className="text-text-high">Sur-risque (&gt; 1,5)</span> — augmentation trop rapide de la charge
              (pic) : risque de blessure ou de surentraînement en nette hausse.
            </span>
          </li>
        </ul>
      </DomainCard>

      <DomainCard variant="training" title={`FC de repos — ${rangeLabel}`}>
        <LineSeriesCard
          data={(restingHr.data ?? []).map((d) => ({ ...d, at: d.day }))}
          xKey="at"
          series={[{ key: "resting_hr", label: "FC de repos (bpm)" }]}
        />
      </DomainCard>

      <DomainCard variant="training" title="Séances">
        <WorkoutList query={workouts} />
      </DomainCard>
    </div>
  );
}
