import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { TrackOut } from "../../api/types";

export interface WorkoutMapProps {
  track: TrackOut;
}

export function WorkoutMap({ track }: WorkoutMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current || track.coordinates.length === 0) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: "https://demotiles.maplibre.org/style.json",
      center: track.coordinates[Math.floor(track.coordinates.length / 2)],
      zoom: 12,
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

  return <div ref={containerRef} className="h-80 w-full rounded-card" />;
}
