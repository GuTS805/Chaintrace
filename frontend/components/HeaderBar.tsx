"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { FolderOpen, LayoutDashboard, ScanLine, Search, ShieldCheck, BarChart3, FileText } from "lucide-react";
import { Mark } from "./Mark";
import { OfficerBadge } from "./OfficerBadge";
import { Kbd } from "./ui";

const links = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/trace", label: "Wallet tracing", icon: ScanLine },
  { href: "/cases", label: "Case workspace", icon: FolderOpen },
];

export function HeaderBar() {
  const pathname = usePathname();
  const login = pathname === "/login";
  return (
    <header className="app-header sticky top-0 z-30 border-b border-soft-border backdrop-blur-xl">
      <div className="mx-auto flex h-[68px] max-w-[1660px] items-center gap-2 sm:gap-5 px-4 sm:px-8">
        <Link href="/" aria-label="ChainTrace overview" className="flex shrink-0 items-center gap-2 sm:gap-3">
          <span className="flex h-9 w-9 sm:h-10 sm:w-10 items-center justify-center brand-emblem rounded-xl border border-primary/20 bg-primary-soft"><Mark size={23} /></span>
          <span><span className="block font-display text-[18px] font-bold tracking-tight text-heading">CHAIN<span className="text-primary">TRACE</span></span><span className="hidden min-[375px]:block text-[9px] uppercase tracking-[.2em] text-muted">Blockchain intelligence</span></span>
        </Link>
        {!login && <nav aria-label="Main navigation" className="ml-5 hidden items-center gap-1 lg:flex">
          {links.map(({ href, label, icon: Icon }) => {
            const active = href === "/" ? pathname === "/" : pathname?.startsWith(href) || (href === "/trace" && pathname?.startsWith("/wallets"));
            return <Link key={href} href={href} aria-current={active ? "page" : undefined} className={`flex items-center gap-2 rounded-btn px-3 py-2.5 text-[13px] font-medium transition-colors ${active ? "bg-primary-soft text-primary" : "text-muted hover:bg-surface-lavender hover:text-heading"}`}><Icon size={16} />{label}</Link>;
          })}
          <Link href="/#analytics" className="hidden min-[1320px]:flex items-center gap-2 rounded-btn px-3 py-2.5 text-[13px] text-muted hover:text-primary"><BarChart3 size={16} />Analytics</Link>
          <Link href="/#documentation" className="hidden min-[1320px]:flex items-center gap-2 rounded-btn px-3 py-2.5 text-[13px] text-muted hover:text-primary"><FileText size={16} />Docs</Link>
        </nav>}
        <div className="ml-auto flex items-center gap-1 sm:gap-3">
          {!login && <button type="button" onClick={() => window.dispatchEvent(new Event("chaintrace:search"))} aria-label="Search wallets and cases" className="flex min-h-10 items-center gap-3 rounded-btn border border-soft-border px-3 text-xs text-muted transition-colors hover:border-primary/40 hover:text-heading"><Search size={16} /><span className="hidden xl:inline">Search wallet / case...</span><span className="hidden xl:inline"><Kbd>Ctrl K</Kbd></span></button>}
          {login ? <span className="flex items-center gap-2 text-xs text-muted"><ShieldCheck size={16} className="text-primary" /><span className="hidden sm:inline">Officer access</span></span> : <OfficerBadge />}
        </div>
      </div>
      {!login && <nav aria-label="Mobile navigation" className="grid grid-cols-3 border-t border-soft-border px-2 lg:hidden">{links.map(({ href, label, icon: Icon }) => {
        const active = href === "/" ? pathname === "/" : pathname?.startsWith(href) || (href === "/trace" && pathname?.startsWith("/wallets"));
        return <Link key={href} href={href} aria-current={active ? "page" : undefined} className={`flex min-h-12 items-center justify-center gap-1.5 border-b-2 text-[11px] font-medium ${active ? "border-primary text-primary" : "border-transparent text-muted"}`}><Icon size={14} />{label}</Link>;
      })}</nav>}
    </header>
  );
}
