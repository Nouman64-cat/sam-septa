"use client";

import {
  createContext,
  useContext,
  useState,
  useCallback,
  type ReactNode,
  type Dispatch,
  type SetStateAction,
} from "react";
import type { ScraperState } from "../types";

// ── Types ─────────────────────────────────────────────────────────────────────

interface SeptaScraperContextValue {
  // Scraper job state (status, jobId, recordCount, error)
  state:    ScraperState;
  setState: Dispatch<SetStateAction<ScraperState>>;
  // Date filter input
  dateFilter:    string;
  setDateFilter: Dispatch<SetStateAction<string>>;
  // Reset everything back to idle
  reset: () => void;
}

// ── Context ───────────────────────────────────────────────────────────────────

const SeptaScraperContext = createContext<SeptaScraperContextValue | null>(null);

const INITIAL: ScraperState = { status: "idle" };

// ── Provider ──────────────────────────────────────────────────────────────────

export function SeptaScraperProvider({ children }: { children: ReactNode }) {
  const [state,      setState]      = useState<ScraperState>(INITIAL);
  const [dateFilter, setDateFilter] = useState("");

  const reset = useCallback(() => {
    setState(INITIAL);
    setDateFilter("");
  }, []);

  return (
    <SeptaScraperContext.Provider
      value={{ state, setState, dateFilter, setDateFilter, reset }}
    >
      {children}
    </SeptaScraperContext.Provider>
  );
}

// ── Hook ──────────────────────────────────────────────────────────────────────

export function useSeptaScraper(): SeptaScraperContextValue {
  const ctx = useContext(SeptaScraperContext);
  if (!ctx) throw new Error("useSeptaScraper must be used within SeptaScraperProvider");
  return ctx;
}
