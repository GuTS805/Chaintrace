/** The trace-path mark: three hops terminating at a filled (attributed) node —
 * the same visual grammar as the transaction graph, in miniature. Used as the
 * app's logo everywhere. Now wrapped in a gradient chip per design spec. */
export function Mark({ size = 22, className = "" }: { size?: number; className?: string }) {
  return (
    <div
      className={`inline-flex items-center justify-center rounded-[10px] bg-gradient-to-br from-primary to-accent-pink ${className}`}
      style={{ width: size + 12, height: size + 12 }}
    >
      <svg
        width={size}
        height={size}
        viewBox="0 0 32 32"
        aria-hidden="true"
      >
        <path
          d="M7 24 L15 13 L25 8"
          fill="none"
          stroke="white"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <circle cx="7" cy="24" r="2.4" fill="white" stroke="white" strokeWidth="1.6" opacity="0.7" />
        <circle cx="15" cy="13" r="2" fill="white" stroke="white" strokeWidth="1.6" opacity="0.8" />
        <circle cx="25" cy="8" r="3" fill="white" />
      </svg>
    </div>
  );
}
