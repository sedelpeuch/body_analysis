import { request } from "../client";
import type { IngestionRunOut } from "../types";

export function fetchImportRuns() {
  return request<IngestionRunOut[]>("/imports");
}

export function fetchImportRun(id: number) {
  return request<IngestionRunOut>(`/imports/${id}`);
}

export function uploadZip(file: File) {
  const form = new FormData();
  form.set("file", file);
  return request<IngestionRunOut>("/imports/samsung-zip", { method: "POST", body: form });
}
