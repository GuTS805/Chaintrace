export function shortAddr(address: string, head = 6, tail = 4): string {
  if (address.length <= head + tail + 2) return address;
  return `${address.slice(0, head)}…${address.slice(-tail)}`;
}

export function pct(x: number, digits = 0): string {
  return `${(x * 100).toFixed(digits)}%`;
}

export function weiToEth(wei: string, digits = 3): string {
  const n = Number(wei) / 1e18;
  if (!Number.isFinite(n)) return "0";
  return n.toFixed(digits);
}

export function fmtTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toISOString().replace("T", " ").slice(0, 16);
}

export const SIGNAL_LABEL: Record<string, string> = {
  HOP_PATH: "hop path",
  DEPOSIT_SWEEP: "deposit sweep",
  COUNTERPARTY_OVERLAP: "counterparty overlap",
  TEMPORAL_CORRELATION: "temporal correlation",
  KNOWN_LABEL: "known label",
  PATTERN_SIMILARITY: "pattern similarity",
};

export const DEMO_WALLETS: { label: string; address: string; note: string }[] = [
  {
    label: "Ransomware → exchange",
    address: "0xb8d31a8c81282ce8cda98988e14f014b2c36edc3",
    note: "clean attribution (Binance)",
  },
  {
    label: "Peel chain",
    address: "0x3d2a2561bf2b18e85fdc482a15674cc977f95b3f",
    note: "moderate (Kraken)",
  },
  {
    label: "No VASP linkage",
    address: "0x1226019c453f6fd2e7021fd1eb30c61cb4766772",
    note: "insufficient evidence",
  },
  {
    label: "Two exchanges",
    address: "0xed56909537fdf8a83d918fa5521545f09ef07a17",
    note: "ambiguous split",
  },
  {
    label: "Real on-chain wallet",
    address: "0x216b75231dfec0a4716b602ab00669fa568ad09b",
    note: "real: Kraken deposit",
  },
];
