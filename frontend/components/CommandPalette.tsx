"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Clock, Search } from "lucide-react";
import { getRecents } from "@/lib/recents";
import { shortAddr } from "@/lib/format";
import { Kbd } from "./ui";
import * as Dialog from "@radix-ui/react-dialog";

/** Global ⌘K / Ctrl+K lookup — an investigator running many wallet lookups a
 * day shouldn't have to leave the keyboard or navigate to the home page to
 * start the next trace. Also surfaces recent lookups. */
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
    const show = () => setOpen(true);
    window.addEventListener("chaintrace:search", show);
    window.addEventListener("keydown", onKey);
    return () => { window.removeEventListener("keydown", onKey); window.removeEventListener("chaintrace:search", show); };
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
    router.push(`/wallets/${encodeURIComponent(address)}`);
  }

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (trimmed) go(trimmed.toLowerCase().startsWith("0x") ? trimmed.toLowerCase() : trimmed);
  }

  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm" />
        <Dialog.Content aria-describedby="search-description" className="fixed left-1/2 top-[14vh] z-50 w-[calc(100%-2rem)] max-w-lg -translate-x-1/2 overflow-hidden rounded-card border border-soft-border bg-surface shadow-card-hover">
          <Dialog.Title className="sr-only">Search the workspace</Dialog.Title>
          <Dialog.Description id="search-description" className="sr-only">Enter a wallet address, reopen a recent trace, or navigate to cases.</Dialog.Description>
        <form onSubmit={submit} className="flex items-center gap-2 border-b border-soft-border px-4 py-3">
          <Search size={16} className="shrink-0 text-primary" />
          <input
            aria-label="Search wallet address"
            ref={inputRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="0x… or T… address, or jump to cases"
            spellCheck={false}
            className="w-full bg-transparent text-sm text-heading outline-none placeholder:text-muted"
          />
          <Dialog.Close aria-label="Close search"><Kbd>esc</Kbd></Dialog.Close>
        </form>

        <div className="max-h-80 overflow-y-auto p-2">
          {trimmed && (
            <button
              type="button"
              onClick={() => go(trimmed.toLowerCase().startsWith("0x") ? trimmed.toLowerCase() : trimmed)}
              className="flex w-full items-center gap-2 rounded-btn px-3 py-2 text-left text-sm text-body hover:bg-surface-lavender"
            >
              <ArrowRight size={14} className="shrink-0 text-primary" />
              <span>
                Trace <span className="font-mono text-heading">{trimmed}</span>
              </span>
            </button>
          )}

          {!trimmed && (
            <button
              type="button"
              onClick={() => {
                setOpen(false);
                router.push("/trace");
              }}
              className="flex w-full items-center gap-2 rounded-btn px-3 py-2 text-left text-sm text-body hover:bg-surface-lavender"
            >
              <ArrowRight size={14} className="shrink-0 text-primary" />
              <span>Start a trace</span>
            </button>
          )}

          <button
            type="button"
            onClick={() => {
              setOpen(false);
              router.push("/cases");
            }}
            className="flex w-full items-center gap-2 rounded-btn px-3 py-2 text-left text-sm text-body hover:bg-surface-lavender"
          >
            <ArrowRight size={14} className="shrink-0 text-primary" />
            <span>Go to cases</span>
          </button>

          {filteredRecents.length > 0 && (
            <div className="mt-2 border-t border-soft-border pt-2">
              <div className="flex items-center gap-1.5 px-3 pb-1 text-[10px] uppercase tracking-widest text-muted">
                <Clock size={11} />
                Recent lookups
              </div>
              {filteredRecents.map((r) => (
                <button
                  key={r.address}
                  type="button"
                  onClick={() => go(r.address)}
                  className="flex w-full items-center gap-2 rounded-btn px-3 py-2 text-left text-sm hover:bg-surface-lavender"
                >
                  <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-muted" />
                  <span className="font-mono text-heading">{shortAddr(r.address, 8, 6)}</span>
                  {r.label && <span className="text-xs text-muted">{r.label}</span>}
                </button>
              ))}
            </div>
          )}
        </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
