import { useState } from "react";
import type { PhotoOut } from "../../api/types";
import { photoImageUrl } from "../../api/photos/hooks";
import { PhotoImage } from "../../components/photo/PhotoImage";

export interface PhotoComparatorProps {
  photos: PhotoOut[];
  confidential: boolean;
}

export function PhotoComparator({ photos, confidential }: PhotoComparatorProps) {
  const sorted = [...photos].sort((a, b) => a.taken_on.localeCompare(b.taken_on));
  // null = pas encore choisi par l'utilisateur : se résout contre `sorted`
  // à chaque rendu plutôt que de figer un index calculé une seule fois au
  // montage, quand `sorted` peut encore être vide (photos en chargement).
  const [beforeIndex, setBeforeIndex] = useState<number | null>(null);
  const [afterIndex, setAfterIndex] = useState<number | null>(null);

  if (sorted.length < 2) {
    return <p className="text-sm text-text-mid">Au moins deux photos sont nécessaires pour comparer.</p>;
  }

  const effectiveBeforeIndex = beforeIndex ?? 0;
  const effectiveAfterIndex = afterIndex ?? sorted.length - 1;
  const before = sorted[effectiveBeforeIndex];
  const after = sorted[effectiveAfterIndex];

  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-2 gap-4">
        <div className="flex flex-col gap-2">
          <select
            value={effectiveBeforeIndex}
            onChange={(e) => setBeforeIndex(Number(e.target.value))}
            className="rounded-card border border-line bg-surface px-2 py-1 text-sm text-text-high"
          >
            {sorted.map((p, i) => (
              <option key={p.id} value={i}>
                {p.taken_on}
              </option>
            ))}
          </select>
          <PhotoImage
            src={photoImageUrl(before.id, "medium", confidential)}
            alt={`Photo ${before.tag} du ${before.taken_on}`}
            className="aspect-[3/4] w-full rounded-card object-cover"
          />
        </div>
        <div className="flex flex-col gap-2">
          <select
            value={effectiveAfterIndex}
            onChange={(e) => setAfterIndex(Number(e.target.value))}
            className="rounded-card border border-line bg-surface px-2 py-1 text-sm text-text-high"
          >
            {sorted.map((p, i) => (
              <option key={p.id} value={i}>
                {p.taken_on}
              </option>
            ))}
          </select>
          <PhotoImage
            src={photoImageUrl(after.id, "medium", confidential)}
            alt={`Photo ${after.tag} du ${after.taken_on}`}
            className="aspect-[3/4] w-full rounded-card object-cover"
          />
        </div>
      </div>
    </div>
  );
}
