import { useWorkoutStrength } from "../../api/workouts/hooks";
import { DomainCard } from "../../components/domain-card/DomainCard";
import { StatTile } from "../../components/charts/StatTile";
import { EmptyValue } from "../../components/empty-state/EmptyValue";

export function StrengthSection({ workoutId }: { workoutId: number }) {
  const strength = useWorkoutStrength(workoutId);

  return (
    <DomainCard variant="training" title="Musculation — séries et volume">
      {strength.isLoading ? (
        <p className="text-sm text-text-mid">Chargement…</p>
      ) : (
        <div className="flex flex-col gap-4">
          <div className="flex gap-6">
            <StatTile label="Séries" value={strength.data?.set_count ?? null} />
            <StatTile label="Répétitions" value={strength.data?.total_reps ?? null} />
            <StatTile label="Volume total" value={strength.data?.total_volume_kg ?? null} unit="kg" />
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-text-mid">
                <th className="pb-2 font-normal">#</th>
                <th className="pb-2 font-normal">Répétitions</th>
                <th className="pb-2 font-normal">Charge</th>
                <th className="pb-2 font-normal">Durée</th>
              </tr>
            </thead>
            <tbody className="tabular">
              {strength.data?.sets.map((set) => (
                <tr key={set.idx} className="border-t border-line">
                  <td className="py-2 text-text-high">{set.idx}</td>
                  <td className="py-2">{set.reps ?? <EmptyValue />}</td>
                  <td className="py-2">{set.weight_kg !== null ? `${set.weight_kg} kg` : <EmptyValue />}</td>
                  <td className="py-2">{set.duration_s !== null ? `${set.duration_s} s` : <EmptyValue />}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </DomainCard>
  );
}
