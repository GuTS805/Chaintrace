"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

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
    const addr = value.trim().toLowerCase();
    if (addr) router.push(`/wallets/${addr}`);
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
        placeholder="0x… wallet address"
        spellCheck={false}
        autoFocus={autoFocus}
        aria-label="Wallet address"
        className="w-full bg-transparent text-text outline-none placeholder:text-muted"
      />
      <button
        type="submit"
        className="rounded border border-accent/50 bg-accent/10 px-4 py-1.5 text-xs uppercase tracking-widest text-accent hover:bg-accent/20"
      >
        run
      </button>
    </form>
  );
}
