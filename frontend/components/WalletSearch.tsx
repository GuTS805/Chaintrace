"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { ArrowRight, Search } from "lucide-react";
import { pushRecent } from "@/lib/recents";

export function WalletSearch({
  initial = "",
  autoFocus = false,
  showNetwork = false,
}: {
  initial?: string;
  autoFocus?: boolean;
  showNetwork?: boolean;
}) {
  const router = useRouter();
  const [value, setValue] = useState(initial);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = value.trim();
    // EVM addresses are case-insensitive hex; lowercase for consistency. Tron
    // (and other base58) addresses are case-sensitive/checksummed, so leave
    // them untouched.
    const addr = trimmed.toLowerCase().startsWith("0x") ? trimmed.toLowerCase() : trimmed;
    if (addr) {
      pushRecent(addr);
      router.push(`/wallets/${encodeURIComponent(addr)}`);
    }
  }

  return (
    <form
      onSubmit={submit}
      className="wallet-search flex min-h-16 items-center gap-2 rounded-input border border-soft-border bg-[#0D1025] p-2 pl-4 transition-all focus-within:border-primary focus-within:ring-2 focus-within:ring-primary-soft"
    >
      <Search size={16} className="shrink-0 text-primary" />
      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="0x… or T… wallet address"
        spellCheck={false}
        autoFocus={autoFocus}
        aria-label="Wallet address"
        className="min-w-0 w-full bg-transparent font-mono text-heading outline-none placeholder:text-muted"
      />
      {showNetwork && <span className="network-badge" title="Network detected from address"><span>{value.trim().startsWith("T") ? "T" : "E"}</span>{value.trim().startsWith("T") ? "Tron" : "Ethereum"}</span>}
      <button
        type="submit"
        disabled={!value.trim()}
        aria-label="Trace wallet"
        className="flex min-h-11 shrink-0 items-center gap-1.5 action-primary rounded-btn bg-primary px-3 sm:px-5 disabled:opacity-40 py-2.5 text-[12px] font-medium text-[#091126] shadow-button transition-all hover:-translate-y-0.5 hover:bg-primary-hover active:translate-y-0"
      >
        Trace
        <ArrowRight size={14} />
      </button>
    </form>
  );
}
