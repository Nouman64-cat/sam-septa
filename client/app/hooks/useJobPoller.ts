"use client";

import { useEffect, useRef, useCallback } from "react";
import { getJobStatus } from "../services/jobService";
import type { JobStatus, JobStatusResponse } from "../types";

const TERMINAL_STATUSES = new Set<JobStatus>(["done", "stopped", "error"]);
const POLL_INTERVAL_MS = 3000;

export interface JobPollerOptions {
  /** Called each time a status response arrives. */
  onStatusUpdate: (response: JobStatusResponse) => void;
  /** Polling interval in ms. Defaults to 3000. */
  intervalMs?: number;
}

/**
 * useJobPoller — polls GET /status/{jobId} every `intervalMs` milliseconds.
 *
 * - Starts polling when `jobId` becomes a non-empty string.
 * - Stops automatically once the status reaches a terminal state
 *   ("done" | "stopped" | "error").
 * - Cleans up the interval on unmount or when `jobId` changes.
 *
 * Returns a `stopPolling` function for manual cancellation.
 */
export function useJobPoller(
  jobId: string | undefined,
  { onStatusUpdate, intervalMs = POLL_INTERVAL_MS }: JobPollerOptions,
) {
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const onStatusRef = useRef(onStatusUpdate);

  // Keep the callback ref fresh without re-starting the interval on every render
  useEffect(() => {
    onStatusRef.current = onStatusUpdate;
  });

  const stopPolling = useCallback(() => {
    if (timerRef.current !== null) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (!jobId) return;

    // Immediate first poll so UI updates without waiting the full interval
    const poll = async () => {
      try {
        const response = await getJobStatus(jobId);
        onStatusRef.current(response);
        if (TERMINAL_STATUSES.has(response.status)) {
          stopPolling();
        }
      } catch {
        // Network blip — keep polling; the scraper may still be running
      }
    };

    poll();
    timerRef.current = setInterval(poll, intervalMs);

    return stopPolling;
  }, [jobId, intervalMs, stopPolling]);

  return { stopPolling };
}
