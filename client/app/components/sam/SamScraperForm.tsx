"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { Input } from "../ui/Input";
import { Button } from "../ui/Button";
import { StatusBadge } from "../ui/StatusBadge";
import { scrapeSam } from "../../services/samService";
import { stopJob } from "../../services/jobService";
import { exportSam } from "../../services/exportService";
import { searchNaics } from "../../services/naicsService";
import { useJobPoller } from "../../hooks/useJobPoller";
import { useToast } from "../../context/ToastContext";
import { useSamScraper } from "../../context/SamScraperContext";
import { validateDateRange, describeDateScenario } from "../../utils/dateUtils";
import type { JobStatusResponse, NaicsCodeItem } from "../../types";

// ── Component ─────────────────────────────────────────────────────────────────

export function SamScraperForm() {
  // Persistent state from context (survives page navigation)
  const {
    state, setState,
    dateFrom, setDateFrom,
    dateTo, setDateTo,
    naicsCodes, setNaicsCodes,
    reset,
  } = useSamScraper();

  // Transient UI-only state (no need to persist)
  const [rangeError, setRangeError] = useState<string | null>(null);
  const [stopping,   setStopping]   = useState(false);

  // NAICS search state
  const [naicsQuery,   setNaicsQuery]   = useState("");
  const [naicsResults, setNaicsResults] = useState<NaicsCodeItem[]>([]);
  const [naicsOpen,    setNaicsOpen]    = useState(false);
  const [naicsLoading, setNaicsLoading] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Prevent selecting future dates
  const today = new Date().toISOString().split("T")[0];

  const { toast } = useToast();

  const isRunning  = state.status === "running";
  const isFinished = ["done", "stopped", "error"].includes(state.status);

  // ── Close dropdown when clicking outside ──────────────────────────────────
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setNaicsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  // ── NAICS search handler ──────────────────────────────────────────────────
  function handleNaicsSearch(e: React.ChangeEvent<HTMLInputElement>) {
    const q = e.target.value;
    setNaicsQuery(q);

    if (debounceRef.current) clearTimeout(debounceRef.current);

    if (!q.trim()) {
      setNaicsResults([]);
      setNaicsOpen(false);
      return;
    }

    debounceRef.current = setTimeout(async () => {
      setNaicsLoading(true);
      try {
        const data = await searchNaics(q, 1, 10);
        setNaicsResults(data.results);
        setNaicsOpen(data.results.length > 0);
      } catch {
        setNaicsResults([]);
      } finally {
        setNaicsLoading(false);
      }
    }, 300);
  }

  function addNaicsCode(code: string) {
    if (!naicsCodes.includes(code)) {
      setNaicsCodes((prev) => [...prev, code]);
    }
    setNaicsQuery("");
    setNaicsResults([]);
    setNaicsOpen(false);
  }

  function removeNaicsCode(code: string) {
    setNaicsCodes((prev) => prev.filter((c) => c !== code));
  }

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
          toast("success", "SAM.gov scraping complete!", `${res.record_count} bids saved to database`);
        } else if (res.status === "stopped") {
          toast("warning", "Scraping stopped", `${res.record_count} bids saved`);
        } else if (res.status === "error") {
          toast("error", "SAM.gov scraping failed", res.error?.slice(0, 100));
        }
      }
    },
    [setState, toast],
  );

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
        naics_codes: naicsCodes.length > 0 ? naicsCodes : undefined,
      });
      if (res.success && res.job_id) {
        setState({ status: "running", jobId: res.job_id, recordCount: 0 });
        const modeDesc = dateFrom
          ? `Date range: ${dateFrom}${dateTo ? ` → ${dateTo}` : " → today"}`
          : "All open bids";
        toast("info", "SAM.gov scraping started", modeDesc);
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
    exportSam(state.jobId);
    toast("info", "Preparing download", "Your Excel file will begin downloading shortly");
  }

  function handleReset() {
    reset();
    setStopping(false);
    setRangeError(null);
  }

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm">

      {/* Blue accent stripe */}
      <div className="h-1 bg-blue-600 rounded-t-2xl" />

      {/* Card header */}
      <div className="px-6 pt-5 pb-4 flex items-start justify-between gap-3 border-b border-slate-100">
        <div>
          <h2 className="text-base font-bold text-slate-900">SAM.gov Scraper</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Government bids — results saved to database
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
                Date Range — <span className="font-normal normal-case">optional</span>
              </p>

              <div className="grid grid-cols-2 gap-3">
                <Input
                  id="sam-date-from"
                  label="From Date"
                  type="date"
                  value={dateFrom}
                  onChange={handleFromChange}
                  max={today}
                  hint="Start of range"
                />
                <Input
                  id="sam-date-to"
                  label="To Date"
                  type="date"
                  value={dateTo}
                  onChange={handleToChange}
                  max={today}
                  hint="Defaults to today"
                />
              </div>

              {rangeError && (
                <p className="text-xs text-red-500 flex items-center gap-1.5">
                  <span aria-hidden>⚠</span> {rangeError}
                </p>
              )}

              {/* Active mode chip */}
              <div className="flex items-center gap-2 text-xs text-slate-500">
                <span>Mode:</span>
                <span className="inline-flex items-center rounded-full bg-blue-50 text-blue-700 border border-blue-100 px-2.5 py-0.5 font-medium text-xs">
                  {describeDateScenario(dateFrom, dateTo)}
                </span>
              </div>
            </div>

            {/* ── NAICS Code Filter ── */}
            <div className="space-y-3">
              <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-widest">
                NAICS Codes — <span className="font-normal normal-case">optional</span>
              </p>

              {/* Search input with dropdown */}
              <div ref={dropdownRef} className="relative">
                <input
                  type="text"
                  placeholder="Search by code or industry name…"
                  value={naicsQuery}
                  onChange={handleNaicsSearch}
                  onFocus={() => naicsResults.length > 0 && setNaicsOpen(true)}
                  className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:border-blue-300 focus:ring-1 focus:ring-blue-200 focus:bg-white outline-none transition-all"
                />
                {naicsLoading && (
                  <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-slate-400">
                    ...
                  </span>
                )}

                {/* Dropdown */}
                {naicsOpen && naicsResults.length > 0 && (
                  <div className="absolute z-50 mt-1 w-full max-h-48 overflow-y-auto rounded-lg border border-slate-200 bg-white shadow-lg">
                    {naicsResults.map((r) => {
                      const isSelected = naicsCodes.includes(r.code);
                      return (
                        <button
                          key={r.code}
                          type="button"
                          onClick={() => addNaicsCode(r.code)}
                          disabled={isSelected}
                          className={[
                            "w-full text-left px-3 py-2 text-xs flex items-center gap-2 transition-colors",
                            isSelected
                              ? "bg-blue-50 text-blue-400 cursor-not-allowed"
                              : "hover:bg-slate-50 text-slate-700",
                          ].join(" ")}
                        >
                          <span className="font-mono font-semibold shrink-0 w-16">{r.code}</span>
                          <span className="truncate">{r.title}</span>
                          {isSelected && <span className="ml-auto text-blue-500 shrink-0">Added</span>}
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Selected chips */}
              {naicsCodes.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {naicsCodes.map((code) => (
                    <span
                      key={code}
                      className="inline-flex items-center gap-1 rounded-full bg-blue-50 border border-blue-100 text-blue-700 px-2.5 py-1 text-xs font-medium"
                    >
                      {code}
                      <button
                        type="button"
                        onClick={() => removeNaicsCode(code)}
                        className="ml-0.5 text-blue-400 hover:text-blue-700 transition-colors leading-none"
                        aria-label={`Remove ${code}`}
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>

            <Button type="submit" className="w-full" variant="primary">
              Start Scraping SAM.gov
            </Button>
          </form>
        )}

        {/* ── Running ── */}
        {isRunning && (
          <div className="space-y-5">
            <div className="space-y-3">
              <div className="flex items-center justify-between gap-2">
                <p className="text-sm font-medium text-slate-700">
                  Collecting bids…
                </p>
                <span className="text-xl font-bold font-mono text-slate-900 tabular-nums leading-none">
                  {state.recordCount ?? 0}
                </span>
              </div>

              <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
                <div className="h-full bg-blue-500 animate-pulse rounded-full w-full" />
              </div>

              <div className="flex items-center justify-between">
                {state.jobId
                  ? <p className="text-xs text-slate-400 font-mono truncate">{state.jobId}</p>
                  : <span />}
                <p className="text-xs text-slate-400 shrink-0">bids saved</p>
              </div>
            </div>

            <div className="flex items-center justify-between gap-3 pt-1 border-t border-slate-100">
              <p className="text-xs text-slate-400">Stopping saves all collected bids.</p>
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
                  bids saved to database
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
