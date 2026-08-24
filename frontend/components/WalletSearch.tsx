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
      className="flex h-14 items-center gap-2 rounded-input bg-surface-lavender px-4 transition-all focus-within:border focus-within:border-primary focus-within:ring-2 focus-within:ring-primary-soft"
    >
      <span className="select-none font-mono text-primary">trace&gt;</span>
      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="0x… or T… wallet address"
        spellCheck={false}
        autoFocus={autoFocus}
        aria-label="Wallet address"
        className="w-full bg-transparent font-mono text-heading outline-none placeholder:text-muted"
      />
      <button
        type="submit"
        className="rounded-btn bg-primary px-6 py-2.5 text-[12px] font-medium text-white shadow-button transition-all hover:-translate-y-0.5 hover:bg-primary-hover active:translate-y-0"
      >
        Run
      </button>
    </form>
  );
}
