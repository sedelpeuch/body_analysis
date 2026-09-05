import { ProgressPill } from "../charts/ProgressPill";
import { objectiveProgress } from "../../lib/objective-progress";
import { formatDelta } from "../../lib/format";
import type { Direction } from "../../api/types";

export interface ObjectiveSummaryProps {
  label: string;
  color: string;
  // Unité de la valeur elle-même (kg pour poids/muscle, % pour masse grasse).
  unit: string;
  // Unité de la variation absolue — distincte de `unit` pour une métrique
  // déjà exprimée en % : une variation de masse grasse se compte en points
  // (pts), jamais en "%", pour ne pas la confondre avec l'unité de la valeur.
  deltaUnit: string;
  start: number | null;
  current: number | null;
  target: number;
  direction: Direction;
  // Fourni par l'API (analytics/objectives.py) plutôt que redérivé ici :
  // c'est la même règle qui sert au bilan transverse de /phases, pas une
  // approximation locale qui pourrait diverger sur un cas limite.
  achieved: boolean | null;
  changeAbs: number | null;
  monthlyRateAbs: number | null;
}

function round2(value: number): number {
  return Math.round(value * 100) / 100;
}

export function ObjectiveSummary({
  label,
  color,
  unit,
  deltaUnit,
  start,
  current,
  target,
  direction,
  achieved,
  changeAbs,
  monthlyRateAbs,
}: ObjectiveSummaryProps) {
  const ratio = objectiveProgress(direction, start, current, target);

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-2">
        <h4 className="text-sm text-text-mid">{label}</h4>
        {achieved && (
          <span className="rounded-full bg-accent-green/15 px-2 py-0.5 text-xs text-accent-green">Atteint</span>
        )}
      </div>
      <p className="tabular text-lg text-text-high">
        {start ?? "—"} → {current ?? "—"} {unit}
      </p>
      <p className="text-xs text-text-mid">
        objectif {target} {unit} ({direction === "down" ? "↓" : "↑"})
      </p>
      <ProgressPill value={ratio} color={color} />
      <p className="tabular text-xs text-text-mid">
        {formatDelta(changeAbs, deltaUnit)} depuis le début
        {monthlyRateAbs !== null && ` · ${formatDelta(round2(monthlyRateAbs), `${deltaUnit}/mois`)}`}
      </p>
    </div>
  );
}
