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
  const [beforeIndex, setBeforeIndex] = useState(0);
  const [afterIndex, setAfterIndex] = useState(sorted.length - 1);

  if (sorted.length < 2) {
    return <p className="text-sm text-text-mid">Au moins deux photos sont nécessaires pour comparer.</p>;
  }

  const before = sorted[beforeIndex];
  const after = sorted[afterIndex];

  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-2 gap-4">
        <div className="flex flex-col gap-2">
          <select
            value={beforeIndex}
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
            value={afterIndex}
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
