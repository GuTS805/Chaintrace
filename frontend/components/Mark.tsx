/** The ChainTrace mark: a hexagon (a block) with a magnifying glass inside
 * it (attribution as "search inside the chain"), a single amber accent dot
 * standing in for the confidence signal. Rendered on a near-black chip. */
export function Mark({ size = 22, className = "" }: { size?: number; className?: string }) {
  return (
    <div
      className={`inline-flex shrink-0 items-center justify-center rounded-[10px] bg-[#0a0a0a] ${className}`}
      style={{ width: size + 12, height: size + 12 }}
    >
      <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
        {/* hexagon block */}
        <path
          d="M16 3.5 L26.83 9.75 L26.83 22.25 L16 28.5 L5.17 22.25 L5.17 9.75 Z"
          fill="none"
          stroke="#F3F1EA"
          strokeWidth="1.7"
          strokeLinejoin="round"
        />

        {/* magnifying glass */}
        <circle cx="14" cy="14.6" r="4.3" fill="none" stroke="#F3F1EA" strokeWidth="1.7" />
        <line x1="17.2" y1="17.8" x2="21" y2="21.6" stroke="#F3F1EA" strokeWidth="1.7" strokeLinecap="round" />

        {/* confidence accent */}
        <circle cx="16" cy="25.2" r="1.5" fill="#F2A93B" />
      </svg>
    </div>
  );
}
