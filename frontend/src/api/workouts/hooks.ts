import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import * as workoutsApi from "./api";
import type { DateRangeParams } from "../body/api";

export function useSports() {
  return useQuery({ queryKey: ["workouts", "sports"] as const, queryFn: workoutsApi.fetchSports });
}

export function useWorkouts(params: DateRangeParams & { sport?: string; limit?: number }) {
  return useInfiniteQuery({
    queryKey: ["workouts", "list", params] as const,
    queryFn: ({ pageParam }: { pageParam: string | undefined }) => workoutsApi.fetchWorkouts({ ...params, cursor: pageParam }),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last) => last.next_cursor ?? undefined,
  });
}

export function useWorkoutStats(params: DateRangeParams & { sport?: string }) {
  return useQuery({ queryKey: ["workouts", "stats", params] as const, queryFn: () => workoutsApi.fetchWorkoutStats(params) });
}

export function useWorkoutRecords(sport?: string) {
  return useQuery({ queryKey: ["workouts", "records", sport] as const, queryFn: () => workoutsApi.fetchWorkoutRecords({ sport }) });
}

export function useWorkoutCalendar(params: { metric?: string; year: number }) {
  return useQuery({ queryKey: ["workouts", "calendar", params] as const, queryFn: () => workoutsApi.fetchWorkoutCalendar(params) });
}

export function useWorkout(id: number) {
  return useQuery({ queryKey: ["workouts", id] as const, queryFn: () => workoutsApi.fetchWorkout(id) });
}

export function useWorkoutSamples(id: number, points?: number) {
  return useQuery({ queryKey: ["workouts", id, "samples", points] as const, queryFn: () => workoutsApi.fetchWorkoutSamples(id, points) });
}

export function useWorkoutTrack(id: number) {
  return useQuery({ queryKey: ["workouts", id, "track"] as const, queryFn: () => workoutsApi.fetchWorkoutTrack(id) });
}

export function useWorkoutSplits(id: number, unit?: string) {
  return useQuery({ queryKey: ["workouts", id, "splits", unit] as const, queryFn: () => workoutsApi.fetchWorkoutSplits(id, unit) });
}

export function useWorkoutHrZones(id: number) {
  return useQuery({ queryKey: ["workouts", id, "hr-zones"] as const, queryFn: () => workoutsApi.fetchWorkoutHrZones(id) });
}

export function useWorkoutCardiacDrift(id: number) {
  return useQuery({
    queryKey: ["workouts", id, "cardiac-drift"] as const,
    queryFn: () => workoutsApi.fetchWorkoutCardiacDrift(id),
  });
}

export function useWorkoutSwim(id: number) {
  return useQuery({ queryKey: ["workouts", id, "swim"] as const, queryFn: () => workoutsApi.fetchWorkoutSwim(id) });
}

export function useWorkoutStrength(id: number) {
  return useQuery({ queryKey: ["workouts", id, "strength"] as const, queryFn: () => workoutsApi.fetchWorkoutStrength(id) });
}
