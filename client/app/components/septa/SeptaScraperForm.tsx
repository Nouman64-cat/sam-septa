"use client";

import { useState, useCallback } from "react";
import { Card } from "../ui/Card";
import { Input } from "../ui/Input";
import { Button } from "../ui/Button";
import { StatusBadge } from "../ui/StatusBadge";
import { scrapeSepta } from "../../services/septaService";
import { stopJob } from "../../services/jobService";
import { getDownloadUrl } from "../../services/api";
import { useJobPoller } from "../../hooks/useJobPoller";
import { isValidDate } from "../../utils/dateUtils";
import { triggerDownload, extractFilename } from "../../utils/downloadUtils";
import type { ScraperState, JobStatusResponse } from "../../types";

// ── Component ─────────────────────────────────────────────────────────────────

const INITIAL_STATE: ScraperState = { status: "idle" };

export function SeptaScraperForm() {
  const [dateFilter, setDateFilter] = useState("");
  const [dateError, setDateError]   = useState<string | null>(null);
  const [state, setState]           = useState<ScraperState>(INITIAL_STATE);
  const [stopping, setStopping]     = useState(false);

  const isRunning  = state.status === "running";
  const isFinished =
    state.status === "done" ||
    state.status === "stopped" ||
    state.status === "error";

  // ── Job polling ────────────────────────────────────────────────────────────

  const handleStatusUpdate = useCallback((res: JobStatusResponse) => {
    setState((prev) => ({
      ...prev,
      status:   res.status,
      filename: res.filename ?? undefined,
      error:    res.error   ?? undefined,
    }));
    // Keep the Stop button in its loading state until the job actually
    // finishes — clearing it on every "running" poll would kill the spinner.
    if (res.status !== "running") {
      setStopping(false);
    }
  }, []);

  useJobPoller(state.jobId, { onStatusUpdate: handleStatusUpdate });

  // ── Handlers ──────────────────────────────────────────────────────────────

  function handleDateChange(e: React.ChangeEvent<HTMLInputElement>) {
    setDateFilter(e.target.value);
    setDateError(null);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    if (dateFilter && !isValidDate(dateFilter)) {
      setDateError("Please enter a valid date.");
      return;
    }

    setState({ status: "running" });

    try {
      const res = await scrapeSepta({
        date_filter: dateFilter || undefined,
      });

      if (res.success && res.job_id) {
        setState({ status: "running", jobId: res.job_id });
      } else {
        setState({ status: "error", error: res.error ?? "Failed to start scraping job." });
      }
    } catch (err: unknown) {
      setState({
        status: "error",
        error:  err instanceof Error ? err.message : "Network error — is the server running?",
      });
    }
  }

  async function handleStop() {
    if (!state.jobId) return;
    setStopping(true);
    try {
      await stopJob(state.jobId);
    } catch {
      setStopping(false);
    }
  }

  function handleDownload() {
    if (!state.filename) return;
    triggerDownload(
      getDownloadUrl(state.filename),
      extractFilename(state.filename),
    );
  }

  function handleReset() {
    setState(INITIAL_STATE);
    setStopping(false);
  }

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <Card>
      {/* Header */}
      <div className="flex items-start justify-between mb-6 gap-4">
        <div>
          <h2 className="text-xl font-bold text-gray-900">SEPTA Scraper</h2>
          <p className="text-sm text-gray-500 mt-0.5">
            Collects open procurement quotes from the SEPTA eProcurement portal.
          </p>
        </div>
        <StatusBadge status={state.status} />
      </div>

      {/* Form — hidden while a job is active */}
      {!isRunning && !isFinished && (
        <form onSubmit={handleSubmit} className="space-y-5" noValidate>
          <div className="rounded-xl border border-gray-200 bg-gray-50 p-4 space-y-4">
            <p className="text-sm font-semibold text-gray-700">
              Date Filter{" "}
              <span className="font-normal text-gray-400">(optional)</span>
            </p>

            <Input
              id="septa-date-filter"
              label="Filter Date"
              type="date"
              value={dateFilter}
              onChange={handleDateChange}
              error={dateError ?? undefined}
              hint="Leave empty to scrape all currently open quotes"
            />

            <div className="flex items-center gap-2 rounded-lg border border-emerald-100 bg-emerald-50 px-3 py-2 text-xs text-emerald-700">
              <span className="font-semibold whitespace-nowrap">Active mode:</span>
              <span className="font-mono">
                {dateFilter
                  ? `Filter by date: ${dateFilter}`
                  : "No filter — all open quotes"}
              </span>
            </div>
          </div>

          {/* Credential notice */}
          <div className="rounded-xl border border-amber-100 bg-amber-50 px-4 py-3 text-xs text-amber-700">
            <span className="font-semibold">Credentials:</span> Uses the SEPTA
            username &amp; password from the server&apos;s{" "}
            <code className="font-mono">.env</code> file.
          </div>

          <Button type="submit" className="w-full">
            Start Scraping
          </Button>
        </form>
      )}

      {/* Running state — progress card with Stop button */}
      {isRunning && (
        <div className="space-y-4">
          <div className="rounded-xl border border-blue-200 bg-blue-50 p-4 space-y-3">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-blue-900">
                  Scraping in progress…
                </p>
                <p className="text-xs text-blue-700 mt-0.5">
                  A headless browser is logged into SEPTA and collecting quotes.
                  This can take a few minutes.
                </p>
              </div>
              <Button
                variant="danger"
                loading={stopping}
                onClick={handleStop}
                className="shrink-0"
              >
                {stopping ? "Stopping…" : "Stop"}
              </Button>
            </div>

            {state.jobId && (
              <p className="text-xs text-blue-600 font-mono">
                Job: {state.jobId}
              </p>
            )}
          </div>

          <div className="rounded-xl border border-amber-100 bg-amber-50 px-4 py-3 text-xs text-amber-700">
            <span className="font-semibold">Tip:</span> Clicking{" "}
            <strong>Stop</strong> saves all quotes collected so far — nothing
            is lost.
          </div>
        </div>
      )}

      {/* Success / stopped panel */}
      {(state.status === "done" || state.status === "stopped") && (
        <div className="rounded-xl border border-green-200 bg-green-50 p-4">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div className="min-w-0">
              <p className="text-sm font-semibold text-green-800">
                {state.status === "stopped"
                  ? "Scraping stopped — partial data saved!"
                  : "Scraping complete!"}
              </p>
              {state.filename && (
                <p className="text-xs text-green-700 mt-0.5 font-mono truncate">
                  {extractFilename(state.filename)}
                </p>
              )}
            </div>
            <div className="flex items-center gap-2 shrink-0">
              {state.filename && (
                <Button variant="secondary" onClick={handleDownload}>
                  Download
                </Button>
              )}
              <Button variant="ghost" onClick={handleReset}>
                New Scrape
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Error panel */}
      {state.status === "error" && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4">
          <p className="text-sm font-semibold text-red-800">Scraping failed</p>
          <p className="mt-1 text-xs text-red-700 font-mono break-all">
            {state.error}
          </p>
          <button
            onClick={handleReset}
            className="mt-3 text-xs text-red-600 underline hover:no-underline"
          >
            Try again
          </button>
        </div>
      )}
    </Card>
  );
}
