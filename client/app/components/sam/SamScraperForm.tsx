"use client";

import { useState, useCallback } from "react";
import { Card } from "../ui/Card";
import { Input } from "../ui/Input";
import { Button } from "../ui/Button";
import { StatusBadge } from "../ui/StatusBadge";
import { scrapeSam } from "../../services/samService";
import { stopJob } from "../../services/jobService";
import { getDownloadUrl } from "../../services/api";
import { useJobPoller } from "../../hooks/useJobPoller";
import {
  validateDateRange,
  describeDateScenario,
} from "../../utils/dateUtils";
import { triggerDownload, extractFilename } from "../../utils/downloadUtils";
import type { ScraperState, JobStatusResponse } from "../../types";

// ── Scenario reference grid ───────────────────────────────────────────────────

const SCENARIOS = [
  { label: "Both dates", desc: "From → To" },
  { label: "From only",  desc: "From → Today" },
  { label: "Same date",  desc: "Exact day" },
  { label: "No dates",   desc: "All bids" },
] as const;

// ── Component ─────────────────────────────────────────────────────────────────

const INITIAL_STATE: ScraperState = { status: "idle" };

export function SamScraperForm() {
  const [dateFrom, setDateFrom]     = useState("");
  const [dateTo, setDateTo]         = useState("");
  const [rangeError, setRangeError] = useState<string | null>(null);
  const [state, setState]           = useState<ScraperState>(INITIAL_STATE);
  const [stopping, setStopping]     = useState(false);

  const isRunning = state.status === "running";
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

  function handleFromChange(e: React.ChangeEvent<HTMLInputElement>) {
    setDateFrom(e.target.value);
    setRangeError(null);
  }

  function handleToChange(e: React.ChangeEvent<HTMLInputElement>) {
    setDateTo(e.target.value);
    setRangeError(null);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    const err = validateDateRange(dateFrom, dateTo);
    if (err) { setRangeError(err); return; }

    setState({ status: "running" });

    try {
      const res = await scrapeSam({
        date_filter: dateFrom || undefined,
        date_to:     dateTo   || undefined,
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
          <h2 className="text-xl font-bold text-gray-900">SAM.gov Scraper</h2>
          <p className="text-sm text-gray-500 mt-0.5">
            Collects government bid notices from SAM.gov with optional date
            range filtering.
          </p>
        </div>
        <StatusBadge status={state.status} />
      </div>

      {/* Form — hidden while a job is active */}
      {!isRunning && !isFinished && (
        <form onSubmit={handleSubmit} className="space-y-5" noValidate>
          {/* Date range inputs */}
          <div className="rounded-xl border border-gray-200 bg-gray-50 p-4 space-y-4">
            <p className="text-sm font-semibold text-gray-700">
              Date Range Filter{" "}
              <span className="font-normal text-gray-400">(optional)</span>
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input
                id="sam-date-from"
                label="From Date"
                type="date"
                value={dateFrom}
                onChange={handleFromChange}
                hint="Start of the date range"
              />
              <Input
                id="sam-date-to"
                label="To Date"
                type="date"
                value={dateTo}
                onChange={handleToChange}
                hint="Defaults to today when left empty"
              />
            </div>

            {rangeError && (
              <p className="text-sm text-red-600 flex items-center gap-1.5">
                <span aria-hidden>&#9888;</span>
                {rangeError}
              </p>
            )}

            <div className="flex items-center gap-2 rounded-lg border border-blue-100 bg-blue-50 px-3 py-2 text-xs text-blue-700">
              <span className="font-semibold whitespace-nowrap">Active mode:</span>
              <span className="font-mono">
                {describeDateScenario(dateFrom, dateTo)}
              </span>
            </div>
          </div>

          {/* Scenario reference */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {SCENARIOS.map(({ label, desc }) => (
              <div
                key={label}
                className="rounded-lg border border-gray-100 bg-gray-50 px-3 py-2 text-center"
              >
                <div className="text-xs font-semibold text-gray-600">{label}</div>
                <div className="text-xs text-gray-400 mt-0.5">{desc}</div>
              </div>
            ))}
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
                  A Chrome window is open on the server collecting bids.
                  This can take several minutes.
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
            <strong>Stop</strong> saves all data scraped so far — nothing is
            lost.
          </div>
        </div>
      )}

      {/* Success / stopped panel */}
      {(state.status === "done" || state.status === "stopped") && (
        <div className="space-y-3">
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
