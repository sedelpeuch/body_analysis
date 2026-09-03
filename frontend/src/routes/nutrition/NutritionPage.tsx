import { useMemo, useState } from "react";
import { usePhases } from "../../api/phases/hooks";
import { useDailyNutrition, useEatingWindow, useNutritionBreakdown, useNutritionEntries } from "../../api/nutrition/hooks";
import { DomainCard } from "../../components/domain-card/DomainCard";
import { LineSeriesCard } from "../../components/charts/LineSeriesCard";
import { StatTile } from "../../components/charts/StatTile";
import { EmptyValue } from "../../components/empty-state/EmptyValue";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select";

export function NutritionPage() {
  const [page, setPage] = useState(1);
  const [phaseId, setPhaseId] = useState<number | undefined>(undefined);

  const phases = usePhases();
  const selectedPhase = phases.data?.find((p) => p.id === phaseId);
  const range = { from: selectedPhase?.starts_on, to: selectedPhase?.ends_on };

  const daily = useDailyNutrition(range);
  const entries = useNutritionEntries({ ...range, page });
  const breakdown = useNutritionBreakdown(range);
  const eatingWindow = useEatingWindow(range);

  const dailyData = useMemo(() => (daily.data ?? []).map((d) => ({ ...d, at: d.day })), [daily.data]);
  const hourlyData = useMemo(
    () => (eatingWindow.data ?? []).map((h) => ({ hour: `${h.hour}h`, entry_count: h.entry_count })),
    [eatingWindow.data],
  );

  const averageCalories = useMemo(() => {
    const withValue = (daily.data ?? []).filter((d) => d.calories !== null);
    if (withValue.length === 0) return null;
    return Math.round(withValue.reduce((sum, d) => sum + d.calories!, 0) / withValue.length);
  }, [daily.data]);

  const totalPages = entries.data ? Math.ceil(entries.data.total / entries.data.page_size) : 1;

  function handlePhaseChange(value: string) {
    setPhaseId(value === "all" ? undefined : Number(value));
    setPage(1);
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl">Nutrition</h1>
          <p className="text-text-mid">Calories par jour, répartition par repas, fenêtre alimentaire.</p>
        </div>
        <Select value={phaseId?.toString() ?? "all"} onValueChange={handlePhaseChange}>
          <SelectTrigger className="w-56">
            <SelectValue placeholder="Toutes les données" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Toutes les données</SelectItem>
            {phases.data?.map((p) => (
              <SelectItem key={p.id} value={p.id.toString()}>
                {p.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <DomainCard variant="nutrition" title="Apport moyen">
          <StatTile label="Apport moyen" value={averageCalories} unit="kcal/j" />
        </DomainCard>
        <DomainCard variant="nutrition" title="Jours journalisés">
          <StatTile label="Jours" value={daily.data?.length ?? null} />
        </DomainCard>
        <DomainCard variant="nutrition" title="Entrées">
          <StatTile label="Entrées" value={entries.data?.total ?? null} />
        </DomainCard>
      </div>

      <DomainCard variant="nutrition" title="Calories par jour">
        <LineSeriesCard data={dailyData} xKey="at" series={[{ key: "calories", label: "Calories" }]} />
      </DomainCard>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <DomainCard variant="nutrition" title="Répartition par repas">
          {breakdown.isLoading ? (
            <p className="text-sm text-text-mid">Chargement…</p>
          ) : (
            <ul className="flex flex-col gap-2">
              {breakdown.data?.by_meal_type.map((m) => (
                <li key={m.meal_type_label} className="tabular flex justify-between text-sm">
                  <span className="text-text-mid">{m.meal_type_label}</span>
                  <span className="text-text-high">
                    {m.calories !== null ? `${Math.round(m.calories)} kcal` : <EmptyValue />} ({m.entry_count})
                  </span>
                </li>
              ))}
            </ul>
          )}
        </DomainCard>

        <DomainCard variant="nutrition" title="Fenêtre alimentaire">
          <LineSeriesCard data={hourlyData} xKey="hour" series={[{ key: "entry_count", label: "Prises" }]} height={200} />
        </DomainCard>
      </div>

      <DomainCard variant="nutrition" title="Entrées">
        {entries.isLoading ? (
          <p className="text-sm text-text-mid">Chargement…</p>
        ) : (
          <div className="flex flex-col gap-3">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-text-mid">
                  <th className="pb-2 font-normal">Date</th>
                  <th className="pb-2 font-normal">Aliment</th>
                  <th className="pb-2 font-normal">Repas</th>
                  <th className="pb-2 font-normal">Calories</th>
                </tr>
              </thead>
              <tbody className="tabular">
                {entries.data?.items.map((e, i) => (
                  <tr key={i} className="border-t border-line">
                    <td className="py-2 text-text-mid">{new Date(e.at).toLocaleString("fr-FR")}</td>
                    <td className="py-2 text-text-high">{e.food_name}</td>
                    <td className="py-2 text-text-mid">{e.meal_type_label}</td>
                    <td className="py-2">{e.calories !== null ? Math.round(e.calories) : <EmptyValue />}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="flex items-center justify-between text-sm text-text-mid">
              <button
                type="button"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
                className="rounded-card border border-line px-3 py-1 disabled:opacity-50"
              >
                Précédent
              </button>
              <span className="tabular">
                Page {page} / {totalPages}
              </span>
              <button
                type="button"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
                className="rounded-card border border-line px-3 py-1 disabled:opacity-50"
              >
                Suivant
              </button>
            </div>
          </div>
        )}
      </DomainCard>
    </div>
  );
}
