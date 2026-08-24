import type { Metadata } from "next";
import { Poppins, DM_Sans, JetBrains_Mono } from "next/font/google";
import { AuthGate } from "@/components/AuthGate";
import { CommandPalette } from "@/components/CommandPalette";
import { HeaderBar } from "@/components/HeaderBar";
import "./globals.css";
import { cn } from "@/lib/utils";

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
      className={cn(poppins.variable, dmSans.variable, jetbrainsMono.variable, "font-sans")}
    >
      <body className="min-h-screen font-sans text-sm text-body">
        <HeaderBar />

        <main className="relative z-10 mx-auto max-w-[1680px] px-6 py-12 sm:px-10">
          <AuthGate>{children}</AuthGate>
        </main>

        <CommandPalette />
      </body>
    </html>
  );
}
