"use client";

import { useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { motion, AnimatePresence } from "framer-motion";
import { AlertTriangle, X } from "lucide-react";
import { Button } from "./ui";

/**
 * A destructive-action confirmation, replacing native window.confirm() —
 * keyboard/focus-trapped via Radix, animated via framer-motion.
 */
export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel = "Delete",
  onConfirm,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  confirmLabel?: string;
  onConfirm: () => void | Promise<void>;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function confirm() {
    setBusy(true); setError(null);
    try { await onConfirm(); onOpenChange(false); }
    catch (e) { setError(e instanceof Error ? e.message : "The action could not be completed."); }
    finally { setBusy(false); }
  }
  return (
    <Dialog.Root open={open} onOpenChange={(next) => { if (!busy) { setError(null); onOpenChange(next); } }}>
      <AnimatePresence>
        {open && (
          <Dialog.Portal forceMount>
            <Dialog.Overlay asChild forceMount>
              <motion.div
                className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.15 }}
              />
            </Dialog.Overlay>
            <Dialog.Content asChild forceMount>
              <motion.div
                className="fixed left-1/2 top-1/2 z-50 w-[calc(100%-2rem)] max-w-sm -translate-x-1/2 -translate-y-1/2 rounded-card border border-soft-border bg-surface p-6 shadow-card-hover"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.15 }}
              >
                <div className="flex items-start gap-3">
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-bad-fill">
                    <AlertTriangle size={18} className="text-bad-text" />
                  </div>
                  <div className="flex-1">
                    <Dialog.Title className="font-display text-[15px] font-semibold text-heading">
                      {title}
                    </Dialog.Title>
                    <Dialog.Description className="mt-1.5 text-[13px] leading-relaxed text-muted">
                      {description}
                    </Dialog.Description>
                  </div>
                  <Dialog.Close asChild>
                    <button
                      className="rounded-btn p-1 text-muted hover:bg-surface-lavender hover:text-heading"
                      disabled={busy}
                      aria-label="Cancel"
                    >
                      <X size={16} />
                    </button>
                  </Dialog.Close>
                </div>

                {error && <p role="alert" className="mt-4 text-sm text-bad-text">{error}</p>}
                <div className="mt-6 flex justify-end gap-2">
                  <Dialog.Close asChild>
                    <Button variant="secondary" disabled={busy}>Cancel</Button>
                  </Dialog.Close>
                  <Button
                    variant="primary"
                    className="!bg-bad-text hover:!bg-bad-text/90"
                    disabled={busy}
                    onClick={() => void confirm()}
                  >
                    {busy ? "Working..." : confirmLabel}
                  </Button>
                </div>
              </motion.div>
            </Dialog.Content>
          </Dialog.Portal>
        )}
      </AnimatePresence>
    </Dialog.Root>
  );
}
