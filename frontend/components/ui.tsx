import type { ReactNode } from "react";

export function Panel({
  title,
  right,
  children,
  className = "",
}: {
  title?: string;
  right?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      className={`rounded-md border border-border bg-panel ${className}`}
    >
      {title && (
        <div className="flex items-center justify-between border-b border-border px-4 py-2">
          <h2 className="text-xs uppercase tracking-widest text-muted">
            {title}
          </h2>
          {right}
        </div>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}

export function Bar({ value, tone = "accent" }: { value: number; tone?: string }) {
  const toneClass =
    {
      accent: "bg-accent",
      good: "bg-good",
      warn: "bg-warn",
      bad: "bg-bad",
      vasp: "bg-vasp",
    }[tone] ?? "bg-accent";
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-panel2">
      <div
        className={`h-full ${toneClass}`}
        style={{ width: `${Math.max(0, Math.min(1, value)) * 100}%` }}
      />
    </div>
  );
}

export function Pill({
  children,
  tone = "muted",
}: {
  children: ReactNode;
  tone?: "muted" | "accent" | "good" | "warn" | "bad" | "vasp";
}) {
  const map: Record<string, string> = {
    muted: "border-border text-muted",
    accent: "border-accent/40 text-accent",
    good: "border-good/40 text-good",
    warn: "border-warn/40 text-warn",
    bad: "border-bad/40 text-bad",
    vasp: "border-vasp/40 text-vasp",
  };
  return (
    <span
      className={`inline-block rounded border px-1.5 py-0.5 text-[10px] uppercase tracking-wider ${map[tone]}`}
    >
      {children}
    </span>
  );
}
