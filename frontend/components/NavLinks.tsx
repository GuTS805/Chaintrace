"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export function NavLinks() {
  const pathname = usePathname();
  
  const isCases = pathname?.startsWith("/cases");
  const isTrace = pathname?.startsWith("/trace") || pathname?.startsWith("/wallets");
  const isHome = !isCases && !isTrace;

  return (
    <nav className="flex items-center gap-1 text-[12px] font-medium uppercase tracking-[0.08em]">
      <Link
        href="/"
        className={`rounded-full px-4 py-2 transition-colors ${
          isHome
            ? "bg-primary-soft text-primary hover:bg-primary-soft/80"
            : "text-muted hover:bg-surface-lavender hover:text-primary"
        }`}
      >
        Home
      </Link>
      <Link
        href="/trace"
        className={`rounded-full px-4 py-2 transition-colors ${
          isTrace
            ? "bg-primary-soft text-primary hover:bg-primary-soft/80"
            : "text-muted hover:bg-surface-lavender hover:text-primary"
        }`}
      >
        Trace
      </Link>
      <Link
        href="/cases"
        className={`rounded-full px-4 py-2 transition-colors ${
          isCases
            ? "bg-primary-soft text-primary hover:bg-primary-soft/80"
            : "text-muted hover:bg-surface-lavender hover:text-primary"
        }`}
      >
        Cases
      </Link>
    </nav>
  );
}
