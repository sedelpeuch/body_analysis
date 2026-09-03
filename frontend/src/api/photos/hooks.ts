import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as photosApi from "./api";
import type { UploadPhotoInput } from "./api";

export { photoImageUrl } from "./api";

const PHOTOS_KEY = ["photos"] as const;

export function usePhotos(tag?: string) {
  return useQuery({ queryKey: [...PHOTOS_KEY, tag] as const, queryFn: () => photosApi.fetchPhotos(tag) });
}

export function useUploadPhotoMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: UploadPhotoInput) => photosApi.uploadPhoto(input),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: PHOTOS_KEY }),
  });
}

export function useDeletePhotoMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => photosApi.deletePhoto(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: PHOTOS_KEY }),
  });
}
