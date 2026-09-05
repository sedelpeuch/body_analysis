import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { TrackOut } from "../../api/types";

export interface WorkoutMapProps {
  track: TrackOut;
}

// Fond satellite Esri World Imagery : gratuit, sans clé d'API. Attribution
// obligatoire par leurs conditions d'utilisation.
const TILE_URL = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}";
const ATTRIBUTION = "Tiles &copy; Esri &mdash; Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community";
// Vert de l'accent peu lisible sur de la végétation ou de l'eau en imagerie
// satellite : rouge franc pour un contraste garanti sur tout type de terrain.
const TRACK_COLOR = "#e0452e";

export function WorkoutMap({ track }: WorkoutMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current || track.coordinates.length === 0) return;

    // GeoJSON est [lng, lat], Leaflet attend [lat, lng].
    const latLngs = track.coordinates.map(([lng, lat]) => [lat, lng] as [number, number]);

    const map = L.map(containerRef.current, { attributionControl: true });
    L.tileLayer(TILE_URL, { attribution: ATTRIBUTION, maxZoom: 19 }).addTo(map);

    const polyline = L.polyline(latLngs, { color: TRACK_COLOR, weight: 3 }).addTo(map);
    map.fitBounds(polyline.getBounds(), { padding: [24, 24] });

    return () => {
      map.remove();
    };
  }, [track]);

  return <div ref={containerRef} className="h-80 w-full rounded-card" />;
}
