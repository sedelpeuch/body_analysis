import { useState } from "react";
import { NavLink } from "react-router-dom";
import {
  Dumbbell,
  Home,
  Image,
  Layers,
  MoreHorizontal,
  Settings,
  User,
  UtensilsCrossed,
  Zap,
  type LucideIcon,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface Entry {
  to: string;
  label: string;
  icon: LucideIcon;
  end?: boolean;
  activeColor: string;
}

const PRIMARY_ENTRIES: Entry[] = [
  { to: "/", label: "Aujourd'hui", icon: Home, end: true, activeColor: "text-accent-green" },
  { to: "/corps", label: "Corps", icon: User, activeColor: "text-domain-body" },
  { to: "/nutrition", label: "Nutrition", icon: UtensilsCrossed, activeColor: "text-domain-nutrition" },
  { to: "/entrainement", label: "Training", icon: Dumbbell, activeColor: "text-domain-training" },
  { to: "/phases", label: "Phases", icon: Layers, activeColor: "text-domain-phase" },
];

const MORE_ENTRIES: Entry[] = [
  { to: "/corps/photos", label: "Photos", icon: Image, activeColor: "text-domain-body" },
  { to: "/energie", label: "Énergie", icon: Zap, activeColor: "text-accent-blue" },
  { to: "/reglages", label: "Réglages", icon: Settings, activeColor: "text-text-high" },
];

function TabLink({ to, label, icon: Icon, end, activeColor }: Entry) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        [
          "flex flex-1 flex-col items-center justify-center gap-0.5 py-2 text-[0.65rem] font-display uppercase tracking-wide transition-colors",
          isActive ? activeColor : "text-text-low",
        ].join(" ")
      }
    >
      <Icon className="size-5" strokeWidth={2} />
      {label}
    </NavLink>
  );
}

export function BottomNav() {
  const [moreOpen, setMoreOpen] = useState(false);

  return (
    <>
      <nav
        className="fixed inset-x-0 bottom-0 z-40 flex border-t border-line bg-surface pb-[env(safe-area-inset-bottom)] md:hidden"
        aria-label="Navigation principale"
      >
        {PRIMARY_ENTRIES.map((entry) => (
          <TabLink key={entry.to} {...entry} />
        ))}
        <button
          type="button"
          onClick={() => setMoreOpen(true)}
          className="flex flex-1 flex-col items-center justify-center gap-0.5 py-2 text-[0.65rem] font-display uppercase tracking-wide text-text-low transition-colors"
        >
          <MoreHorizontal className="size-5" strokeWidth={2} />
          Plus
        </button>
      </nav>

      <Dialog open={moreOpen} onOpenChange={setMoreOpen}>
        <DialogContent className="top-auto bottom-0 left-0 translate-x-0 translate-y-0 max-w-full rounded-b-none sm:max-w-full">
          <DialogHeader>
            <DialogTitle>Plus</DialogTitle>
          </DialogHeader>
          <div className="flex flex-col gap-1 pb-2">
            {MORE_ENTRIES.map(({ to, label, icon: Icon, activeColor }) => (
              <NavLink
                key={to}
                to={to}
                onClick={() => setMoreOpen(false)}
                className={({ isActive }) =>
                  [
                    "flex items-center gap-3 rounded-card px-3 py-3 font-display uppercase tracking-wide text-sm transition-colors",
                    isActive ? `bg-surface-raised ${activeColor}` : "text-text-mid hover:bg-surface-raised hover:text-text-high",
                  ].join(" ")
                }
              >
                <Icon className="size-5" strokeWidth={2} />
                {label}
              </NavLink>
            ))}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
