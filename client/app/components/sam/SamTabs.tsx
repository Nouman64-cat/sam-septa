"use client";

import { useState } from "react";
import { SamScraperForm } from "./SamScraperForm";
import { EvalConfigPanel } from "./EvalConfigPanel";

const TABS = [
  { id: "scraper", label: "Scraper", icon: (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
    </svg>
  )},
  { id: "evaluator", label: "Evaluator Config", icon: (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
    </svg>
  )},
] as const;

type TabId = (typeof TABS)[number]["id"];

export function SamTabs() {
  const [active, setActive] = useState<TabId>("scraper");

  return (
    <div>
      {/* Tab bar */}
      <div className="flex gap-1.5 bg-slate-100 rounded-xl p-1.5 mb-0">
        {TABS.map((tab) => {
          const isActive = active === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActive(tab.id)}
              className={[
                "flex-1 flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-bold transition-all duration-150",
                isActive
                  ? "bg-blue-600 text-white shadow-md shadow-blue-200"
                  : "text-slate-500 hover:text-slate-800 hover:bg-white/70",
              ].join(" ")}
            >
              <span className={isActive ? "text-blue-100" : "text-slate-400"}>{tab.icon}</span>
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab content */}
      <div className="mt-0">
        {active === "scraper" && <SamScraperForm />}
        {active === "evaluator" && <EvalConfigPanel defaultOpen />}
      </div>
    </div>
  );
}
