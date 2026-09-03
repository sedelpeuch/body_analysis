import { Dialog, DialogContent } from "../ui/dialog";

export interface LightboxPhoto {
  src: string;
  alt: string;
}

export interface PhotoLightboxProps {
  photo: LightboxPhoto | null;
  onClose: () => void;
}

export function PhotoLightbox({ photo, onClose }: PhotoLightboxProps) {
  return (
    <Dialog open={photo !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-3xl border-none bg-transparent p-0 ring-0">
        {photo && <img src={photo.src} alt={photo.alt} className="max-h-[85vh] w-full rounded-card object-contain" />}
      </DialogContent>
    </Dialog>
  );
}
