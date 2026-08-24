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
    <div className={`grid grid-cols-4 gap-6 md:grid-cols-12 ${className}`}>
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
      className={`text-[10px] font-semibold uppercase tracking-[0.12em] ${
        tone === "accent" ? "text-primary" : "text-muted"
      } ${className}`}
    >
      {children}
    </div>
  );
}

/**
 * Section: an unboxed content group — eyebrow + optional heading + body,
 * separated by whitespace and a hairline top border, not a bordered card.
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
    <section className={`${bordered ? "border-t border-soft-border pt-6" : ""} ${className}`}>
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
 * Tile: a dark floating card on a near-black canvas — a thin hairline
 * border does the separation a shadow alone can't do against black.
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
  /** Subtle lift on hover, for tiles that lead somewhere. */
  interactive?: boolean;
}) {
  return (
    <section
      className={`flex flex-col overflow-hidden rounded-card border border-soft-border bg-surface shadow-card ${
        interactive
          ? "transition-all duration-200 hover:-translate-y-1 hover:border-primary/30 hover:shadow-card-hover"
          : ""
      } ${className}`}
    >
      {title && (
        <div className="flex items-center justify-between px-6 py-4">
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

export function Bar({
  value,
  tone = "primary",
  threshold,
  height = "h-1.5",
}: {
  value: number;
  tone?: string;
  threshold?: number;
  height?: string;
}) {
  const clamped = Math.max(0, Math.min(1, value));
  const toneMap: Record<string, string> = {
    primary: "bg-primary",
    good: "bg-good-text",
    warn: "bg-warn-text",
    bad: "bg-bad-text",
    muted: "bg-muted",
  };
  return (
    <div className={`relative w-full overflow-hidden rounded-full bg-neutral-fill ${height}`}>
      <div
        className={`h-full rounded-full transition-[width] duration-500 ease-out ${toneMap[tone] ?? "bg-primary"}`}
        style={{ width: `${clamped * 100}%` }}
      />
      {threshold !== undefined && (
        <span
          className="absolute top-0 h-full w-px bg-heading/30"
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
  tone?: "muted" | "accent" | "gold" | "good" | "warn" | "bad" | "info" | "neutral";
  className?: string;
}) {
  const map: Record<string, string> = {
    good: "bg-good-fill text-good-text",
    warn: "bg-warn-fill text-warn-text",
    muted: "bg-neutral-fill text-neutral-text",
    neutral: "bg-neutral-fill text-neutral-text",
    accent: "bg-info-fill text-info-text",
    info: "bg-info-fill text-info-text",
    gold: "bg-info-fill text-info-text",
    bad: "bg-bad-fill text-bad-text",
  };
  return (
    <span
      className={`inline-block rounded-full px-3 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${map[tone] ?? map.muted} ${className}`}
    >
      {children}
    </span>
  );
}

/** A single keyboard-key hint, e.g. for the command palette shortcut. */
export function Kbd({ children }: { children: ReactNode }) {
  return (
    <kbd className="rounded-lg border border-soft-border bg-surface-lavender px-1.5 py-0.5 font-mono text-[10px] text-muted shadow-sm">
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
      className={`rounded-btn border px-2.5 py-1 text-[11px] font-medium transition-all ${
        active
          ? "border-primary/30 bg-primary-soft text-primary"
          : "border-soft-border text-muted hover:bg-surface-lavender hover:text-primary"
      } ${className}`}
    >
      {children}
    </button>
  );
}

/**
 * Button: two clean button styles — solid primary for the main action per
 * view, thin-border secondary for everything else.
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
  const base =
    "rounded-btn px-5 py-2.5 text-[13px] font-medium transition-all disabled:cursor-not-allowed disabled:opacity-40";
  const variants: Record<string, string> = {
    primary:
      "bg-primary text-[#1A1206] shadow-button hover:bg-primary-hover hover:-translate-y-0.5 active:translate-y-0",
    secondary:
      "border border-soft-border text-heading hover:bg-surface-lavender",
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
