import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { TrackOut } from "../../api/types";

export interface WorkoutMapProps {
  track: TrackOut;
}

// Fond de carte CARTO Dark Matter : gratuit, sans clé d'API, assorti au
// thème sombre de l'appli. Attribution obligatoire par leur CGU.
const TILE_URL = "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png";
const ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>';

export function WorkoutMap({ track }: WorkoutMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current || track.coordinates.length === 0) return;

    // GeoJSON est [lng, lat], Leaflet attend [lat, lng].
    const latLngs = track.coordinates.map(([lng, lat]) => [lat, lng] as [number, number]);

    const map = L.map(containerRef.current, { attributionControl: true });
    L.tileLayer(TILE_URL, { attribution: ATTRIBUTION, subdomains: "abcd", maxZoom: 20 }).addTo(map);

    const polyline = L.polyline(latLngs, { color: "#21c274", weight: 3 }).addTo(map);
    map.fitBounds(polyline.getBounds(), { padding: [24, 24] });

    return () => {
      map.remove();
    };
  }, [track]);

  return <div ref={containerRef} className="h-80 w-full rounded-card" />;
}
