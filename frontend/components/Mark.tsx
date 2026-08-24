/** The trace-path mark: three hops terminating at a filled (attributed) node —
 * the same visual grammar as the transaction graph, in miniature. Used as the
 * app's logo everywhere instead of a generic geometric glyph. */
export function Mark({ size = 22, className = "" }: { size?: number; className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      className={className}
      aria-hidden="true"
    >
      <path
        d="M7 24 L15 13 L25 8"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="text-accent"
      />
      <circle cx="7" cy="24" r="2.4" fill="#0a0b10" stroke="currentColor" strokeWidth="1.6" className="text-accent" />
      <circle cx="15" cy="13" r="2" fill="#0a0b10" stroke="currentColor" strokeWidth="1.6" className="text-accent" />
      <circle cx="25" cy="8" r="3" fill="currentColor" className="text-gold" />
    </svg>
  );
}
