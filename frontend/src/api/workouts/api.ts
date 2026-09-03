import { request } from "../client";
import { buildQueryString } from "../../lib/query-string";
import type {
  SportOut,
  WorkoutSummaryOut,
  WorkoutStatsOut,
  RecordOut,
  WorkoutCalendarCellOut,
  WorkoutDetailOut,
  SamplePointOut,
  TrackOut,
  SplitOut,
  HrZoneOut,
  CardiacDriftOut,
  SwolfByStrokeOut,
  StrengthOut,
  CursorPage,
} from "../types";
import type { DateRangeParams } from "../body/api";

export function fetchSports() {
  return request<SportOut[]>("/sports");
}

export function fetchWorkouts(params: DateRangeParams & { sport?: string; limit?: number; cursor?: string }) {
  return request<CursorPage<WorkoutSummaryOut>>(`/workouts${buildQueryString(params)}`);
}

export function fetchWorkoutStats(params: DateRangeParams & { sport?: string }) {
  return request<WorkoutStatsOut>(`/workouts/stats${buildQueryString(params)}`);
}

export function fetchWorkoutRecords(params: { sport?: string } = {}) {
  return request<RecordOut[]>(`/workouts/records${buildQueryString(params)}`);
}

export function fetchWorkoutCalendar(params: { metric?: string; year: number }) {
  return request<WorkoutCalendarCellOut[]>(`/workouts/calendar${buildQueryString(params)}`);
}

export function fetchWorkout(id: number) {
  return request<WorkoutDetailOut>(`/workouts/${id}`);
}

export function fetchWorkoutSamples(id: number, points?: number) {
  return request<SamplePointOut[]>(`/workouts/${id}/samples${buildQueryString({ points })}`);
}

export function fetchWorkoutTrack(id: number) {
  return request<TrackOut>(`/workouts/${id}/track`);
}

export function fetchWorkoutSplits(id: number, unit?: string) {
  return request<SplitOut[]>(`/workouts/${id}/splits${buildQueryString({ unit })}`);
}

export function fetchWorkoutHrZones(id: number) {
  return request<HrZoneOut[]>(`/workouts/${id}/hr-zones`);
}

export function fetchWorkoutCardiacDrift(id: number) {
  return request<CardiacDriftOut>(`/workouts/${id}/cardiac-drift`);
}

export function fetchWorkoutSwim(id: number) {
  return request<SwolfByStrokeOut[]>(`/workouts/${id}/swim`);
}

export function fetchWorkoutStrength(id: number) {
  return request<StrengthOut>(`/workouts/${id}/strength`);
}
