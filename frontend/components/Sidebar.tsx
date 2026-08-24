"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { FolderOpen, Home, Search, X } from "lucide-react";
import { Mark } from "./Mark";

const LINKS = [
  { href: "/", label: "Home", icon: Home, match: (p: string) => p === "/" },
  { href: "/trace", label: "Trace", icon: Search, match: (p: string) => p.startsWith("/trace") || p.startsWith("/wallets") },
  { href: "/cases", label: "Cases", icon: FolderOpen, match: (p: string) => p.startsWith("/cases") },
];

export function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  const pathname = usePathname() ?? "/";

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.18 }}
            onClick={onClose}
          />
          <motion.aside
            className="fixed inset-y-0 left-0 z-40 flex w-72 flex-col border-r border-soft-border bg-surface"
            initial={{ x: "-100%" }}
            animate={{ x: 0 }}
            exit={{ x: "-100%" }}
            transition={{ type: "spring", damping: 28, stiffness: 300 }}
          >
            <div className="flex items-center justify-between border-b border-soft-border px-5 py-4">
              <Link href="/" onClick={onClose} className="group flex items-center gap-2.5">
                <Mark size={20} />
                <span className="font-display text-[18px] font-bold tracking-tight text-heading">
                  CHAIN<span className="text-primary">TRACE</span>
                </span>
              </Link>
              <button
                onClick={onClose}
                className="rounded-btn p-1.5 text-muted hover:bg-surface-lavender hover:text-heading"
                aria-label="Close menu"
              >
                <X size={18} />
              </button>
            </div>

            <nav className="flex-1 space-y-1 p-3">
              {LINKS.map((link) => {
                const active = link.match(pathname);
                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    onClick={onClose}
                    className={`flex items-center gap-3 rounded-btn px-3.5 py-2.5 text-[13px] font-medium transition-colors ${
                      active
                        ? "bg-primary-soft text-primary"
                        : "text-muted hover:bg-surface-lavender hover:text-heading"
                    }`}
                  >
                    <link.icon size={17} />
                    {link.label}
                  </Link>
                );
              })}
            </nav>

            <div className="border-t border-soft-border p-4 text-[11px] text-muted">
              SIH 26182 · forensic wallet attribution
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}
