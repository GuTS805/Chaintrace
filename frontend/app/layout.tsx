import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "VASP Attribution",
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
      <body className="min-h-screen bg-bg font-mono text-sm text-text">
        <header className="border-b border-border bg-panel">
          <div className="mx-auto flex max-w-[1400px] items-center gap-6 px-5 py-3">
            <Link href="/" className="flex items-center gap-2">
              <span className="text-accent">◆</span>
              <span className="font-semibold tracking-tight">
                vasp<span className="text-muted">·</span>attribution
              </span>
            </Link>
            <nav className="flex items-center gap-4 text-xs text-muted">
              <Link href="/" className="hover:text-text">
                search
              </Link>
              <Link href="/cases" className="hover:text-text">
                cases
              </Link>
            </nav>
            <span className="ml-auto text-[11px] text-muted">
              SIH 26182 · law-enforcement crypto tracing
            </span>
          </div>
        </header>
        <main className="mx-auto max-w-[1400px] px-5 py-6">{children}</main>
      </body>
    </html>
  );
}
