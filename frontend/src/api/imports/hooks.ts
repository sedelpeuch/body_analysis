import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as importsApi from "./api";
import type { IngestionRunOut } from "../types";

const IMPORTS_KEY = ["imports"] as const;

export function useImportRuns() {
  return useQuery({ queryKey: IMPORTS_KEY, queryFn: importsApi.fetchImportRuns });
}

export function useImportRun(id: number | undefined, options: { pollWhileRunning?: boolean } = {}) {
  return useQuery({
    queryKey: [...IMPORTS_KEY, id] as const,
    queryFn: () => importsApi.fetchImportRun(id!),
    enabled: id !== undefined,
    refetchInterval: options.pollWhileRunning
      ? (query: { state: { data?: IngestionRunOut } }) => (query.state.data?.status === "running" ? 1500 : false)
      : undefined,
  });
}

export function useUploadZipMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => importsApi.uploadZip(file),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: IMPORTS_KEY }),
  });
}
