import { request } from "../client";
import { buildQueryString } from "../../lib/query-string";
import type { MeasurementOut, BodySummaryOut, CalendarCellOut, CompositionPointOut, TimeseriesPointOut } from "../types";

export interface DateRangeParams {
  from?: string;
  to?: string;
}

export function fetchMeasurements(params: DateRangeParams) {
  return request<MeasurementOut[]>(`/body/measurements${buildQueryString(params)}`);
}

export function fetchTimeseries(params: DateRangeParams & { metrics: string; resolution?: "raw" | "daily" }) {
  return request<Record<string, TimeseriesPointOut[]>>(`/body/timeseries${buildQueryString(params)}`);
}

export function fetchSummary(params: { today?: string } = {}) {
  return request<BodySummaryOut>(`/body/summary${buildQueryString(params)}`);
}

export function fetchCalendar(params: { metric: string; year: number }) {
  return request<CalendarCellOut[]>(`/body/calendar${buildQueryString(params)}`);
}

export function fetchComposition(params: DateRangeParams) {
  return request<CompositionPointOut[]>(`/body/composition${buildQueryString(params)}`);
}
