import { request } from "../client";
import { buildQueryString } from "../../lib/query-string";
import type { DailyNutritionOut, EntryOut, NutritionBreakdownOut, HourlyBucketOut, TopFoodOut, Page } from "../types";
import type { DateRangeParams } from "../body/api";

export function fetchDailyNutrition(params: DateRangeParams) {
  return request<DailyNutritionOut[]>(`/nutrition/daily${buildQueryString(params)}`);
}

export function fetchEntries(params: DateRangeParams & { page?: number }) {
  return request<Page<EntryOut>>(`/nutrition/entries${buildQueryString(params)}`);
}

export function fetchBreakdown(params: DateRangeParams) {
  return request<NutritionBreakdownOut>(`/nutrition/breakdown${buildQueryString(params)}`);
}

export function fetchEatingWindow(params: DateRangeParams) {
  return request<HourlyBucketOut[]>(`/nutrition/eating-window${buildQueryString(params)}`);
}

export function fetchTopFoods(params: DateRangeParams & { limit?: number }) {
  return request<TopFoodOut[]>(`/nutrition/top-foods${buildQueryString(params)}`);
}
