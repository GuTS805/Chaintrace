import type { Metadata } from "next";
import Link from "next/link";
import { Poppins, DM_Sans, JetBrains_Mono } from "next/font/google";
import { AuthGate } from "@/components/AuthGate";
import { OfficerBadge } from "@/components/OfficerBadge";
import { CommandPalette } from "@/components/CommandPalette";
import { NavLinks } from "@/components/NavLinks";
import { Mark } from "@/components/Mark";
import { Kbd } from "@/components/ui";
import "./globals.css";

const poppins = Poppins({
  subsets: ["latin"],
  weight: ["500", "600", "700"],
  variable: "--font-poppins",
  display: "swap",
});

const dmSans = DM_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "700"],
  variable: "--font-dm-sans",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-jetbrains-mono",
  display: "swap",
});

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
    <html
      lang="en"
      className={`${poppins.variable} ${dmSans.variable} ${jetbrainsMono.variable}`}
    >
      <body className="min-h-screen font-sans text-sm text-body">
        {/* ── Floating navbar ── */}
        <header className="sticky top-0 z-20 mx-4 mt-4 rounded-card bg-white shadow-nav">
          <div className="mx-auto flex h-16 max-w-[1200px] items-center gap-8 px-6">
            <Link href="/" className="group flex items-center gap-2.5">
              <Mark size={20} />
              <span className="font-display text-[14px] font-bold tracking-tight text-heading">
                CHAIN<span className="text-primary">TRACE</span>
              </span>
            </Link>

            <NavLinks />

            <div className="ml-auto hidden items-center gap-2 rounded-full bg-surface-lavender px-4 py-2 text-[12px] text-muted md:flex" style={{ width: 240 }}>
              <span>Search anywhere</span>
              <Kbd>⌘K</Kbd>
            </div>

            <OfficerBadge />
          </div>
        </header>

        <main className="relative z-10 mx-auto max-w-[1200px] px-8 py-12">
          <AuthGate>{children}</AuthGate>
        </main>

        <CommandPalette />
      </body>
    </html>
  );
}
