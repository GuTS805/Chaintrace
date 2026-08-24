import type { ReactNode } from "react";

/**
 * BentoGrid: the base grid pages compose onto. 12 columns on large screens
 * (so a section can claim 3/4/6/8/12 columns — real proportion, not just
 * "big card, small card"), collapsing to 4 on mobile.
 */
export function BentoGrid({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`grid grid-cols-4 gap-4 md:grid-cols-12 ${className}`}>
      {children}
    </div>
  );
}

/**
 * Eyebrow: the small uppercase label used above a page title, a section,
 * or a data readout — typography doing the work a card border used to.
 */
export function Eyebrow({
  children,
  tone = "muted",
  className = "",
}: {
  children: ReactNode;
  tone?: "muted" | "accent";
  className?: string;
}) {
  return (
    <div
      className={`text-[11px] font-medium uppercase tracking-[0.1em] ${
        tone === "accent" ? "text-accent" : "text-muted"
      } ${className}`}
    >
      {children}
    </div>
  );
}

/**
 * Section: an unboxed content group — eyebrow + optional heading + body,
 * separated by whitespace and a hairline top border, not a bordered card.
 * Use this for most content; reach for Tile only for a handful of major
 * conceptual containers (attribution, graph, risk).
 */
export function Section({
  eyebrow,
  right,
  children,
  className = "",
  bordered = true,
}: {
  eyebrow?: ReactNode;
  right?: ReactNode;
  children: ReactNode;
  className?: string;
  bordered?: boolean;
}) {
  return (
    <section className={`${bordered ? "border-t border-border pt-6" : ""} ${className}`}>
      {eyebrow && (
        <div className="mb-4 flex items-center justify-between">
          <Eyebrow>{eyebrow}</Eyebrow>
          {right}
        </div>
      )}
      {children}
    </section>
  );
}

/**
 * Tile: a bordered surface, reserved for major conceptual sections (not
 * every data point). Thin translucent border, minimal radius, no glow.
 */
export function Tile({
  title,
  right,
  children,
  className = "",
  bodyClassName = "p-6",
  interactive = false,
}: {
  title?: string;
  right?: ReactNode;
  children: ReactNode;
  /** Include col-span and row-span classes here to place the tile in a BentoGrid. */
  className?: string;
  bodyClassName?: string;
  /** Subtle border-brightness lift on hover, for tiles that lead somewhere. */
  interactive?: boolean;
}) {
  return (
    <section
      className={`flex flex-col overflow-hidden rounded-lg border border-border bg-panel transition-colors duration-200 ${
        interactive ? "hover:border-borderStrong" : ""
      } ${className}`}
    >
      {title && (
        <div className="flex items-center justify-between border-b border-border px-6 py-4">
          <Eyebrow>{title}</Eyebrow>
          {right}
        </div>
      )}
      <div className={`flex-1 ${bodyClassName}`}>{children}</div>
    </section>
  );
}

/** @deprecated alias kept from the bento-grid migration — same as Tile. */
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
  height = "h-1.5",
}: {
  value: number;
  tone?: string;
  threshold?: number;
  height?: string;
}) {
  const clamped = Math.max(0, Math.min(1, value));
  return (
    <div className={`relative w-full overflow-hidden rounded-full bg-panel3 ${height}`}>
      <div
        className={`h-full rounded-full transition-[width] duration-500 ease-out ${TONE_BG[tone] ?? "bg-accent"}`}
        style={{ width: `${clamped * 100}%` }}
      />
      {threshold !== undefined && (
        <span
          className="absolute top-0 h-full w-px bg-text/40"
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
      className={`inline-block rounded border px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wider ${map[tone]} ${className}`}
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
      className={`rounded-md border px-2 py-1 text-[11px] transition-colors ${
        active
          ? "border-accent/50 bg-accent/10 text-accent"
          : "border-border text-muted hover:border-borderStrong hover:text-text"
      } ${className}`}
    >
      {children}
    </button>
  );
}

/**
 * Button: the two understated button styles the whole app should use for
 * real actions — solid indigo for the primary action per view, thin-border
 * transparent for everything else. Small radius, no glow, no pill shape.
 */
export function Button({
  children,
  onClick,
  type = "button",
  variant = "secondary",
  disabled = false,
  className = "",
}: {
  children: ReactNode;
  onClick?: () => void;
  type?: "button" | "submit";
  variant?: "primary" | "secondary";
  disabled?: boolean;
  className?: string;
}) {
  const base = "rounded-md px-4 py-2 text-[13px] font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-40";
  const variants: Record<string, string> = {
    primary: "bg-accent text-white hover:bg-accent/90",
    secondary: "border border-border text-text hover:border-borderStrong",
  };
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`${base} ${variants[variant]} ${className}`}
    >
      {children}
    </button>
  );
}
