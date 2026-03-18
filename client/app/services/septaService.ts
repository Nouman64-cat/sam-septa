import { post } from "./api";
import type { SeptaScrapeRequest, ScrapeResponse } from "../types";

/**
 * Trigger the SEPTA portal scraper with an optional date filter.
 * Pass an empty object (or omit `date_filter`) to scrape all open quotes.
 */
export async function scrapeSepta(
  params: SeptaScrapeRequest,
): Promise<ScrapeResponse> {
  return post<SeptaScrapeRequest, ScrapeResponse>("/scrape_septa", params);
}
