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

interface NaicsScraperContextValue {
  state:    ScraperState;
  setState: Dispatch<SetStateAction<ScraperState>>;
  reset:    () => void;
}

const NaicsScraperContext = createContext<NaicsScraperContextValue | null>(null);

const INITIAL: ScraperState = { status: "idle" };

export function NaicsScraperProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<ScraperState>(INITIAL);
  const reset = useCallback(() => setState(INITIAL), []);

  return (
    <NaicsScraperContext.Provider value={{ state, setState, reset }}>
      {children}
    </NaicsScraperContext.Provider>
  );
}

export function useNaicsScraper(): NaicsScraperContextValue {
  const ctx = useContext(NaicsScraperContext);
  if (!ctx) throw new Error("useNaicsScraper must be used within NaicsScraperProvider");
  return ctx;
}
