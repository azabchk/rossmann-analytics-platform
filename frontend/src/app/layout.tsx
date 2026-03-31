import type { Metadata } from "next";
import Link from "next/link";
import { DM_Sans, Space_Grotesk } from "next/font/google";
import type { ReactNode } from "react";

import PrimaryNav from "@/components/navigation/primary-nav";

import "./globals.css";

export const metadata: Metadata = {
  title: "Sales Forecasting Platform",
  description: "Thin presentation layer for the analytical platform",
};

const displayFont = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-display",
});

const bodyFont = DM_Sans({
  subsets: ["latin"],
  variable: "--font-body",
});

type RootLayoutProps = {
  children: ReactNode;
};

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="en">
      <body className={`${displayFont.variable} ${bodyFont.variable}`}>
        <div className="site-chrome">
          <div className="site-orbit site-orbit--amber" />
          <div className="site-orbit site-orbit--teal" />

          <header className="site-header">
            <div className="site-header__inner">
              <Link href="/" className="site-brand" aria-label="Sales Forecasting Platform home">
                <span className="site-brand__mark">SF</span>
                <span className="site-brand__copy">
                  <strong>Sales Forecasting Platform</strong>
                  <span>Retail analytics MVP</span>
                </span>
              </Link>

              <PrimaryNav />

              <div className="site-status">
                <span className="site-status__label">FastAPI-only data boundary</span>
              </div>
            </div>
          </header>

          <main className="site-main">{children}</main>

          <footer className="site-footer">
            <div className="site-footer__inner">
              <p>Headless modular monolith. Thin Next.js presentation layer. Demo-ready thesis MVP.</p>
              <Link href="/login">Open local demo access</Link>
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
