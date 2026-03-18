"use client";

import { SamScraperForm } from "./components/sam/SamScraperForm";
import { SeptaScraperForm } from "./components/septa/SeptaScraperForm";

export default function Home() {
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">

      {/* ── Header ──────────────────────────────────────────────────────────── */}
      <header className="bg-slate-900 border-b border-slate-800 shrink-0">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center gap-4">
          {/* Logo mark */}
          <div className="flex items-center justify-center h-10 w-10 rounded-xl bg-blue-500 shrink-0 select-none">
            <span className="text-white font-bold text-sm">SG</span>
          </div>

          {/* Title */}
          <div className="flex-1 min-w-0">
            <h1 className="text-[15px] font-bold text-white leading-tight">
              SAM &amp; SEPTA Bid Scraper
            </h1>
            <p className="text-xs text-slate-400 mt-px">
              Automated government procurement data collector
            </p>
          </div>

          {/* Status pill */}
          <div className="hidden sm:flex items-center gap-2 rounded-full bg-slate-800 border border-slate-700 px-3 py-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 shrink-0" />
            <span className="text-xs text-slate-400 font-medium">Server connected</span>
          </div>
        </div>
      </header>

      {/* ── Main ────────────────────────────────────────────────────────────── */}
      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-8">
        {/* Section label */}
        <div className="mb-6">
          <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wider">
            Scrapers
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Run independently — both can scrape simultaneously
          </p>
        </div>

        {/* Side-by-side scraper cards */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
          <SamScraperForm />
          <SeptaScraperForm />
        </div>
      </main>

      {/* ── Footer ──────────────────────────────────────────────────────────── */}
      <footer className="shrink-0 border-t border-slate-200 bg-white">
        <div className="max-w-6xl mx-auto px-6 py-3">
          <p className="text-xs text-slate-400 text-center">
            Scraping runs on the server — a browser window opens automatically.
            Large scrapes may take several minutes.
          </p>
        </div>
      </footer>

    </div>
  );
}
