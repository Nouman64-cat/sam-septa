// ── API request shapes ─────────────────────────────────────────────────────────

export interface SamScrapeRequest {
  date_filter?: string;     // from-date YYYY-MM-DD
  date_to?: string;         // to-date   YYYY-MM-DD
  naics_codes?: string[];   // list of 6-digit NAICS codes
}

export interface SeptaScrapeRequest {
  date_filter?: string;   // YYYY-MM-DD
}

// ── Job API shapes ─────────────────────────────────────────────────────────────

export interface JobStartResponse {
  success: boolean;
  job_id?: string;
  error?: string;
}

export type JobStatus = "running" | "done" | "stopped" | "error";

export interface JobStatusResponse {
  status: JobStatus;
  /** Live count of records saved so far (increments per bid for SAM). */
  record_count: number;
  error?: string | null;
}

export interface StopResponse {
  success: boolean;
  message?: string;
  error?: string;
}

// ── Scrape job history ────────────────────────────────────────────────────────

export interface ScrapeJobRecord {
  job_id:        string;
  scraper:       "sam" | "septa";
  status:        JobStatus;
  date_from:     string | null;
  date_to:       string | null;
  started_at:    string | null;
  finished_at:   string | null;
  record_count:  number;
  error_message: string | null;
}

// ── NAICS ─────────────────────────────────────────────────────────────────────

export interface NaicsCodeItem {
  code:  string;
  title: string;
}

export interface NaicsListResponse {
  total:   number;
  page:    number;
  limit:   number;
  results: NaicsCodeItem[];
}

// ── UI state ───────────────────────────────────────────────────────────────────

export type ScraperStatus = "idle" | JobStatus;

export interface ScraperState {
  status:       ScraperStatus;
  jobId?:       string;
  recordCount?: number;
  error?:       string;
}
