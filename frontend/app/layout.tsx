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
        <header className="sticky top-0 z-20 border-b border-border bg-bg/85 backdrop-blur">
          <div className="mx-auto flex max-w-[1400px] items-center gap-6 px-5 py-3">
            <Link href="/" className="group flex items-center gap-2.5">
              <span className="grid h-6 w-6 place-items-center rounded-sm border border-accent/50 text-accent">
                ◆
              </span>
              <span className="font-display text-[15px] font-semibold tracking-tight text-text">
                CHAIN<span className="text-accent">TRACE</span>
              </span>
            </Link>
            <nav className="flex items-center gap-1 text-[11px] uppercase tracking-widest text-muted">
              <Link
                href="/"
                className="rounded px-2 py-1 hover:bg-panel hover:text-text"
              >
                trace
              </Link>
              <Link
                href="/investigations"
                className="rounded px-2 py-1 hover:bg-panel hover:text-text"
              >
                investigations
              </Link>
              <Link
                href="/cases"
                className="rounded px-2 py-1 hover:bg-panel hover:text-text"
              >
                cases
              </Link>
            </nav>
            <span className="ml-auto flex items-center gap-2 text-[10px] uppercase tracking-widest text-muted">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-good" />
              SIH 26182 · crypto attribution
            </span>
          </div>
        </header>
        <main className="mx-auto max-w-[1400px] px-5 py-8">{children}</main>
      </body>
    </html>
  );
}
