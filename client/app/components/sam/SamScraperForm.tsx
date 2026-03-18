"use client";

import { useState } from "react";
import { Card } from "../ui/Card";
import { Input } from "../ui/Input";
import { Button } from "../ui/Button";
import { StatusBadge } from "../ui/StatusBadge";
import { scrapeSam } from "../../services/samService";
import { getDownloadUrl } from "../../services/api";
import {
  validateDateRange,
  describeDateScenario,
} from "../../utils/dateUtils";
import {
  triggerDownload,
  extractFilename,
} from "../../utils/downloadUtils";
import type { ScraperState } from "../../types";

// ── Scenario hint cards ──────────────────────────────────────────────────────

const SCENARIOS = [
  { label: "Both dates", desc: "From → To" },
  { label: "From only", desc: "From → Today" },
  { label: "Same date", desc: "Exact day" },
  { label: "No dates", desc: "All bids" },
] as const;

// ── Component ────────────────────────────────────────────────────────────────

const INITIAL_STATE: ScraperState = { status: "idle" };

export function SamScraperForm() {
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [rangeError, setRangeError] = useState<string | null>(null);
  const [state, setState] = useState<ScraperState>(INITIAL_STATE);

  const isRunning = state.status === "running";

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
    if (err) {
      setRangeError(err);
      return;
    }

    setState({ status: "running" });

    try {
      const res = await scrapeSam({
        date_filter: dateFrom || undefined,
        date_to: dateTo || undefined,
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
        error: err instanceof Error ? err.message : "Network error — is the server running?",
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
          <h2 className="text-xl font-bold text-gray-900">SAM.gov Scraper</h2>
          <p className="text-sm text-gray-500 mt-0.5">
            Collects government bid notices from SAM.gov with optional date range
            filtering.
          </p>
        </div>
        <StatusBadge status={state.status} />
      </div>

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
              disabled={isRunning}
              hint="Start of the date range"
            />
            <Input
              id="sam-date-to"
              label="To Date"
              type="date"
              value={dateTo}
              onChange={handleToChange}
              disabled={isRunning}
              hint='Defaults to today when left empty'
            />
          </div>

          {/* Range validation error */}
          {rangeError && (
            <p className="text-sm text-red-600 flex items-center gap-1.5">
              <span aria-hidden>&#9888;</span>
              {rangeError}
            </p>
          )}

          {/* Active mode indicator */}
          <div className="flex items-center gap-2 rounded-lg border border-blue-100 bg-blue-50 px-3 py-2 text-xs text-blue-700">
            <span className="font-semibold whitespace-nowrap">Active mode:</span>
            <span className="font-mono">{describeDateScenario(dateFrom, dateTo)}</span>
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
          <span className="font-semibold">Note:</span> A Chrome window will open
          on the server. Large scrapes can take several minutes — please keep
          this tab open.
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
