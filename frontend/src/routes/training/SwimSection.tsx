import { useWorkoutSwim } from "../../api/workouts/hooks";
import { DomainCard } from "../../components/domain-card/DomainCard";
import { EmptyValue } from "../../components/empty-state/EmptyValue";

export function SwimSection({ workoutId }: { workoutId: number }) {
  const swim = useWorkoutSwim(workoutId);

  return (
    <DomainCard variant="training" title="Natation — SWOLF par nage">
      {swim.isLoading ? (
        <p className="text-sm text-text-mid">Chargement…</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-text-mid">
              <th className="pb-2 font-normal">Nage</th>
              <th className="pb-2 font-normal">Longueurs</th>
              <th className="pb-2 font-normal">SWOLF moyen</th>
              <th className="pb-2 font-normal">Durée moyenne</th>
            </tr>
          </thead>
          <tbody className="tabular">
            {swim.data?.map((row) => (
              <tr key={row.stroke_type} className="border-t border-line">
                <td className="py-2 text-text-high">{row.stroke_type}</td>
                <td className="py-2">{row.length_count}</td>
                <td className="py-2">{row.mean_swolf ?? <EmptyValue />}</td>
                <td className="py-2">{row.mean_duration_s !== null ? `${row.mean_duration_s.toFixed(1)} s` : <EmptyValue />}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </DomainCard>
  );
}
