"use client";

import { useState } from "react";
import { SamScraperForm } from "./components/sam/SamScraperForm";
import { SeptaScraperForm } from "./components/septa/SeptaScraperForm";

// ── Tab config ────────────────────────────────────────────────────────────────

type TabId = "sam" | "septa";

interface Tab {
  id: TabId;
  label: string;
  sublabel: string;
  activeClasses: string;
}

const TABS: Tab[] = [
  {
    id: "sam",
    label: "SAM.gov",
    sublabel: "Government bids",
    activeClasses: "bg-blue-600 text-white shadow-md",
  },
  {
    id: "septa",
    label: "SEPTA",
    sublabel: "Procurement quotes",
    activeClasses: "bg-emerald-600 text-white shadow-md",
  },
];

// ── Page ──────────────────────────────────────────────────────────────────────

export default function Home() {
  const [activeTab, setActiveTab] = useState<TabId>("sam");

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      {/* Top bar */}
      <header className="sticky top-0 z-10 bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-2xl mx-auto px-4 py-4 flex items-center gap-3">
          <div className="flex items-center justify-center h-9 w-9 rounded-xl bg-blue-600 text-white font-bold text-base select-none">
            SG
          </div>
          <div>
            <h1 className="text-base font-bold text-gray-900 leading-tight">
              SAM &amp; SEPTA Bid Scraper
            </h1>
            <p className="text-xs text-gray-400">
              Automated government procurement data collector
            </p>
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="max-w-2xl mx-auto px-4 py-8 space-y-5">
        {/* Tab switcher */}
        <nav
          aria-label="Scraper selector"
          className="flex gap-1.5 p-1.5 bg-white rounded-2xl border border-gray-200 shadow-sm"
        >
          {TABS.map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                role="tab"
                aria-selected={isActive}
                onClick={() => setActiveTab(tab.id)}
                className={[
                  "flex-1 flex flex-col items-center gap-0.5 py-3 px-4 rounded-xl",
                  "text-sm font-medium transition-all duration-150",
                  isActive
                    ? tab.activeClasses
                    : "text-gray-500 hover:bg-gray-50 hover:text-gray-700",
                ].join(" ")}
              >
                <span className="font-bold tracking-tight">{tab.label}</span>
                <span
                  className={`text-xs font-normal ${
                    isActive ? "opacity-75" : "text-gray-400"
                  }`}
                >
                  {tab.sublabel}
                </span>
              </button>
            );
          })}
        </nav>

        {/* Active scraper form */}
        {activeTab === "sam" && <SamScraperForm />}
        {activeTab === "septa" && <SeptaScraperForm />}

        {/* Footer */}
        <p className="text-center text-xs text-gray-400 pb-4">
          Scraping runs on the server — a browser window opens automatically.
          Large scrapes may take several minutes.
        </p>
      </main>
    </div>
  );
}
