"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { Input } from "../ui/Input";
import { Button } from "../ui/Button";
import { StatusBadge } from "../ui/StatusBadge";
import { scrapeSam } from "../../services/samService";
import { stopJob } from "../../services/jobService";
import { exportSam } from "../../services/exportService";
import { searchNaics, getNaicsCount } from "../../services/naicsService";
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
  const [naicsDbCount, setNaicsDbCount] = useState<number | null>(null);
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

  // ── Fetch NAICS count from DB on mount ────────────────────────────────────
  useEffect(() => {
    getNaicsCount().then(setNaicsDbCount).catch(() => setNaicsDbCount(0));
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
    <div className="bg-white rounded-2xl border border-slate-200 shadow-lg shadow-slate-200/50">

      {/* Gradient accent stripe */}
      <div className="h-1.5 bg-gradient-to-r from-blue-500 via-blue-600 to-indigo-600 rounded-t-2xl" />

      {/* Card header */}
      <div className="px-7 pt-6 pb-5 flex items-center justify-between gap-3 border-b border-slate-100">
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-blue-50">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-900">SAM.gov Scraper</h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Government bids — results saved to database
            </p>
          </div>
        </div>
        <StatusBadge status={state.status} />
      </div>

      {/* Content */}
      <div className="p-7">

        {/* ── Idle: form ── */}
        {!isRunning && !isFinished && (
          <form onSubmit={handleSubmit} className="space-y-7" noValidate>

            {/* Date Range Section */}
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <div className="flex items-center justify-center w-6 h-6 rounded-md bg-slate-100">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#64748b" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
                </div>
                <p className="text-sm font-semibold text-slate-700">
                  Date Range
                </p>
                <span className="text-xs text-slate-400 font-normal ml-1">optional</span>
              </div>

              <div className="grid grid-cols-2 gap-4">
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
                <div className="flex items-center gap-2 rounded-lg bg-red-50 border border-red-100 px-3 py-2">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                  <p className="text-xs text-red-600 font-medium">{rangeError}</p>
                </div>
              )}

              {/* Active mode chip */}
              <div className="flex items-center gap-2.5 text-sm text-slate-600">
                <span className="font-medium">Mode:</span>
                <span className="inline-flex items-center rounded-full bg-blue-50 text-blue-700 border border-blue-100 px-3 py-1 font-medium text-xs">
                  {describeDateScenario(dateFrom, dateTo)}
                </span>
              </div>
            </div>

            {/* Divider */}
            <div className="h-px bg-slate-100" />

            {/* ── NAICS Code Filter ── */}
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <div className="flex items-center justify-center w-6 h-6 rounded-md bg-slate-100">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#64748b" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/></svg>
                </div>
                <p className="text-sm font-semibold text-slate-700">
                  NAICS Codes
                </p>
                <span className="text-xs text-slate-400 font-normal ml-1">optional</span>
                <span className="ml-auto">
                  {naicsDbCount === null ? (
                    <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 text-slate-400 px-2.5 py-0.5 text-[11px] font-medium animate-pulse">
                      Loading…
                    </span>
                  ) : naicsDbCount === 0 ? (
                    <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 border border-amber-200 text-amber-600 px-2.5 py-0.5 text-[11px] font-medium">
                      <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                      No codes in DB — scrape NAICS first
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 px-2.5 py-0.5 text-[11px] font-semibold">
                      <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                      {naicsDbCount.toLocaleString()} codes available
                    </span>
                  )}
                </span>
              </div>

              {/* Search input with dropdown */}
              <div ref={dropdownRef} className="relative">
                <div className="relative">
                  <svg className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                  <input
                    type="text"
                    placeholder="Search by code or industry name…"
                    value={naicsQuery}
                    onChange={handleNaicsSearch}
                    onFocus={() => naicsResults.length > 0 && setNaicsOpen(true)}
                    className="w-full rounded-lg border border-slate-200 bg-slate-50 pl-10 pr-3 py-2.5 text-sm text-slate-700 placeholder:text-slate-400 focus:border-blue-300 focus:ring-2 focus:ring-blue-100 focus:bg-white outline-none transition-all"
                  />
                  {naicsLoading && (
                    <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-slate-400 animate-pulse">
                      Searching…
                    </span>
                  )}
                </div>

                {/* Dropdown */}
                {naicsOpen && naicsResults.length > 0 && (
                  <div className="absolute z-50 mt-1.5 w-full max-h-56 overflow-y-auto rounded-xl border border-slate-200 bg-white shadow-xl shadow-slate-200/50">
                    {naicsResults.map((r) => {
                      const isSelected = naicsCodes.includes(r.code);
                      return (
                        <button
                          key={r.code}
                          type="button"
                          onClick={() => addNaicsCode(r.code)}
                          disabled={isSelected}
                          className={[
                            "w-full text-left px-4 py-2.5 text-sm flex items-center gap-3 transition-colors border-b border-slate-50 last:border-0",
                            isSelected
                              ? "bg-blue-50 text-blue-400 cursor-not-allowed"
                              : "hover:bg-blue-50/50 text-slate-700",
                          ].join(" ")}
                        >
                          <span className="font-mono font-semibold shrink-0 w-16 text-blue-600">{r.code}</span>
                          <span className="truncate">{r.title}</span>
                          {isSelected && (
                            <span className="ml-auto text-xs font-medium text-blue-500 shrink-0 flex items-center gap-1">
                              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                              Added
                            </span>
                          )}
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Selected chips */}
              {naicsCodes.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {naicsCodes.map((code) => (
                    <span
                      key={code}
                      className="inline-flex items-center gap-1.5 rounded-lg bg-blue-50 border border-blue-100 text-blue-700 px-3 py-1.5 text-xs font-semibold group"
                    >
                      <span className="font-mono">{code}</span>
                      <button
                        type="button"
                        onClick={() => removeNaicsCode(code)}
                        className="ml-0.5 w-4 h-4 flex items-center justify-center rounded-full text-blue-400 hover:text-white hover:bg-blue-500 transition-all leading-none"
                        aria-label={`Remove ${code}`}
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* Divider */}
            <div className="h-px bg-slate-100" />

            {/* Submit */}
            <Button type="submit" className="w-full !py-3 !text-base" variant="primary">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12a9 9 0 0 1-9 9m9-9a9 9 0 0 0-9-9m9 9H3m9 9a9 9 0 0 1-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 0 1 9-9"/></svg>
              Start Scraping SAM.gov
            </Button>
          </form>
        )}

        {/* ── Running ── */}
        {isRunning && (
          <div className="space-y-6">
            <div className="space-y-4">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
                  <p className="text-sm font-semibold text-slate-700">
                    Collecting bids…
                  </p>
                </div>
                <span className="text-2xl font-bold font-mono text-slate-900 tabular-nums leading-none">
                  {state.recordCount ?? 0}
                </span>
              </div>

              <div className="h-2.5 rounded-full bg-slate-100 overflow-hidden">
                <div className="h-full bg-gradient-to-r from-blue-500 to-blue-400 animate-pulse rounded-full w-full" />
              </div>

              <div className="flex items-center justify-between">
                {state.jobId
                  ? <p className="text-xs text-slate-400 font-mono truncate max-w-[200px]">{state.jobId}</p>
                  : <span />}
                <p className="text-xs text-slate-500 font-medium shrink-0">bids saved so far</p>
              </div>
            </div>

            <div className="flex items-center justify-between gap-3 pt-4 border-t border-slate-100">
              <p className="text-sm text-slate-500">Stopping gracefully saves all collected bids.</p>
              <Button variant="danger" loading={stopping} onClick={handleStop} className="shrink-0">
                {stopping ? "Stopping…" : "Stop Scraping"}
              </Button>
            </div>
          </div>
        )}

        {/* ── Done / Stopped ── */}
        {(state.status === "done" || state.status === "stopped") && (
          <div className="space-y-5">
            <div className="flex items-start gap-4 rounded-xl bg-emerald-50 border border-emerald-100 px-5 py-4">
              <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-emerald-100 shrink-0 mt-0.5">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
              </div>
              <div>
                <p className="text-base font-bold text-emerald-800">
                  {state.status === "stopped" ? "Stopped — partial data saved" : "Scraping complete!"}
                </p>
                <p className="text-sm text-emerald-700 mt-1">
                  <span className="font-mono font-bold text-lg">{state.recordCount ?? 0}</span>{" "}
                  bids saved to database
                </p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <Button variant="secondary" onClick={handleExport} className="!py-3">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                Export to Excel
              </Button>
              <Button variant="ghost" onClick={handleReset} className="!py-3">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
                New Scrape
              </Button>
            </div>
          </div>
        )}

        {/* ── Error ── */}
        {state.status === "error" && (
          <div className="space-y-5">
            <div className="flex items-start gap-4 rounded-xl bg-red-50 border border-red-100 px-5 py-4">
              <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-red-100 shrink-0 mt-0.5">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
              </div>
              <div>
                <p className="text-base font-bold text-red-800">Scraping failed</p>
                <p className="mt-1.5 text-sm text-red-600 font-mono break-all leading-relaxed">
                  {state.error}
                </p>
              </div>
            </div>
            <Button variant="ghost" onClick={handleReset} className="w-full !py-3">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
              Try Again
            </Button>
          </div>
        )}

      </div>
    </div>
  );
}
