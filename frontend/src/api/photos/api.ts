import { request, BASE_URL } from "../client";
import { buildQueryString } from "../../lib/query-string";
import type { PhotoOut } from "../types";

export function fetchPhotos(tag?: string) {
  return request<PhotoOut[]>(`/photos${buildQueryString({ tag })}`);
}

export interface UploadPhotoInput {
  takenOn: string;
  tag: string;
  file: File;
}

export function uploadPhoto(input: UploadPhotoInput) {
  const form = new FormData();
  form.set("taken_on", input.takenOn);
  form.set("tag", input.tag);
  form.set("file", input.file);
  return request<PhotoOut>("/photos", { method: "POST", body: form });
}

export function deletePhoto(id: number) {
  return request<void>(`/photos/${id}`, { method: "DELETE" });
}

export function photoImageUrl(id: number, size: "thumb" | "medium" | "full" = "medium", blur = false): string {
  return `${BASE_URL}/photos/${id}/image${buildQueryString({ size, blur })}`;
}
