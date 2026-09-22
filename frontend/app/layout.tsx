import type { Metadata } from "next";
import { AuthGate } from "@/components/AuthGate";
import { CommandPalette } from "@/components/CommandPalette";
import { HeaderBar } from "@/components/HeaderBar";
import { MotionScene } from "@/components/MotionScene";
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
    <html
      lang="en"
      className="font-sans"
    >
      <body className="min-h-screen font-sans text-sm text-body">
        <MotionScene>
        <a href="#main-content" className="skip-link">Skip to content</a>
        <HeaderBar />

        <main id="main-content" tabIndex={-1} className="workspace-main">
          <AuthGate>{children}</AuthGate>
        </main>

        <CommandPalette />
        </MotionScene>
      </body>
    </html>
  );
}
