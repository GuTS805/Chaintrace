import type { Metadata } from "next";
import Link from "next/link";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import { AuthGate } from "@/components/AuthGate";
import { OfficerBadge } from "@/components/OfficerBadge";
import { CommandPalette } from "@/components/CommandPalette";
import { Mark } from "@/components/Mark";
import { Kbd } from "@/components/ui";
import "./globals.css";

export const metadata: Metadata = {
  title: "ChainTrace",
  description:
    "Attribute unknown wallets to VASPs with a calibrated confidence score and a traceable evidence chain.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${GeistSans.variable} ${GeistMono.variable}`}>
      <body className="min-h-screen bg-bg font-sans text-sm text-text">
        <header className="sticky top-0 z-20 border-b border-border bg-bg/90 backdrop-blur">
          <div className="mx-auto flex max-w-[1440px] items-center gap-8 px-8 py-4">
            <Link href="/" className="group flex items-center gap-2.5">
              <Mark size={20} />
              <span className="font-display text-[14px] font-medium tracking-tight text-text">
                CHAIN<span className="text-accent">TRACE</span>
              </span>
            </Link>
            <nav className="flex items-center gap-5 text-[11px] font-medium uppercase tracking-[0.1em] text-muted">
              <Link href="/" className="transition-colors hover:text-text">
                Trace
              </Link>
              <Link href="/cases" className="transition-colors hover:text-text">
                Cases
              </Link>
            </nav>
            <div className="hidden items-center gap-2 rounded-md border border-border px-2.5 py-1.5 text-[11px] text-dim md:flex">
              <span>Search anywhere</span>
              <Kbd>⌘K</Kbd>
            </div>
            <OfficerBadge />
          </div>
        </header>
        <main className="mx-auto max-w-[1440px] px-8 py-14">
          <AuthGate>{children}</AuthGate>
        </main>
        <CommandPalette />
      </body>
    </html>
  );
}
