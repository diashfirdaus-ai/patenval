import type { Metadata } from "next";
import "./globals.css";
import { AppStateProvider } from "@/lib/i18n";
import { AppShell } from "@/components/layout/AppShell";

export const metadata: Metadata = {
  title: "TechVal AI — Scientific Technology Assessment & WIPO Valuation",
  description:
    "Four-output scientific technology assessment, commercialization readiness, WIPO deterministic IDR economic valuation, and evidence completeness platform.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased">
        <AppStateProvider>
          <AppShell>{children}</AppShell>
        </AppStateProvider>
      </body>
    </html>
  );
}
