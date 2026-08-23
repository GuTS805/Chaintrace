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
      className={`rounded-md border border-border bg-panel shadow-panel ${className}`}
    >
      {title && (
        <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
          <div className="flex items-center gap-2">
            <span className="h-3 w-[3px] rounded-full bg-accent" />
            <h2 className="text-[10px] uppercase tracking-widest2 text-muted">
              {title}
            </h2>
          </div>
          {right}
        </div>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}

const TONE_BG: Record<string, string> = {
  accent: "bg-accent",
  good: "bg-good",
  warn: "bg-warn",
  bad: "bg-bad",
  vasp: "bg-vasp",
  muted: "bg-muted",
};

export function Bar({
  value,
  tone = "accent",
  threshold,
  height = "h-2",
}: {
  value: number;
  tone?: string;
  threshold?: number;
  height?: string;
}) {
  const clamped = Math.max(0, Math.min(1, value));
  return (
    <div className={`relative w-full overflow-hidden rounded-full bg-panel2 ${height}`}>
      <div
        className={`h-full rounded-full ${TONE_BG[tone] ?? "bg-accent"}`}
        style={{ width: `${clamped * 100}%` }}
      />
      {threshold !== undefined && (
        <span
          className="absolute top-0 h-full w-px bg-text/70"
          style={{ left: `${Math.max(0, Math.min(1, threshold)) * 100}%` }}
          aria-hidden
        />
      )}
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
