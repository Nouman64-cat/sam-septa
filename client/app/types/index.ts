// ── API request shapes ─────────────────────────────────────────────────────────

export interface SamScrapeRequest {
  /** Start of date range – YYYY-MM-DD. Omit for no filter. */
  date_filter?: string;
  /** End of date range – YYYY-MM-DD. Omit to default to today. */
  date_to?: string;
}

export interface SeptaScrapeRequest {
  /** Filter date – YYYY-MM-DD. Omit to scrape all open quotes. */
  date_filter?: string;
}

// ── API response shapes ────────────────────────────────────────────────────────

export interface ScrapeResponse {
  success: boolean;
  /** Relative path to the generated output file (CSV / XLSX). */
  filename?: string;
  /** Human-readable error message when success === false. */
  error?: string;
}

// ── UI state ───────────────────────────────────────────────────────────────────

export type ScraperStatus = "idle" | "running" | "success" | "error";

export interface ScraperState {
  status: ScraperStatus;
  filename?: string;
  error?: string;
}
