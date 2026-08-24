import type { Metadata } from "next";
import Link from "next/link";
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
    <html lang="en">
      <body className="min-h-screen bg-bg font-sans text-sm text-text">
        <header className="sticky top-0 z-20 border-b border-border bg-bg/85 backdrop-blur">
          <div className="mx-auto flex max-w-[1600px] items-center gap-6 px-5 py-3">
            <Link href="/" className="group flex items-center gap-2.5">
              <Mark size={22} />
              <span className="font-display text-[15px] font-semibold tracking-tight text-text">
                CHAIN<span className="text-accent">TRACE</span>
              </span>
            </Link>
            <nav className="flex items-center gap-1 text-[11px] uppercase tracking-widest text-muted">
              <Link href="/" className="rounded px-2 py-1 hover:bg-panel hover:text-text">
                trace
              </Link>
              <Link href="/cases" className="rounded px-2 py-1 hover:bg-panel hover:text-text">
                cases
              </Link>
            </nav>
            <div className="hidden items-center gap-1.5 rounded border border-border bg-panel px-2 py-1 text-[11px] text-dim md:flex">
              <span>search anywhere</span>
              <Kbd>⌘K</Kbd>
            </div>
            <OfficerBadge />
          </div>
        </header>
        <main className="mx-auto max-w-[1600px] px-5 py-8">
          <AuthGate>{children}</AuthGate>
        </main>
        <CommandPalette />
      </body>
    </html>
  );
}
