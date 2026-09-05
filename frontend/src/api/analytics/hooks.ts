import { useQuery } from "@tanstack/react-query";
import * as analyticsApi from "./api";
import type { DateRangeParams } from "../body/api";

export function useTdee(params: DateRangeParams & { phase_id?: number }) {
  return useQuery({ queryKey: ["analytics", "tdee", params] as const, queryFn: () => analyticsApi.fetchTdee(params) });
}

export function useEnergyBalance(params: DateRangeParams) {
  return useQuery({ queryKey: ["analytics", "energy-balance", params] as const, queryFn: () => analyticsApi.fetchEnergyBalance(params) });
}

export function useRestingHr(params: DateRangeParams) {
  return useQuery({ queryKey: ["analytics", "resting-hr", params] as const, queryFn: () => analyticsApi.fetchRestingHr(params) });
}

export function useTrainingLoad(params: DateRangeParams) {
  return useQuery({ queryKey: ["analytics", "training-load", params] as const, queryFn: () => analyticsApi.fetchTrainingLoad(params) });
}
