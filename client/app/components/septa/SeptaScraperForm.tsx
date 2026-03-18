"use client";

import { useState, useCallback } from "react";
import { Input } from "../ui/Input";
import { Button } from "../ui/Button";
import { StatusBadge } from "../ui/StatusBadge";
import { scrapeSepta } from "../../services/septaService";
import { stopJob } from "../../services/jobService";
import { exportSepta } from "../../services/exportService";
import { useJobPoller } from "../../hooks/useJobPoller";
import { useToast } from "../../context/ToastContext";
import { isValidDate } from "../../utils/dateUtils";
import type { ScraperState, JobStatusResponse } from "../../types";

// ── Component ─────────────────────────────────────────────────────────────────

const INITIAL: ScraperState = { status: "idle" };

export function SeptaScraperForm() {
  const [dateFilter, setDateFilter] = useState("");
  const [dateError, setDateError]   = useState<string | null>(null);
  const [state, setState]           = useState<ScraperState>(INITIAL);
  const [stopping, setStopping]     = useState(false);

  const { toast } = useToast();

  const isRunning  = state.status === "running";
  const isFinished = ["done", "stopped", "error"].includes(state.status);

  // ── Job polling ────────────────────────────────────────────────────────────

  const handleStatusUpdate = useCallback(
    (res: JobStatusResponse) => {
      setState((prev) => ({
        ...prev,
        status:      res.status,
        recordCount: res.record_count,
        error:       res.error ?? undefined,
      }));
      if (res.status !== "running") {
        setStopping(false);
        if (res.status === "done") {
          toast("success", "SEPTA scraping complete!", `${res.record_count} quotes saved to database`);
        } else if (res.status === "stopped") {
          toast("warning", "Scraping stopped", `${res.record_count} quotes saved`);
        } else if (res.status === "error") {
          toast("error", "SEPTA scraping failed", res.error?.slice(0, 100));
        }
      }
    },
    [toast],
  );

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
        const modeDesc = dateFilter ? `Filtering by date: ${dateFilter}` : "All open quotes";
        toast("info", "SEPTA scraping started", modeDesc);
      } else {
        setState({ status: "error", error: res.error ?? "Failed to start job." });
        toast("error", "Failed to start scraping", res.error);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Network error — is the server running?";
      setState({ status: "error", error: msg });
      toast("error", "Network error", msg.slice(0, 100));
    }
  }

  async function handleStop() {
    if (!state.jobId) return;
    setStopping(true);
    try { await stopJob(state.jobId); }
    catch { setStopping(false); }
  }

  function handleExport() {
    exportSepta(state.jobId);
    toast("info", "Preparing download", "Your Excel file will begin downloading shortly");
  }

  function handleReset() {
    setState(INITIAL);
    setStopping(false);
    setDateFilter("");
    setDateError(null);
  }

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">

      {/* Emerald accent stripe */}
      <div className="h-1 bg-emerald-600" />

      {/* Card header */}
      <div className="px-6 pt-5 pb-4 flex items-start justify-between gap-3 border-b border-slate-100">
        <div>
          <h2 className="text-base font-bold text-slate-900">SEPTA Scraper</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Procurement quotes — results saved to database
          </p>
        </div>
        <StatusBadge status={state.status} />
      </div>

      {/* Content */}
      <div className="p-6">

        {/* ── Idle: form ── */}
        {!isRunning && !isFinished && (
          <form onSubmit={handleSubmit} className="space-y-5" noValidate>
            <div className="space-y-3">
              <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-widest">
                Date Filter — <span className="font-normal normal-case">optional</span>
              </p>

              <Input
                id="septa-date-filter"
                label="Filter Date"
                type="date"
                value={dateFilter}
                onChange={handleDateChange}
                error={dateError ?? undefined}
                hint="Leave empty to scrape all open quotes"
              />

              {/* Active mode chip */}
              <div className="flex items-center gap-2 text-xs text-slate-500">
                <span>Mode:</span>
                <span className="inline-flex items-center rounded-full bg-emerald-50 text-emerald-700 border border-emerald-100 px-2.5 py-0.5 font-medium text-xs">
                  {dateFilter ? `Filter by date: ${dateFilter}` : "No filter — all open quotes"}
                </span>
              </div>
            </div>

            {/* Credentials note */}
            <div className="flex items-start gap-2 rounded-lg bg-slate-50 border border-slate-100 px-3 py-2.5 text-xs text-slate-500">
              <span aria-hidden className="shrink-0 mt-px">🔑</span>
              <span>
                Uses the SEPTA credentials from the server&apos;s{" "}
                <code className="font-mono text-slate-600">.env</code> file.
              </span>
            </div>

            <Button type="submit" className="w-full" variant="primary">
              Start Scraping SEPTA
            </Button>
          </form>
        )}

        {/* ── Running ── */}
        {isRunning && (
          <div className="space-y-5">
            <div className="space-y-3">
              <div className="flex items-center justify-between gap-2">
                <p className="text-sm font-medium text-slate-700">
                  Collecting quotes…
                </p>
                <span className="text-xl font-bold font-mono text-slate-900 tabular-nums leading-none">
                  {state.recordCount ?? 0}
                </span>
              </div>

              <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
                <div className="h-full bg-emerald-500 animate-pulse rounded-full w-full" />
              </div>

              <div className="flex items-center justify-between">
                {state.jobId
                  ? <p className="text-xs text-slate-400 font-mono truncate">{state.jobId}</p>
                  : <span />}
                <p className="text-xs text-slate-400 shrink-0">quotes saved</p>
              </div>
            </div>

            <div className="flex items-center justify-between gap-3 pt-1 border-t border-slate-100">
              <p className="text-xs text-slate-400">Stopping saves all collected quotes.</p>
              <Button variant="danger" loading={stopping} onClick={handleStop} className="shrink-0">
                {stopping ? "Stopping…" : "Stop"}
              </Button>
            </div>
          </div>
        )}

        {/* ── Done / Stopped ── */}
        {(state.status === "done" || state.status === "stopped") && (
          <div className="space-y-4">
            <div className="flex items-start gap-3 rounded-xl bg-emerald-50 border border-emerald-100 px-4 py-3.5">
              <span className="text-emerald-600 font-bold text-base leading-5 mt-px shrink-0">✓</span>
              <div>
                <p className="text-sm font-semibold text-emerald-800">
                  {state.status === "stopped" ? "Stopped — partial data saved" : "Scraping complete!"}
                </p>
                <p className="text-xs text-emerald-700 mt-0.5">
                  <span className="font-mono font-bold">{state.recordCount ?? 0}</span>{" "}
                  quotes saved to database
                </p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <Button variant="secondary" onClick={handleExport}>
                ↓ Export to Excel
              </Button>
              <Button variant="ghost" onClick={handleReset}>
                + New Scrape
              </Button>
            </div>
          </div>
        )}

        {/* ── Error ── */}
        {state.status === "error" && (
          <div className="space-y-4">
            <div className="rounded-xl bg-red-50 border border-red-100 px-4 py-3.5">
              <p className="text-sm font-semibold text-red-800">Scraping failed</p>
              <p className="mt-1.5 text-xs text-red-600 font-mono break-all leading-relaxed">
                {state.error}
              </p>
            </div>
            <Button variant="ghost" onClick={handleReset} className="w-full">
              Try Again
            </Button>
          </div>
        )}

      </div>
    </div>
  );
}
