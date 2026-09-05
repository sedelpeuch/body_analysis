import { useState } from "react";
import { usePhotos, useUploadPhotoMutation, useDeletePhotoMutation, photoImageUrl } from "../../api/photos/hooks";
import { DomainCard } from "../../components/domain-card/DomainCard";
import { PhotoImage } from "../../components/photo/PhotoImage";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select";
import { ApiError } from "../../api/client";

const TAGS = ["face", "profil", "dos", "bras", "epaule"] as const;

export function PhotoManagement() {
  const [takenOn, setTakenOn] = useState("");
  const [tag, setTag] = useState<(typeof TAGS)[number]>("face");
  const [file, setFile] = useState<File | null>(null);

  const photos = usePhotos();
  const uploadMutation = useUploadPhotoMutation();
  const deleteMutation = useDeletePhotoMutation();

  function handleUpload() {
    if (!file || !takenOn) return;
    uploadMutation.mutate(
      { takenOn, tag, file },
      { onSuccess: () => setFile(null) },
    );
  }

  function handleDelete(id: number) {
    if (!confirm("Supprimer cette photo ?")) return;
    deleteMutation.mutate(id);
  }

  const uploadError =
    uploadMutation.error instanceof ApiError
      ? `${uploadMutation.error.problem.detail}${uploadMutation.error.problem.allowed ? ` (${uploadMutation.error.problem.allowed.join(", ")})` : ""}`
      : null;

  return (
    <DomainCard variant="body" title="Gestion des photos">
      <div className="flex flex-col gap-4">
        <div className="flex flex-wrap items-center gap-2">
          <Input type="date" value={takenOn} onChange={(e) => setTakenOn(e.target.value)} />
          <Select value={tag} onValueChange={(v) => setTag(v as (typeof TAGS)[number])}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {TAGS.map((t) => (
                <SelectItem key={t} value={t}>
                  {t}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <input type="file" accept="image/*" onChange={(e) => setFile(e.target.files?.[0] ?? null)} className="text-sm text-text-mid" />
          <Button onClick={handleUpload} disabled={!file || !takenOn || uploadMutation.isPending}>
            {uploadMutation.isPending ? "Envoi…" : "Envoyer"}
          </Button>
        </div>

        {uploadError && <p className="text-sm text-destructive">{uploadError}</p>}

        <div className="grid grid-cols-4 gap-2 md:grid-cols-6">
          {photos.data?.map((p) => (
            <div key={p.id} className="flex flex-col gap-1">
              <PhotoImage
                src={photoImageUrl(p.id, "thumb", false)}
                alt={`Photo ${p.tag} du ${p.taken_on}`}
                className="aspect-square w-full rounded-card object-cover"
              />
              <div className="flex items-center justify-between text-xs text-text-mid">
                <span className="tabular">{p.taken_on}</span>
                <button type="button" onClick={() => handleDelete(p.id)} className="text-destructive hover:underline">
                  Suppr.
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </DomainCard>
  );
}
