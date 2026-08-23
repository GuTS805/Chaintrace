"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export function WalletSearch({ initial = "" }: { initial?: string }) {
  const router = useRouter();
  const [value, setValue] = useState(initial);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const addr = value.trim().toLowerCase();
    if (addr) router.push(`/wallets/${addr}`);
  }

  return (
    <form onSubmit={submit} className="flex gap-2">
      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="0x… wallet address"
        spellCheck={false}
        className="w-full rounded border border-border bg-panel2 px-3 py-2 text-text outline-none placeholder:text-muted focus:border-accent"
      />
      <button
        type="submit"
        className="rounded border border-accent/50 bg-accent/10 px-4 py-2 text-accent hover:bg-accent/20"
      >
        trace
      </button>
    </form>
  );
}
