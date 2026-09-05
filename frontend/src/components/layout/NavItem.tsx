import { NavLink } from "react-router-dom";

export interface NavItemProps {
  to: string;
  label: string;
  end?: boolean;
}

export function NavItem({ to, label, end }: NavItemProps) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        [
          "block rounded-card px-3 py-2 font-display uppercase tracking-wide text-sm transition-colors",
          isActive
            ? "bg-surface-raised text-text-high"
            : "text-text-mid hover:bg-surface hover:text-text-high",
        ].join(" ")
      }
    >
      {label}
    </NavLink>
  );
}
