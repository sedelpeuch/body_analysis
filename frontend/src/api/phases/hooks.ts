import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as phasesApi from "./api";
import type { PhaseCreate, PhaseUpdate } from "../types";

const PHASES_KEY = ["phases"] as const;

export function usePhases() {
  return useQuery({ queryKey: PHASES_KEY, queryFn: phasesApi.fetchPhases });
}

export function usePhase(id: number) {
  return useQuery({ queryKey: [...PHASES_KEY, id] as const, queryFn: () => phasesApi.fetchPhase(id) });
}

export function useCurrentPhase(today?: string) {
  return useQuery({ queryKey: [...PHASES_KEY, "current", today] as const, queryFn: () => phasesApi.fetchCurrentPhase({ today }) });
}

export function usePhasesReport(today?: string) {
  return useQuery({ queryKey: [...PHASES_KEY, "report", today] as const, queryFn: () => phasesApi.fetchPhasesReport({ today }) });
}

export function usePhaseReport(id: number | undefined, today?: string) {
  return useQuery({
    queryKey: [...PHASES_KEY, id, "report", today] as const,
    queryFn: () => phasesApi.fetchPhaseReport(id!, { today }),
    enabled: id !== undefined,
  });
}

export function useCreatePhaseMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: PhaseCreate) => phasesApi.createPhase(body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: PHASES_KEY }),
  });
}

export function useUpdatePhaseMutation(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: PhaseUpdate) => phasesApi.updatePhase(id, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: PHASES_KEY }),
  });
}

export function useDeletePhaseMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => phasesApi.deletePhase(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: PHASES_KEY }),
  });
}
