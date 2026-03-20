"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { Button } from "../ui/Button";
import { Input } from "../ui/Input";
import { StatusBadge } from "../ui/StatusBadge";
import { scrapeNaics, listNaics, searchNaics } from "../../services/naicsService";
import { stopJob } from "../../services/jobService";
import { useJobPoller } from "../../hooks/useJobPoller";
import { useToast } from "../../context/ToastContext";
import { useNaicsScraper } from "../../context/NaicsScraperContext";
import type { NaicsCodeItem, JobStatusResponse } from "../../types";

export function NaicsPage() {
  const { state, setState, reset } = useNaicsScraper();
  const [stopping, setStopping] = useState(false);
  const { toast } = useToast();

  // ── Search / results state ────────────────────────────────────────────────
  const [query,   setQuery]   = useState("");
  const [results, setResults] = useState<NaicsCodeItem[]>([]);
  const [total,   setTotal]   = useState(0);
  const [page,    setPage]    = useState(1);
  const [loading, setLoading] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const LIMIT = 50;

  const isRunning  = state.status === "running";
  const isFinished = ["done", "stopped", "error"].includes(state.status);

  // ── Fetch results ─────────────────────────────────────────────────────────

  const fetchResults = useCallback(async (q: string, p: number) => {
    setLoading(true);
    try {
      const data = q ? await searchNaics(q, p, LIMIT) : await listNaics(p, LIMIT);
      setResults(data.results);
      setTotal(data.total);
    } catch {
      // silently ignore — table will stay empty
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial load
  useEffect(() => { fetchResults("", 1); }, [fetchResults]);

  // Debounced search on query change
  function handleQueryChange(e: React.ChangeEvent<HTMLInputElement>) {
    const q = e.target.value;
    setQuery(q);
    setPage(1);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => fetchResults(q, 1), 400);
  }

  function handlePage(next: number) {
    setPage(next);
    fetchResults(query, next);
  }

  // ── Job polling ───────────────────────────────────────────────────────────

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
          toast("success", "NAICS scraping complete!", `${res.record_count} codes saved`);
          fetchResults(query, 1);   // refresh table
        } else if (res.status === "stopped") {
          toast("warning", "Scraping stopped", `${res.record_count} codes saved`);
          fetchResults(query, 1);
        } else if (res.status === "error") {
          toast("error", "NAICS scraping failed", res.error?.slice(0, 100));
        }
      }
    },
    [setState, toast, fetchResults, query],
  );

  useJobPoller(state.jobId, { onStatusUpdate: handleStatusUpdate });

  // ── Handlers ──────────────────────────────────────────────────────────────

  async function handleStart() {
    setState({ status: "running" });
    try {
      const res = await scrapeNaics();
      if (res.success && res.job_id) {
        setState({ status: "running", jobId: res.job_id, recordCount: 0 });
        toast("info", "NAICS scraping started", "Fetching all 6-digit codes…");
      } else {
        setState({ status: "error", error: res.error ?? "Failed to start job." });
        toast("error", "Failed to start", res.error);
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

  function handleReset() {
    reset();
    setStopping(false);
  }

  const totalPages = Math.ceil(total / LIMIT);

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="space-y-6">

      {/* ── Scraper Control Card ── */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden max-w-md mx-auto">
        <div className="h-1 bg-violet-600" />

        <div className="px-6 pt-5 pb-4 flex items-start justify-between gap-3 border-b border-slate-100">
          <div>
            <h2 className="text-base font-bold text-slate-900">NAICS Code Scraper</h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Fetches all 6-digit industry codes from naics.com
            </p>
          </div>
          <StatusBadge status={state.status} />
        </div>

        <div className="p-6">

          {/* Idle */}
          {!isRunning && !isFinished && (
            <div className="space-y-4">
              <p className="text-xs text-slate-500 leading-relaxed">
                Scrapes every 6-digit NAICS code and industry title across all sectors.
                Estimated run time: <span className="font-semibold text-slate-700">1–3 minutes</span>.
              </p>
              <Button onClick={handleStart} className="w-full" variant="primary">
                Start Scraping NAICS Codes
              </Button>
            </div>
          )}

          {/* Running */}
          {isRunning && (
            <div className="space-y-5">
              <div className="space-y-3">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-medium text-slate-700">Collecting codes…</p>
                  <span className="text-xl font-bold font-mono text-slate-900 tabular-nums leading-none">
                    {state.recordCount ?? 0}
                  </span>
                </div>
                <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
                  <div className="h-full bg-violet-500 animate-pulse rounded-full w-full" />
                </div>
                <div className="flex items-center justify-between">
                  {state.jobId
                    ? <p className="text-xs text-slate-400 font-mono truncate">{state.jobId}</p>
                    : <span />}
                  <p className="text-xs text-slate-400 shrink-0">codes saved</p>
                </div>
              </div>
              <div className="flex items-center justify-between gap-3 pt-1 border-t border-slate-100">
                <p className="text-xs text-slate-400">Stopping saves all collected codes.</p>
                <Button variant="danger" loading={stopping} onClick={handleStop} className="shrink-0">
                  {stopping ? "Stopping…" : "Stop"}
                </Button>
              </div>
            </div>
          )}

          {/* Done / Stopped */}
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
                    codes saved to database
                  </p>
                </div>
              </div>
              <Button variant="ghost" onClick={handleReset} className="w-full">
                + New Scrape
              </Button>
            </div>
          )}

          {/* Error */}
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

      {/* ── Search & Results ── */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 pt-5 pb-4 border-b border-slate-100 flex items-center justify-between gap-4">
          <div>
            <h3 className="text-sm font-bold text-slate-900">NAICS Code Reference</h3>
            <p className="text-xs text-slate-400 mt-0.5">
              {total > 0 ? `${total.toLocaleString()} codes in database` : "No codes scraped yet"}
            </p>
          </div>
          <div className="w-64">
            <Input
              id="naics-search"
              label=""
              placeholder="Search by code or keyword…"
              value={query}
              onChange={handleQueryChange}
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50">
                <th className="text-left py-2.5 px-4 text-xs font-semibold text-slate-500 uppercase tracking-wider w-32">
                  NAICS Code
                </th>
                <th className="text-left py-2.5 px-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                  Industry Title
                </th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr>
                  <td colSpan={2} className="py-10 text-center text-xs text-slate-400">
                    Loading…
                  </td>
                </tr>
              )}
              {!loading && results.length === 0 && (
                <tr>
                  <td colSpan={2} className="py-10 text-center text-xs text-slate-400">
                    {total === 0
                      ? "No NAICS codes in database yet. Run the scraper above to populate."
                      : "No codes match your search."}
                  </td>
                </tr>
              )}
              {!loading && results.map((r) => (
                <tr
                  key={r.code}
                  className="border-b border-slate-50 hover:bg-violet-50/40 transition-colors"
                >
                  <td className="py-2.5 px-4 font-mono text-slate-700 font-semibold text-xs">
                    {r.code}
                  </td>
                  <td className="py-2.5 px-4 text-slate-600 text-xs">
                    {r.title}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="px-6 py-3 border-t border-slate-100 flex items-center justify-between gap-3">
            <button
              onClick={() => handlePage(page - 1)}
              disabled={page <= 1}
              className="text-xs font-medium text-slate-500 hover:text-slate-900 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              ← Previous
            </button>
            <span className="text-xs text-slate-400">
              Page {page} of {totalPages}
            </span>
            <button
              onClick={() => handlePage(page + 1)}
              disabled={page >= totalPages}
              className="text-xs font-medium text-slate-500 hover:text-slate-900 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              Next →
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
