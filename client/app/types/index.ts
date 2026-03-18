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

// ── Job API shapes ─────────────────────────────────────────────────────────────

/** Returned immediately when POST /scrape_* is called. */
export interface JobStartResponse {
  success: boolean;
  /** Present when success === true. Use to poll /status/{job_id}. */
  job_id?: string;
  error?: string;
}

/** Status string returned by GET /status/{job_id}. */
export type JobStatus = "running" | "done" | "stopped" | "error";

/** Shape of GET /status/{job_id} response body. */
export interface JobStatusResponse {
  status: JobStatus;
  /** Absolute server-side path to the output file once the job finishes. */
  filename?: string | null;
  error?: string | null;
}

/** Shape of POST /stop/{job_id} response body. */
export interface StopResponse {
  success: boolean;
  message?: string;
  error?: string;
}

// ── UI state ───────────────────────────────────────────────────────────────────

/** UI-facing status — extends JobStatus with the initial "idle" state. */
export type ScraperStatus = "idle" | JobStatus;

export interface ScraperState {
  status: ScraperStatus;
  /** Active job ID while running or after completion. */
  jobId?: string;
  filename?: string;
  error?: string;
}
