"use client";

import { useState, useCallback } from "react";
import { Card } from "../ui/Card";
import { Input } from "../ui/Input";
import { Button } from "../ui/Button";
import { StatusBadge } from "../ui/StatusBadge";
import { scrapeSepta } from "../../services/septaService";
import { stopJob } from "../../services/jobService";
import { exportSepta } from "../../services/exportService";
import { useJobPoller } from "../../hooks/useJobPoller";
import { isValidDate } from "../../utils/dateUtils";
import type { ScraperState, JobStatusResponse } from "../../types";

// ── Component ─────────────────────────────────────────────────────────────────

const INITIAL: ScraperState = { status: "idle" };

export function SeptaScraperForm() {
  const [dateFilter, setDateFilter] = useState("");
  const [dateError, setDateError]   = useState<string | null>(null);
  const [state, setState]           = useState<ScraperState>(INITIAL);
  const [stopping, setStopping]     = useState(false);

  const isRunning  = state.status === "running";
  const isFinished = ["done", "stopped", "error"].includes(state.status);

  // ── Job polling ────────────────────────────────────────────────────────────

  const handleStatusUpdate = useCallback((res: JobStatusResponse) => {
    setState((prev) => ({
      ...prev,
      status:      res.status,
      recordCount: res.record_count,
      error:       res.error ?? undefined,
    }));
    if (res.status !== "running") setStopping(false);
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
      const res = await scrapeSepta({ date_filter: dateFilter || undefined });
      if (res.success && res.job_id) {
        setState({ status: "running", jobId: res.job_id, recordCount: 0 });
      } else {
        setState({ status: "error", error: res.error ?? "Failed to start job." });
      }
    } catch (err: unknown) {
      setState({
        status: "error",
        error: err instanceof Error ? err.message : "Network error — is the server running?",
      });
    }
  }

  async function handleStop() {
    if (!state.jobId) return;
    setStopping(true);
    try { await stopJob(state.jobId); }
    catch { setStopping(false); }
  }

  function handleExport() { exportSepta(state.jobId); }
  function handleReset()  { setState(INITIAL); setStopping(false); }

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <Card>
      {/* Header */}
      <div className="flex items-start justify-between mb-6 gap-4">
        <div>
          <h2 className="text-xl font-bold text-gray-900">SEPTA Scraper</h2>
          <p className="text-sm text-gray-500 mt-0.5">
            Collects open procurement quotes — results saved directly to the database.
          </p>
        </div>
        <StatusBadge status={state.status} />
      </div>

      {/* ── Form (visible only when idle) ── */}
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
                {dateFilter ? `Filter by date: ${dateFilter}` : "No filter — all open quotes"}
              </span>
            </div>
          </div>

          <div className="rounded-xl border border-amber-100 bg-amber-50 px-4 py-3 text-xs text-amber-700">
            <span className="font-semibold">Credentials:</span> Uses the SEPTA username &amp; password
            from the server&apos;s <code className="font-mono">.env</code> file.
          </div>

          <Button type="submit" className="w-full">Start Scraping</Button>
        </form>
      )}

      {/* ── Running state ── */}
      {isRunning && (
        <div className="space-y-4">
          <div className="rounded-xl border border-blue-200 bg-blue-50 p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-blue-900">Scraping in progress…</p>
                <p className="text-xs text-blue-700 mt-0.5">
                  A headless browser is logged into SEPTA collecting quotes.
                </p>
              </div>
              <Button variant="danger" loading={stopping} onClick={handleStop} className="shrink-0">
                {stopping ? "Stopping…" : "Stop"}
              </Button>
            </div>

            <div className="mt-3 flex items-center gap-3">
              <div className="flex-1 h-1.5 rounded-full bg-blue-200 overflow-hidden">
                <div className="h-full bg-blue-500 animate-pulse w-full" />
              </div>
              <span className="text-xs font-mono text-blue-700 whitespace-nowrap">
                {state.recordCount ?? 0} quotes collected
              </span>
            </div>

            {state.jobId && (
              <p className="text-xs text-blue-500 font-mono mt-2">Job: {state.jobId}</p>
            )}
          </div>

          <div className="rounded-xl border border-amber-100 bg-amber-50 px-4 py-3 text-xs text-amber-700">
            <span className="font-semibold">Tip:</span> Stopping saves all quotes collected so far.
          </div>
        </div>
      )}

      {/* ── Success / stopped ── */}
      {(state.status === "done" || state.status === "stopped") && (
        <div className="rounded-xl border border-green-200 bg-green-50 p-4">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-green-800">
                {state.status === "stopped" ? "Stopped — partial data saved to DB" : "Complete!"}
              </p>
              <p className="text-xs text-green-700 mt-0.5">
                <span className="font-semibold font-mono">{state.recordCount ?? 0}</span> quotes
                saved to the database
                {state.jobId && (
                  <span className="text-green-600"> · {state.jobId}</span>
                )}
              </p>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <Button variant="secondary" onClick={handleExport}>
                Export to Excel
              </Button>
              <Button variant="ghost" onClick={handleReset}>New Scrape</Button>
            </div>
          </div>
        </div>
      )}

      {/* ── Error ── */}
      {state.status === "error" && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4">
          <p className="text-sm font-semibold text-red-800">Scraping failed</p>
          <p className="mt-1 text-xs text-red-700 font-mono break-all">{state.error}</p>
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
