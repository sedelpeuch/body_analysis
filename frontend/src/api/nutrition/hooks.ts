import { useQuery } from "@tanstack/react-query";
import * as nutritionApi from "./api";
import type { DateRangeParams } from "../body/api";

export function useDailyNutrition(params: DateRangeParams) {
  return useQuery({ queryKey: ["nutrition", "daily", params] as const, queryFn: () => nutritionApi.fetchDailyNutrition(params) });
}

export function useNutritionEntries(params: DateRangeParams & { page?: number }) {
  return useQuery({ queryKey: ["nutrition", "entries", params] as const, queryFn: () => nutritionApi.fetchEntries(params) });
}

export function useNutritionBreakdown(params: DateRangeParams) {
  return useQuery({ queryKey: ["nutrition", "breakdown", params] as const, queryFn: () => nutritionApi.fetchBreakdown(params) });
}

export function useEatingWindow(params: DateRangeParams) {
  return useQuery({ queryKey: ["nutrition", "eating-window", params] as const, queryFn: () => nutritionApi.fetchEatingWindow(params) });
}

export function useTopFoods(params: DateRangeParams & { limit?: number }) {
  return useQuery({ queryKey: ["nutrition", "top-foods", params] as const, queryFn: () => nutritionApi.fetchTopFoods(params) });
}
