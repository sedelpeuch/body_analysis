import { useParams } from "react-router-dom";

export function WorkoutDetailPage() {
  const { id } = useParams();
  return (
    <div>
      <h1 className="text-2xl">Séance {id}</h1>
      <p className="text-text-mid">Courbes FC, vitesse et altitude, trace GPS, temps par zone cardiaque, splits, natation, musculation.</p>
    </div>
  );
}
