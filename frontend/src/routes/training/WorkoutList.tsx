import { Link } from "react-router-dom";
import type { UseInfiniteQueryResult, InfiniteData } from "@tanstack/react-query";
import type { CursorPage, WorkoutSummaryOut } from "../../api/types";
import { EmptyValue } from "../../components/empty-state/EmptyValue";
import { formatDuration } from "../../lib/format";

export interface WorkoutListProps {
  query: UseInfiniteQueryResult<InfiniteData<CursorPage<WorkoutSummaryOut>>>;
}

export function WorkoutList({ query }: WorkoutListProps) {
  const items = query.data?.pages.flatMap((page) => page.items) ?? [];

  if (query.isLoading) return <p className="text-sm text-text-mid">Chargement…</p>;
  if (items.length === 0) return <p className="text-sm text-text-mid">Aucune séance.</p>;

  return (
    <div className="flex flex-col gap-3">
      <ul className="flex flex-col gap-3">
        {items.map((w) => (
          <li key={w.id} className="border-b border-line pb-2 last:border-none">
            <Link to={`/entrainement/${w.id}`} className="flex items-center justify-between text-sm hover:text-text-high">
              <div>
                <p className="text-text-high">{w.sport}</p>
                <p className="tabular text-xs text-text-mid">{new Date(w.started_at).toLocaleString("fr-FR")}</p>
              </div>
              <div className="tabular flex gap-4 text-right text-text-mid">
                <span>{w.duration_ms !== null ? formatDuration(w.duration_ms) : <EmptyValue />}</span>
                <span>{w.distance_m !== null ? `${(w.distance_m / 1000).toFixed(2)} km` : <EmptyValue />}</span>
                <span>{w.mean_heart_rate !== null ? `${Math.round(w.mean_heart_rate)} bpm` : <EmptyValue />}</span>
              </div>
            </Link>
          </li>
        ))}
      </ul>
      {query.hasNextPage && (
        <button
          type="button"
          onClick={() => query.fetchNextPage()}
          disabled={query.isFetchingNextPage}
          className="self-center rounded-card border border-line px-3 py-1.5 text-sm text-text-mid hover:text-text-high disabled:opacity-50"
        >
          {query.isFetchingNextPage ? "Chargement…" : "Charger plus"}
        </button>
      )}
    </div>
  );
}
