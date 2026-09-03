import { NavItem } from "./NavItem";

const NAV_ENTRIES = [
  { to: "/", label: "Aujourd'hui", end: true },
  { to: "/corps", label: "Corps" },
  { to: "/corps/photos", label: "Photos" },
  { to: "/phases", label: "Phases" },
  { to: "/nutrition", label: "Nutrition" },
  { to: "/energie", label: "Énergie" },
  { to: "/entrainement", label: "Entraînement" },
  { to: "/reglages", label: "Réglages" },
];

export function Sidebar() {
  return (
    <nav className="flex h-full w-56 shrink-0 flex-col gap-1 border-r border-line bg-surface p-3">
      <div className="mb-4 px-3 py-2 font-display text-lg uppercase tracking-wide text-text-high">
        Body Analysis
      </div>
      {NAV_ENTRIES.map((entry) => (
        <NavItem key={entry.to} {...entry} />
      ))}
    </nav>
  );
}
