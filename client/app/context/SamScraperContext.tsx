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

interface SamScraperContextValue {
  // Scraper job state (status, jobId, recordCount, error)
  state:    ScraperState;
  setState: Dispatch<SetStateAction<ScraperState>>;
  // Date inputs
  dateFrom:    string;
  setDateFrom: Dispatch<SetStateAction<string>>;
  dateTo:      string;
  setDateTo:   Dispatch<SetStateAction<string>>;
  // NAICS codes
  naicsCodes:    string[];
  setNaicsCodes: Dispatch<SetStateAction<string[]>>;
  // Award Notice filter
  awardNotice:    boolean;
  setAwardNotice: Dispatch<SetStateAction<boolean>>;
  // Reset everything back to idle
  reset: () => void;
}

// ── Context ───────────────────────────────────────────────────────────────────

const SamScraperContext = createContext<SamScraperContextValue | null>(null);

const INITIAL: ScraperState = { status: "idle" };

// ── Provider ──────────────────────────────────────────────────────────────────

export function SamScraperProvider({ children }: { children: ReactNode }) {
  const [state,       setState]       = useState<ScraperState>(INITIAL);
  const [dateFrom,    setDateFrom]    = useState("");
  const [dateTo,      setDateTo]      = useState("");
  const [naicsCodes,  setNaicsCodes]  = useState<string[]>([]);
  const [awardNotice, setAwardNotice] = useState(false);

  const reset = useCallback(() => {
    setState(INITIAL);
    setDateFrom("");
    setDateTo("");
    setNaicsCodes([]);
    setAwardNotice(false);
  }, []);

  return (
    <SamScraperContext.Provider
      value={{ state, setState, dateFrom, setDateFrom, dateTo, setDateTo, naicsCodes, setNaicsCodes, awardNotice, setAwardNotice, reset }}
    >
      {children}
    </SamScraperContext.Provider>
  );
}

// ── Hook ──────────────────────────────────────────────────────────────────────

export function useSamScraper(): SamScraperContextValue {
  const ctx = useContext(SamScraperContext);
  if (!ctx) throw new Error("useSamScraper must be used within SamScraperProvider");
  return ctx;
}
