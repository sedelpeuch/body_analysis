import { useQuery } from "@tanstack/react-query";
import * as bodyApi from "./api";
import type { DateRangeParams } from "./api";

export const measurementsQueryKey = (params: DateRangeParams) => ["body", "measurements", params] as const;
export function useMeasurements(params: DateRangeParams) {
  return useQuery({ queryKey: measurementsQueryKey(params), queryFn: () => bodyApi.fetchMeasurements(params) });
}

export function useTimeseries(params: DateRangeParams & { metrics: string; resolution?: "raw" | "daily" }) {
  return useQuery({ queryKey: ["body", "timeseries", params] as const, queryFn: () => bodyApi.fetchTimeseries(params) });
}

export function useBodySummary(params: { today?: string } = {}) {
  return useQuery({ queryKey: ["body", "summary", params] as const, queryFn: () => bodyApi.fetchSummary(params) });
}

export function useBodyCalendar(params: { metric: string; year: number }) {
  return useQuery({ queryKey: ["body", "calendar", params] as const, queryFn: () => bodyApi.fetchCalendar(params) });
}

export function useComposition(params: DateRangeParams) {
  return useQuery({ queryKey: ["body", "composition", params] as const, queryFn: () => bodyApi.fetchComposition(params) });
}
