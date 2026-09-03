import { useParams } from "react-router-dom";

export function PhaseDetailPage() {
  const { id } = useParams();
  return (
    <div>
      <h1 className="text-2xl">Phase {id}</h1>
      <p className="text-text-mid">Objectifs contre réalisé, courbes et photos de la période.</p>
    </div>
  );
}
