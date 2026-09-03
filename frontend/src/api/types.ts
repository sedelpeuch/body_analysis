// Contrat API — transcrit depuis backend/app/schemas/*.py et backend/app/api/*.py.
// Source de vérité : le code du backend, pas la spec.

export interface ProblemDetails {
  type: "about:blank";
  title: string;
  status: number;
  detail: string;
  instance: string;
  errors?: unknown[];
  allowed?: string[];
}

export type PhaseKind = "free" | "bulk" | "cut" | "maintain";
export type IngestionStatus = "running" | "success" | "failed";
export type Metric = "weight" | "body_fat" | "muscle";
export type Direction = "up" | "down";

export interface Page<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
}

export interface CursorPage<T> {
  items: T[];
  next_cursor: string | null;
}

// --- Corps ---

export interface MeasurementOut {
  at: string;
  weight_kg: number | null;
  body_fat_pct: number | null;
  body_fat_mass_kg: number | null;
  skeletal_muscle_mass_kg: number | null;
  fat_free_mass_kg: number | null;
  total_body_water_kg: number | null;
  basal_metabolic_rate_kcal: number | null;
}

export interface TimeseriesPointOut {
  at: string;
  value: number | null;
}

export interface DeltaOut {
  window_days: number;
  start_value: number | null;
  end_value: number | null;
  change: number | null;
}

export interface BodySummaryOut {
  latest: MeasurementOut | null;
  weight_deltas: DeltaOut[];
  current_phase_id: number | null;
}

export interface CalendarCellOut {
  day: string;
  value: number | null;
}

export interface CompositionPointOut {
  day: string;
  body_fat_mass_kg: number | null;
  fat_free_mass_kg: number | null;
  skeletal_muscle_mass_kg: number | null;
  total_body_water_kg: number | null;
  basal_metabolic_rate_kcal: number | null;
}

// --- Analytics ---

export interface TdeeOut {
  tdee_kcal: number | null;
  mean_intake_kcal: number | null;
  weight_slope_kg_per_day: number | null;
  is_valid: boolean;
  reason: string | null;
  uncertainty_note: string;
}

export interface EnergyBalanceDayOut {
  day: string;
  intake_kcal: number | null;
  expenditure_kcal: number | null;
  balance_kcal: number | null;
}

export interface RestingHrPointOut {
  day: string;
  resting_hr: number | null;
}

export interface LoadBalanceOut {
  day: string;
  acute_load: number | null;
  chronic_load: number | null;
  ratio: number | null;
}

// --- Nutrition ---

export interface DailyNutritionOut {
  day: string;
  calories: number | null;
  entry_count: number;
}

export interface EntryOut {
  at: string;
  food_name: string;
  meal_type_label: string;
  amount: number | null;
  unit_label: string;
  calories: number | null;
}

export interface MealTypeShareOut {
  meal_type_label: string;
  calories: number | null;
  entry_count: number;
}

export interface TopFoodOut {
  food_name: string;
  entry_count: number;
  total_calories: number | null;
}

export interface NutritionBreakdownOut {
  by_meal_type: MealTypeShareOut[];
  top_foods: TopFoodOut[];
}

export interface HourlyBucketOut {
  hour: number;
  entry_count: number;
  total_calories: number | null;
}

// --- Phases ---

export interface PhaseOut {
  id: number;
  name: string;
  kind: PhaseKind;
  starts_on: string;
  ends_on: string;
  weight_target_kg: number | null;
  body_fat_target_pct: number | null;
  skeletal_muscle_target_kg: number | null;
  daily_calories_target: number | null;
  notes: string | null;
}

export interface PhaseCreate {
  name: string;
  kind: PhaseKind;
  starts_on: string;
  ends_on: string;
  weight_target_kg?: number | null;
  body_fat_target_pct?: number | null;
  skeletal_muscle_target_kg?: number | null;
  daily_calories_target?: number | null;
  notes?: string | null;
}

export interface PhaseUpdate {
  name?: string | null;
  kind?: PhaseKind | null;
  starts_on?: string | null;
  ends_on?: string | null;
  weight_target_kg?: number | null;
  body_fat_target_pct?: number | null;
  skeletal_muscle_target_kg?: number | null;
  daily_calories_target?: number | null;
  notes?: string | null;
}

export interface MetricSuccessRateOut {
  metric: Metric;
  achieved_count: number;
  total_count: number;
  success_rate: number;
}

export interface ObjectiveCheckOut {
  metric: Metric;
  target: number;
  current: number | null;
  direction: Direction;
  achieved: boolean | null;
  remaining: number | null;
}

export interface PhaseMetricReportOut {
  metric: Metric;
  start_value: number | null;
  end_value: number | null;
  change: number | null;
  change_pct: number | null;
  monthly_rate: number | null;
  objective: ObjectiveCheckOut | null;
}

export interface RecompositionOut {
  fat_mass_delta_kg: number | null;
  lean_mass_delta_kg: number | null;
}

export interface PhaseReportOut {
  phase: PhaseOut;
  metrics: PhaseMetricReportOut[];
  average_calories_kcal: number | null;
  recomposition: RecompositionOut;
}

// --- Entraînement ---

export interface SportOut {
  sport: string;
  workout_count: number;
}

export interface WorkoutSummaryOut {
  id: number;
  sport: string;
  started_at: string;
  ended_at: string | null;
  duration_ms: number | null;
  distance_m: number | null;
  calories_kcal: number | null;
  mean_heart_rate: number | null;
}

export interface WorkoutStatsOut {
  session_count: number;
  total_duration_ms: number;
  total_distance_m: number;
  total_calories_kcal: number;
}

export interface RecordOut {
  label: string;
  workout_id: number;
  value: number;
  at: string;
}

export interface WorkoutCalendarCellOut {
  day: string;
  value: number | null;
}

export interface WorkoutDetailOut {
  id: number;
  sport: string;
  sport_type: number | null;
  started_at: string;
  ended_at: string | null;
  duration_ms: number | null;
  distance_m: number | null;
  calories_kcal: number | null;
  mean_heart_rate: number | null;
  max_heart_rate: number | null;
  min_heart_rate: number | null;
  mean_speed_mps: number | null;
  max_speed_mps: number | null;
  mean_cadence: number | null;
  max_cadence: number | null;
  min_altitude_m: number | null;
  max_altitude_m: number | null;
  altitude_gain_m: number | null;
  altitude_loss_m: number | null;
  pool_length_m: number | null;
  resting_hr: number | null;
  has_samples: boolean;
  has_locations: boolean;
  has_swim_lengths: boolean;
  has_strength_sets: boolean;
}

export interface SamplePointOut {
  at: string;
  heart_rate: number | null;
  speed_mps: number | null;
  distance_m: number | null;
  cadence: number | null;
  altitude_m: number | null;
}

export interface TrackOut {
  type: "LineString";
  coordinates: [number, number][];
}

export interface SplitOut {
  index: number;
  distance_m: number;
  duration_s: number;
  pace_s_per_km: number | null;
  mean_heart_rate: number | null;
}

export interface HrZoneOut {
  zone: number;
  label: string;
  seconds: number;
}

export interface CardiacDriftOut {
  first_half_mean_hr: number | null;
  second_half_mean_hr: number | null;
  drift_pct: number | null;
}

export interface SwolfByStrokeOut {
  stroke_type: string;
  length_count: number;
  mean_swolf: number | null;
  mean_duration_s: number | null;
}

export interface StrengthSetOut {
  idx: number;
  reps: number | null;
  weight_kg: number | null;
  duration_s: number | null;
}

export interface StrengthOut {
  sets: StrengthSetOut[];
  set_count: number;
  total_volume_kg: number | null;
  total_reps: number | null;
}

// --- Photos ---

export interface PhotoOut {
  id: number;
  taken_on: string;
  tag: string;
  width: number | null;
  height: number | null;
  byte_size: number | null;
  content_type: string | null;
  created_at: string;
}

// --- Imports ---

export interface IngestionRunOut {
  id: number;
  kind: string;
  source_name: string;
  status: IngestionStatus;
  started_at: string;
  finished_at: string | null;
  counts: Record<string, unknown> | null;
  error: string | null;
}
