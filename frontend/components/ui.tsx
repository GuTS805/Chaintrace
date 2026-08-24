import type { ReactNode } from "react";

export function Panel({
  title,
  right,
  children,
  className = "",
  bodyClassName = "p-4",
}: {
  title?: string;
  right?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
}) {
  return (
    <section
      className={`rounded-lg border border-border bg-panel shadow-panel ${className}`}
    >
      {title && (
        <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
          <div className="flex items-center gap-2">
            <span className="h-3 w-[3px] rounded-full bg-accent" />
            <h2 className="text-[10px] uppercase tracking-widest text-muted">
              {title}
            </h2>
          </div>
          {right}
        </div>
      )}
      <div className={bodyClassName}>{children}</div>
    </section>
  );
}

const TONE_BG: Record<string, string> = {
  accent: "bg-accent",
  gold: "bg-gold",
  good: "bg-good",
  warn: "bg-warn",
  bad: "bg-bad",
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
        className={`h-full rounded-full transition-[width] duration-500 ease-out ${TONE_BG[tone] ?? "bg-accent"}`}
        style={{ width: `${clamped * 100}%` }}
      />
      {threshold !== undefined && (
        <span
          className="absolute top-0 h-full w-px bg-text/50"
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
  className = "",
}: {
  children: ReactNode;
  tone?: "muted" | "accent" | "gold" | "good" | "warn" | "bad";
  className?: string;
}) {
  const map: Record<string, string> = {
    muted: "border-border text-muted",
    accent: "border-accent/40 text-accent",
    gold: "border-gold/40 text-gold",
    good: "border-good/40 text-good",
    warn: "border-warn/40 text-warn",
    bad: "border-bad/40 text-bad",
  };
  return (
    <span
      className={`inline-block rounded border px-1.5 py-0.5 text-[10px] uppercase tracking-wider ${map[tone]} ${className}`}
    >
      {children}
    </span>
  );
}

/** A single keyboard-key hint, e.g. for the command palette shortcut. */
export function Kbd({ children }: { children: ReactNode }) {
  return (
    <kbd className="rounded border border-border bg-panel2 px-1.5 py-0.5 font-mono text-[10px] text-muted">
      {children}
    </kbd>
  );
}

/** A borderless, low-emphasis action button used in toolbars/headers. */
export function GhostButton({
  children,
  onClick,
  active = false,
  className = "",
  title,
}: {
  children: ReactNode;
  onClick?: () => void;
  active?: boolean;
  className?: string;
  title?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={title}
      className={`rounded border px-2 py-1 text-[11px] transition-colors ${
        active
          ? "border-accent/50 bg-accent/10 text-accent"
          : "border-border text-muted hover:border-accent/40 hover:text-accent"
      } ${className}`}
    >
      {children}
    </button>
  );
}
