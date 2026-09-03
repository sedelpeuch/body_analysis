import type { Metric } from "../api/types";
import { seriesColor } from "./chart-palette";

// Couleur fixe par métrique récurrente, à travers toutes les pages —
// poids en vert, muscle en bleu, masse grasse en ambre. L'unité varie
// selon le contexte (le "muscle" d'un graphique /body/timeseries est un
// pourcentage, celui d'un objectif de phase compare des kilogrammes contre
// skeletal_muscle_target_kg), donc seule la couleur est fixée ici.
export const METRIC_COLOR: Record<Metric, string> = {
  weight: seriesColor(0),
  muscle: seriesColor(1),
  body_fat: seriesColor(2),
};

export const METRIC_LABEL: Record<Metric, string> = {
  weight: "Poids",
  muscle: "Muscle",
  body_fat: "Masse grasse",
};

// Unité de la valeur d'objectif elle-même.
export const OBJECTIVE_UNIT: Record<Metric, string> = { weight: "kg", body_fat: "%", muscle: "kg" };

// Unité de la variation absolue — "pts" pour une métrique déjà en % (une
// variation de masse grasse se compte en points, jamais en "%", pour ne
// pas se confondre avec la variation relative qui elle est toujours en %).
export const OBJECTIVE_DELTA_UNIT: Record<Metric, string> = { weight: "kg", body_fat: "pts", muscle: "kg" };
