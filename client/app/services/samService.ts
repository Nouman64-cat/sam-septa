import { post } from "./api";
import type { SamScrapeRequest, JobStartResponse } from "../types";

/**
 * Start a SAM.gov scrape in a background job.
 * Returns a job_id immediately — use jobService to poll status or stop it.
 *
 * Date-range scenarios handled by the backend:
 *  - Both date_filter + date_to   → range [from, to]
 *  - Only date_filter             → range [from, today]
 *  - date_filter === date_to      → exact single-day match
 *  - Neither provided             → no date filter (all available bids)
 */
export async function scrapeSam(
  params: SamScrapeRequest,
): Promise<JobStartResponse> {
  return post<SamScrapeRequest, JobStartResponse>("/scrape_sam", params);
}
