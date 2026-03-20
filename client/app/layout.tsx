import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { ToastProvider } from "./context/ToastContext";
import { ToastContainer } from "./components/ui/Toast";
import { SamScraperProvider } from "./context/SamScraperContext";
import { SeptaScraperProvider } from "./context/SeptaScraperContext";
import { NaicsScraperProvider } from "./context/NaicsScraperContext";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "SAM & SEPTA Bid Scraper",
  description: "Automated government procurement data collector for SAM.gov and SEPTA",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="scroll-smooth">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <ToastProvider>
          <SamScraperProvider>
            <SeptaScraperProvider>
            <NaicsScraperProvider>
              {children}
              <ToastContainer />
            </NaicsScraperProvider>
            </SeptaScraperProvider>
          </SamScraperProvider>
        </ToastProvider>
      </body>
    </html>
  );
}
