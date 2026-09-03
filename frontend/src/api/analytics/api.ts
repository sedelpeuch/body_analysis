import { request } from "../client";
import { buildQueryString } from "../../lib/query-string";
import type { TdeeOut, EnergyBalanceDayOut, RestingHrPointOut, LoadBalanceOut } from "../types";
import type { DateRangeParams } from "../body/api";

export function fetchTdee(params: DateRangeParams & { phase_id?: number }) {
  return request<TdeeOut>(`/analytics/tdee${buildQueryString(params)}`);
}

export function fetchEnergyBalance(params: DateRangeParams) {
  return request<EnergyBalanceDayOut[]>(`/analytics/energy-balance${buildQueryString(params)}`);
}

export function fetchRestingHr(params: DateRangeParams) {
  return request<RestingHrPointOut[]>(`/analytics/resting-hr${buildQueryString(params)}`);
}

export function fetchTrainingLoad(params: DateRangeParams) {
  return request<LoadBalanceOut[]>(`/analytics/training-load${buildQueryString(params)}`);
}
