import { useEffect, useState } from "react";
import { usePhotos, photoImageUrl } from "../../api/photos/hooks";
import { DomainCard } from "../../components/domain-card/DomainCard";
import { PhotoImage } from "../../components/photo/PhotoImage";
import { PhotoLightbox, type LightboxPhoto } from "../../components/photo/PhotoLightbox";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../components/ui/tabs";
import { PhotoComparator } from "./PhotoComparator";

const TAGS = ["face", "profil", "dos", "bras", "epaule"] as const;
const CONFIDENTIAL_STORAGE_KEY = "body-analysis:confidential-mode";

function readConfidentialPreference(): boolean {
  try {
    return localStorage.getItem(CONFIDENTIAL_STORAGE_KEY) === "true";
  } catch {
    return false;
  }
}

export function PhotosPage() {
  const [tag, setTag] = useState<(typeof TAGS)[number]>("face");
  const [confidential, setConfidential] = useState(readConfidentialPreference);
  const [lightboxPhoto, setLightboxPhoto] = useState<LightboxPhoto | null>(null);
  const photos = usePhotos(tag);

  useEffect(() => {
    try {
      localStorage.setItem(CONFIDENTIAL_STORAGE_KEY, String(confidential));
    } catch {
      // Préférence d'affichage non critique : une erreur de stockage local ne doit pas casser la page.
    }
  }, [confidential]);

  const sorted = [...(photos.data ?? [])].sort((a, b) => a.taken_on.localeCompare(b.taken_on));

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl">Photos</h1>
          <p className="text-text-mid">Timeline par tag, comparateur avant/après, mode confidentiel.</p>
        </div>
        <label className="flex shrink-0 items-center gap-2 text-sm text-text-mid">
          <input type="checkbox" checked={confidential} onChange={(e) => setConfidential(e.target.checked)} />
          Mode confidentiel
        </label>
      </div>

      <Tabs value={tag} onValueChange={(v) => setTag(v as (typeof TAGS)[number])}>
        <TabsList className="w-full overflow-x-auto overflow-y-hidden sm:w-fit">
          {TAGS.map((t) => (
            <TabsTrigger key={t} value={t}>
              {t}
            </TabsTrigger>
          ))}
        </TabsList>
        {TAGS.map((t) => (
          <TabsContent key={t} value={t}>
            <div className="flex flex-col gap-6">
              <DomainCard variant="body" title="Timeline">
                {photos.isLoading ? (
                  <p className="text-sm text-text-mid">Chargement…</p>
                ) : sorted.length === 0 ? (
                  <p className="text-sm text-text-mid">Aucune photo pour ce tag.</p>
                ) : (
                  <div className="grid grid-cols-3 gap-2 sm:grid-cols-4 md:grid-cols-6">
                    {sorted.map((p) => (
                      <button
                        key={p.id}
                        type="button"
                        onClick={() =>
                          setLightboxPhoto({
                            src: photoImageUrl(p.id, "medium", confidential),
                            alt: `Photo ${p.tag} du ${p.taken_on}`,
                          })
                        }
                        className="flex flex-col gap-1 text-left"
                      >
                        <PhotoImage
                          src={photoImageUrl(p.id, "thumb", confidential)}
                          alt={`Photo ${p.tag} du ${p.taken_on}`}
                          className="aspect-square w-full rounded-card object-cover active:opacity-75"
                        />
                        <span className="tabular text-center text-xs text-text-mid">{p.taken_on}</span>
                      </button>
                    ))}
                  </div>
                )}
              </DomainCard>

              <DomainCard variant="body" title="Comparateur avant/après">
                <PhotoComparator photos={sorted} confidential={confidential} />
              </DomainCard>
            </div>
          </TabsContent>
        ))}
      </Tabs>

      <PhotoLightbox photo={lightboxPhoto} onClose={() => setLightboxPhoto(null)} />
    </div>
  );
}
