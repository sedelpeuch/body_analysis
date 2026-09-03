import { useEffect, useRef } from "react";
import maplibregl, { type StyleSpecification } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { TrackOut } from "../../api/types";

export interface WorkoutMapProps {
  track: TrackOut;
}

// Pas de tuiles externes : aucune source de fond de carte gratuite et fiable
// sans clé d'API n'est garantie accessible depuis cet environnement. Un
// style vide et transparent affiche juste la trace sur le fond sombre de
// l'appli plutôt qu'un aplat de couleur qui ne correspond à aucune carte
// réelle.
const BLANK_STYLE: StyleSpecification = {
  version: 8,
  sources: {},
  layers: [{ id: "background", type: "background", paint: { "background-color": "transparent" } }],
};

export function WorkoutMap({ track }: WorkoutMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current || track.coordinates.length === 0) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: BLANK_STYLE,
      center: track.coordinates[Math.floor(track.coordinates.length / 2)],
      zoom: 12,
      attributionControl: false,
    });

    map.on("load", () => {
      map.addSource("track", { type: "geojson", data: { type: "Feature", properties: {}, geometry: track } });
      map.addLayer({
        id: "track-line",
        type: "line",
        source: "track",
        paint: { "line-color": "#21c274", "line-width": 3 },
      });

      const bounds = track.coordinates.reduce(
        (b, coord) => b.extend(coord as [number, number]),
        new maplibregl.LngLatBounds(track.coordinates[0], track.coordinates[0]),
      );
      map.fitBounds(bounds, { padding: 24 });
    });

    return () => map.remove();
  }, [track]);

  return <div ref={containerRef} className="h-80 w-full rounded-card bg-surface-raised" />;
}
