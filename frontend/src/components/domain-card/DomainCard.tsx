import type { ReactNode } from "react";

export type DomainVariant = "body" | "nutrition" | "training" | "phase";

const BAND_CLASS: Record<DomainVariant, string> = {
  body: "bg-domain-body",
  nutrition: "bg-domain-nutrition",
  training: "bg-domain-training",
  phase: "bg-domain-phase",
};

export interface DomainCardProps {
  variant: DomainVariant;
  title: string;
  children: ReactNode;
}

export function DomainCard({ variant, title, children }: DomainCardProps) {
  return (
    <section className="overflow-hidden rounded-card border border-line bg-surface">
      <header className={`h-1 ${BAND_CLASS[variant]}`} />
      <div className="p-4">
        <h3 className="mb-3 text-sm">{title}</h3>
        {children}
      </div>
    </section>
  );
}
