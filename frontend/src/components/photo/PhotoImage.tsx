import { useState } from "react";

export interface PhotoImageProps {
  src: string;
  alt: string;
  className?: string;
}

export function PhotoImage({ src, alt, className }: PhotoImageProps) {
  const [failed, setFailed] = useState(false);

  if (failed) {
    return (
      <div className={`flex items-center justify-center bg-surface-raised text-xs text-text-mid ${className ?? ""}`}>
        Image indisponible
      </div>
    );
  }

  return <img src={src} alt={alt} className={className} onError={() => setFailed(true)} />;
}
