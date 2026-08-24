import type { ReactNode } from "react";

/**
 * BentoGrid: the base grid every page composes tiles onto. 12 columns on
 * large screens (so a tile can claim 3/4/6/8/12 columns — real proportion,
 * not just "big card, small card"), collapsing to 4 on mobile so span
 * classes like `md:col-span-4` still read as "half" rather than overflowing.
 */
export function BentoGrid({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`grid grid-cols-4 gap-3 md:grid-cols-12 ${className}`}>
      {children}
    </div>
  );
}

export function Tile({
  title,
  right,
  children,
  className = "",
  bodyClassName = "p-4",
  interactive = false,
}: {
  title?: string;
  right?: ReactNode;
  children: ReactNode;
  /** Include col-span and row-span classes here to place the tile in a BentoGrid. */
  className?: string;
  bodyClassName?: string;
  /** Subtle lift + border glow on hover, for tiles that lead somewhere. */
  interactive?: boolean;
}) {
  return (
    <section
      className={`flex flex-col overflow-hidden rounded-2xl border border-border bg-panel shadow-panel transition-[transform,box-shadow,border-color] duration-200 ${
        interactive
          ? "hover:-translate-y-0.5 hover:border-accent/40 hover:shadow-glow"
          : ""
      } ${className}`}
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
      <div className={`flex-1 ${bodyClassName}`}>{children}</div>
    </section>
  );
}

/** @deprecated alias kept during the bento-grid migration — same as Tile. */
export const Panel = Tile;

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
