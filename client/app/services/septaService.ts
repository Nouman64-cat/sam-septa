import { post } from "./api";
import type { SeptaScrapeRequest, JobStartResponse } from "../types";

/**
 * Start a SEPTA portal scrape in a background job.
 * Returns a job_id immediately — use jobService to poll status or stop it.
 * Pass an empty object (or omit date_filter) to scrape all open quotes.
 */
export async function scrapeSepta(
  params: SeptaScrapeRequest,
): Promise<JobStartResponse> {
  return post<SeptaScrapeRequest, JobStartResponse>("/scrape_septa", params);
}
