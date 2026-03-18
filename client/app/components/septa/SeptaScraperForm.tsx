"use client";

import { useState } from "react";
import { Card } from "../ui/Card";
import { Input } from "../ui/Input";
import { Button } from "../ui/Button";
import { StatusBadge } from "../ui/StatusBadge";
import { scrapeSepta } from "../../services/septaService";
import { getDownloadUrl } from "../../services/api";
import { isValidDate } from "../../utils/dateUtils";
import { triggerDownload, extractFilename } from "../../utils/downloadUtils";
import type { ScraperState } from "../../types";

// ── Component ────────────────────────────────────────────────────────────────

const INITIAL_STATE: ScraperState = { status: "idle" };

export function SeptaScraperForm() {
  const [dateFilter, setDateFilter] = useState("");
  const [dateError, setDateError] = useState<string | null>(null);
  const [state, setState] = useState<ScraperState>(INITIAL_STATE);

  const isRunning = state.status === "running";

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

      if (res.success && res.filename) {
        setState({ status: "success", filename: res.filename });
      } else {
        setState({
          status: "error",
          error: res.error ?? "Scraping finished but no output file was created.",
        });
      }
    } catch (err: unknown) {
      setState({
        status: "error",
        error:
          err instanceof Error
            ? err.message
            : "Network error — is the server running?",
      });
    }
  }

  function handleDownload() {
    if (!state.filename) return;
    triggerDownload(
      getDownloadUrl(state.filename),
      extractFilename(state.filename),
    );
  }

  function handleDismiss() {
    setState(INITIAL_STATE);
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

      <form onSubmit={handleSubmit} className="space-y-5" noValidate>
        {/* Date filter */}
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
            disabled={isRunning}
            error={dateError ?? undefined}
            hint="Leave empty to scrape all currently open quotes"
          />

          {/* Active mode indicator */}
          <div className="flex items-center gap-2 rounded-lg border border-emerald-100 bg-emerald-50 px-3 py-2 text-xs text-emerald-700">
            <span className="font-semibold whitespace-nowrap">Active mode:</span>
            <span className="font-mono">
              {dateFilter ? `Filter by date: ${dateFilter}` : "No date filter — all open quotes"}
            </span>
          </div>
        </div>

        {/* Credential note */}
        <div className="rounded-xl border border-amber-100 bg-amber-50 px-4 py-3 text-xs text-amber-700">
          <span className="font-semibold">Credentials:</span> The scraper uses
          the SEPTA username &amp; password configured in the server&apos;s{" "}
          <code className="font-mono">.env</code> file.
        </div>

        {/* Submit */}
        <Button
          type="submit"
          loading={isRunning}
          disabled={isRunning}
          className="w-full"
        >
          {isRunning ? "Scraping in progress…" : "Start Scraping"}
        </Button>
      </form>

      {/* Running notice */}
      {isRunning && (
        <div className="mt-4 rounded-xl border border-blue-100 bg-blue-50 px-4 py-3 text-xs text-blue-700">
          <span className="font-semibold">Note:</span> A headless browser is
          logging into SEPTA and scraping quotes. This can take a few minutes —
          please keep this tab open.
        </div>
      )}

      {/* Success panel */}
      {state.status === "success" && state.filename && (
        <div className="mt-5 rounded-xl border border-green-200 bg-green-50 p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="text-sm font-semibold text-green-800">
              Scraping complete!
            </p>
            <p className="text-xs text-green-700 mt-0.5 font-mono truncate">
              {extractFilename(state.filename)}
            </p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <Button variant="secondary" onClick={handleDownload}>
              Download
            </Button>
            <Button variant="ghost" onClick={handleDismiss}>
              Reset
            </Button>
          </div>
        </div>
      )}

      {/* Error panel */}
      {state.status === "error" && (
        <div className="mt-5 rounded-xl border border-red-200 bg-red-50 p-4">
          <p className="text-sm font-semibold text-red-800">Scraping failed</p>
          <p className="mt-1 text-xs text-red-700 font-mono break-all">
            {state.error}
          </p>
          <button
            onClick={handleDismiss}
            className="mt-3 text-xs text-red-600 underline hover:no-underline"
          >
            Dismiss
          </button>
        </div>
      )}
    </Card>
  );
}
