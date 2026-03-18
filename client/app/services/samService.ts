import { post } from "./api";
import type { SamScrapeRequest, ScrapeResponse } from "../types";

/**
 * Trigger the SAM.gov scraper with an optional date range.
 *
 * Scenarios handled by the backend:
 *  - Both `date_filter` + `date_to`  → range [from, to]
 *  - Only `date_filter`              → range [from, today]
 *  - `date_filter` === `date_to`     → exact single-day match
 *  - Neither provided                → no date filter (all available bids)
 */
export async function scrapeSam(
  params: SamScrapeRequest,
): Promise<ScrapeResponse> {
  return post<SamScrapeRequest, ScrapeResponse>("/scrape_sam", params);
}
