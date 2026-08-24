"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { getRecents } from "@/lib/recents";
import { shortAddr } from "@/lib/format";
import { Kbd } from "./ui";

/** Global ⌘K / Ctrl+K lookup — an investigator running many wallet lookups a
 * day shouldn't have to leave the keyboard or navigate to the home page to
 * start the next trace. Also surfaces recent lookups (Elliptic/TRM's
 * "hotkeys + quick-arrange for volume caseloads" pattern). */
export function CommandPalette() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [value, setValue] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const isK = e.key.toLowerCase() === "k";
      if ((e.metaKey || e.ctrlKey) && isK) {
        e.preventDefault();
        setOpen((o) => !o);
      }
      if (e.key === "Escape") setOpen(false);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    if (open) {
      setValue("");
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [open]);

  if (!open) return null;

  const recents = getRecents();
  const trimmed = value.trim();
  const filteredRecents = trimmed
    ? recents.filter((r) => r.address.toLowerCase().includes(trimmed.toLowerCase()))
    : recents;

  function go(address: string) {
    setOpen(false);
    router.push(`/wallets/${address}`);
  }

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (trimmed) go(trimmed.toLowerCase().startsWith("0x") ? trimmed.toLowerCase() : trimmed);
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-bg/70 pt-[14vh] backdrop-blur-sm"
      onClick={() => setOpen(false)}
    >
      <div
        role="dialog"
        aria-label="Command palette"
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-lg overflow-hidden rounded-lg border border-borderStrong bg-panel shadow-2xl"
      >
        <form onSubmit={submit} className="flex items-center gap-2 border-b border-border px-4 py-3">
          <span className="text-accent">trace&gt;</span>
          <input
            ref={inputRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="0x… or T… address, or jump to cases"
            spellCheck={false}
            className="w-full bg-transparent text-sm text-text outline-none placeholder:text-dim"
          />
          <Kbd>esc</Kbd>
        </form>

        <div className="max-h-80 overflow-y-auto p-2">
          {trimmed && (
            <button
              type="button"
              onClick={() => go(trimmed.toLowerCase().startsWith("0x") ? trimmed.toLowerCase() : trimmed)}
              className="flex w-full items-center gap-2 rounded px-3 py-2 text-left text-sm hover:bg-panel2"
            >
              <span className="text-accent">→</span>
              <span>
                Trace <span className="font-mono text-text">{trimmed}</span>
              </span>
            </button>
          )}

          <button
            type="button"
            onClick={() => {
              setOpen(false);
              router.push("/cases");
            }}
            className="flex w-full items-center gap-2 rounded px-3 py-2 text-left text-sm hover:bg-panel2"
          >
            <span className="text-accent">→</span>
            <span>Go to cases</span>
          </button>

          {filteredRecents.length > 0 && (
            <div className="mt-2 border-t border-border pt-2">
              <div className="px-3 pb-1 text-[10px] uppercase tracking-widest text-dim">
                Recent lookups
              </div>
              {filteredRecents.map((r) => (
                <button
                  key={r.address}
                  type="button"
                  onClick={() => go(r.address)}
                  className="flex w-full items-center gap-2 rounded px-3 py-2 text-left text-sm hover:bg-panel2"
                >
                  <span className="text-dim">◇</span>
                  <span className="font-mono text-text">{shortAddr(r.address, 8, 6)}</span>
                  {r.label && <span className="text-xs text-muted">{r.label}</span>}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
