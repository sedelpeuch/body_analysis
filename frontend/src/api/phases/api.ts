import { request } from "../client";
import { buildQueryString } from "../../lib/query-string";
import type { PhaseOut, PhaseCreate, PhaseUpdate, PhaseReportOut, MetricSuccessRateOut } from "../types";

export function fetchPhases() {
  return request<PhaseOut[]>("/phases");
}

export function fetchPhase(id: number) {
  return request<PhaseOut>(`/phases/${id}`);
}

export function fetchCurrentPhase(params: { today?: string } = {}) {
  return request<PhaseOut | null>(`/phases/current${buildQueryString(params)}`);
}

export function fetchPhasesReport(params: { today?: string } = {}) {
  return request<MetricSuccessRateOut[]>(`/phases/report${buildQueryString(params)}`);
}

export function fetchPhaseReport(id: number, params: { today?: string } = {}) {
  return request<PhaseReportOut>(`/phases/${id}/report${buildQueryString(params)}`);
}

export function createPhase(body: PhaseCreate) {
  return request<PhaseOut>("/phases", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
}

export function updatePhase(id: number, body: PhaseUpdate) {
  return request<PhaseOut>(`/phases/${id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
}

export function deletePhase(id: number) {
  return request<void>(`/phases/${id}`, { method: "DELETE" });
}
