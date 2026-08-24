"use client";

import { useState } from "react";
import Link from "next/link";
import { Menu } from "lucide-react";
import { Mark } from "./Mark";
import { Sidebar } from "./Sidebar";
import { OfficerBadge } from "./OfficerBadge";
import { Kbd } from "./ui";

export function HeaderBar() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <header className="sticky top-0 z-20 mx-4 mt-4 rounded-card border border-soft-border bg-surface shadow-nav">
        <div className="mx-auto flex h-16 max-w-[1680px] items-center gap-4 px-6">
          <button
            onClick={() => setOpen(true)}
            className="rounded-btn p-2 text-muted transition-colors hover:bg-surface-lavender hover:text-heading"
            aria-label="Open menu"
          >
            <Menu size={20} />
          </button>

          <Link href="/" className="group flex items-center gap-2.5">
            <Mark size={22} />
            <span className="font-display text-[19px] font-bold tracking-tight text-heading">
              CHAIN<span className="text-primary">TRACE</span>
            </span>
          </Link>

          <div className="ml-auto hidden items-center gap-2 rounded-full bg-surface-lavender px-4 py-2 text-[12px] text-muted md:flex" style={{ width: 240 }}>
            <span>Search anywhere</span>
            <Kbd>⌘K</Kbd>
          </div>

          <OfficerBadge />
        </div>
      </header>

      <Sidebar open={open} onClose={() => setOpen(false)} />
    </>
  );
}
