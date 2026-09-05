import { Link } from "react-router-dom";
import { ImportSection } from "./ImportSection";
import { PhotoManagement } from "./PhotoManagement";
import { DomainCard } from "../../components/domain-card/DomainCard";

export function SettingsPage() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl">Réglages</h1>
        <p className="text-text-mid">Import ZIP, gestion des photos et des phases.</p>
      </div>

      <ImportSection />
      <PhotoManagement />

      <DomainCard variant="phase" title="Phases">
        <Link to="/phases" className="text-sm text-text-high hover:underline">
          Gérer les phases →
        </Link>
      </DomainCard>
    </div>
  );
}
