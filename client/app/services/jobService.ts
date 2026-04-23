/**
 * Job management service.
 * Handles polling and stopping background scrape jobs on the server.
 */

import { post } from "./api";
import type { JobStatusResponse, StopResponse } from "../types";

const BASE_URL =
  process.env.NEXT_PUBLIC_SERVER_URL?.replace(/\/$/, "") ??
  "http://127.0.0.1:8001";

/**
 * Fetch the current status of a background job.
 * Calls GET /status/{jobId}.
 */
export async function getJobStatus(jobId: string): Promise<JobStatusResponse> {
  const res = await fetch(`${BASE_URL}/status/${jobId}`);
  if (!res.ok) {
    throw new Error(`Status check failed: HTTP ${res.status}`);
  }
  return res.json() as Promise<JobStatusResponse>;
}

/**
 * Send a graceful stop signal to a running job.
 * The scraper will finish its current page and save partial data.
 * Calls POST /stop/{jobId}.
 */
export async function stopJob(jobId: string): Promise<StopResponse> {
  return post<Record<string, never>, StopResponse>(`/stop/${jobId}`, {});
}

/**
 * Fetch a live screenshot from a running SAM job.
 */
export async function getJobScreenshot(jobId: string): Promise<{ screenshot: string }> {
  const res = await fetch(`${BASE_URL}/sam/screenshot/${jobId}`);
  if (!res.ok) {
    throw new Error(`Screenshot fetch failed: HTTP ${res.status}`);
  }
  return res.json() as Promise<{ screenshot: string }>;
}
