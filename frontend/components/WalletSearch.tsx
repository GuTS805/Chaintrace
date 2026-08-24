"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { pushRecent } from "@/lib/recents";

export function WalletSearch({
  initial = "",
  autoFocus = false,
}: {
  initial?: string;
  autoFocus?: boolean;
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
      router.push(`/wallets/${addr}`);
    }
  }

  return (
    <form
      onSubmit={submit}
      className="flex items-center gap-2 rounded-md border border-border bg-panel px-3 py-2 focus-within:border-accent"
    >
      <span className="select-none text-accent">trace&gt;</span>
      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="0x… or T… wallet address"
        spellCheck={false}
        autoFocus={autoFocus}
        aria-label="Wallet address"
        className="w-full bg-transparent text-text outline-none placeholder:text-muted"
      />
      <button
        type="submit"
        className="rounded-md bg-accent px-4 py-1.5 text-[12px] font-medium text-white transition-colors hover:bg-accent/90"
      >
        Run
      </button>
    </form>
  );
}
