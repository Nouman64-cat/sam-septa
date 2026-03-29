"use client";

import { useState, useEffect, useRef } from "react";
import {
  getEvalConfig,
  addKillWord,
  deleteKillWord,
  addAllowedState,
  deleteAllowedState,
} from "../../services/evalConfigService";
import { useToast } from "../../context/ToastContext";

// ── Tag chip ────────────────────────────────────────────────────────────────

function Tag({
  label,
  color,
  onRemove,
}: {
  label: string;
  color: "red" | "emerald";
  onRemove: () => void;
}) {
  const base =
    color === "red"
      ? "bg-red-50 border-red-100 text-red-700"
      : "bg-emerald-50 border-emerald-100 text-emerald-700";
  const btn =
    color === "red"
      ? "text-red-400 hover:text-white hover:bg-red-500"
      : "text-emerald-400 hover:text-white hover:bg-emerald-500";

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-semibold ${base}`}
    >
      <span className="font-mono capitalize">{label}</span>
      <button
        type="button"
        onClick={onRemove}
        className={`ml-0.5 w-4 h-4 flex items-center justify-center rounded-full transition-all leading-none ${btn}`}
        aria-label={`Remove ${label}`}
      >
        ×
      </button>
    </span>
  );
}

// ── Add-word input row ───────────────────────────────────────────────────────

function AddRow({
  placeholder,
  onAdd,
  loading,
  accent,
}: {
  placeholder: string;
  onAdd: (value: string) => Promise<void>;
  loading: boolean;
  accent: "red" | "emerald";
}) {
  const [val, setVal] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const focusRing =
    accent === "red"
      ? "focus:border-red-300 focus:ring-red-100"
      : "focus:border-emerald-300 focus:ring-emerald-100";
  const btnColor =
    accent === "red"
      ? "bg-red-600 hover:bg-red-700 disabled:bg-red-200"
      : "bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-200";

  async function handleAdd() {
    const trimmed = val.trim().toLowerCase();
    if (!trimmed) return;
    await onAdd(trimmed);
    setVal("");
    inputRef.current?.focus();
  }

  return (
    <div className="flex gap-2 mt-3">
      <input
        ref={inputRef}
        type="text"
        value={val}
        onChange={(e) => setVal(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && handleAdd()}
        placeholder={placeholder}
        disabled={loading}
        className={`flex-1 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:ring-2 focus:bg-white outline-none transition-all ${focusRing}`}
      />
      <button
        type="button"
        onClick={handleAdd}
        disabled={loading || !val.trim()}
        className={`shrink-0 px-4 py-2 rounded-lg text-white text-sm font-semibold transition-colors disabled:cursor-not-allowed ${btnColor}`}
      >
        {loading ? "..." : "Add"}
      </button>
    </div>
  );
}

// ── Main component ───────────────────────────────────────────────────────────

export function EvalConfigPanel({ defaultOpen = false }: { defaultOpen?: boolean } = {}) {
  const [killWords,     setKillWords]     = useState<string[]>([]);
  const [allowedStates, setAllowedStates] = useState<string[]>([]);
  const [loadingKW,     setLoadingKW]     = useState(false);
  const [loadingAS,     setLoadingAS]     = useState(false);
  const [fetchError,    setFetchError]    = useState<string | null>(null);
  const [open,          setOpen]          = useState(defaultOpen);
  const { toast } = useToast();

  async function fetchConfig() {
    setFetchError(null);
    try {
      const data = await getEvalConfig();
      setKillWords(data.kill_words);
      setAllowedStates(data.allowed_states);
    } catch {
      setFetchError("Could not load evaluator settings.");
    }
  }

  useEffect(() => {
    if (open) fetchConfig();
  }, [open]);

  // ── Kill word handlers ────────────────────────────────────────────────────
  async function handleAddKillWord(value: string) {
    setLoadingKW(true);
    try {
      await addKillWord(value);
      setKillWords((prev) => [...prev, value].sort());
      toast("success", "Kill word added", `"${value}" will instantly reject matching bids`);
    } catch {
      toast("error", "Failed to add kill word", "");
    } finally {
      setLoadingKW(false);
    }
  }

  async function handleDeleteKillWord(value: string) {
    setLoadingKW(true);
    try {
      await deleteKillWord(value);
      setKillWords((prev) => prev.filter((w) => w !== value));
      toast("warning", "Kill word removed", `"${value}" will no longer reject bids`);
    } catch {
      toast("error", "Failed to remove kill word", "");
    } finally {
      setLoadingKW(false);
    }
  }

  // ── Allowed state handlers ────────────────────────────────────────────────
  async function handleAddAllowedState(value: string) {
    setLoadingAS(true);
    try {
      await addAllowedState(value);
      setAllowedStates((prev) => [...prev, value].sort());
      toast("success", "State/region added", `"${value}" is now an allowed work location`);
    } catch {
      toast("error", "Failed to add state", "");
    } finally {
      setLoadingAS(false);
    }
  }

  async function handleDeleteAllowedState(value: string) {
    setLoadingAS(true);
    try {
      await deleteAllowedState(value);
      setAllowedStates((prev) => prev.filter((s) => s !== value));
      toast("warning", "State/region removed", `Bids for "${value}" may now be restricted`);
    } catch {
      toast("error", "Failed to remove state", "");
    } finally {
      setLoadingAS(false);
    }
  }

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="mt-6 bg-white rounded-2xl border border-slate-200 shadow-sm shadow-slate-100/80">

      {/* Collapsible header */}
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-6 py-4 text-left group"
      >
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-slate-100 group-hover:bg-slate-200 transition-colors">
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#64748b" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
            </svg>
          </div>
          <div>
            <p className="text-sm font-bold text-slate-800">Evaluator Settings</p>
            <p className="text-xs text-slate-400 mt-0.5">
              {killWords.length > 0 || allowedStates.length > 0
                ? `${killWords.length} kill word${killWords.length !== 1 ? "s" : ""} · ${allowedStates.length} allowed state${allowedStates.length !== 1 ? "s" : ""}`
                : "Configure kill words & allowed work locations"}
            </p>
          </div>
        </div>
        <svg
          width="16" height="16" viewBox="0 0 24 24" fill="none"
          stroke="#94a3b8" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"
          className={`transition-transform duration-200 ${open ? "rotate-180" : ""}`}
        >
          <polyline points="6 9 12 15 18 9"/>
        </svg>
      </button>

      {/* Expanded content */}
      {open && (
        <div className="px-6 pb-6 space-y-6 border-t border-slate-100 pt-5">

          {fetchError && (
            <div className="rounded-lg bg-red-50 border border-red-100 px-4 py-3 text-sm text-red-600">
              {fetchError}
            </div>
          )}

          {/* ── Kill Words ── */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-red-100 text-red-600 text-[10px] font-bold">✕</span>
              <p className="text-sm font-semibold text-slate-700">Kill Words</p>
              <span className="text-xs text-slate-400">— instant REJECT if found in bid text</span>
              <span className="ml-auto inline-flex items-center rounded-full bg-red-50 border border-red-100 text-red-600 px-2 py-0.5 text-[11px] font-semibold">
                {killWords.length}
              </span>
            </div>

            {killWords.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {killWords.map((w) => (
                  <Tag
                    key={w}
                    label={w}
                    color="red"
                    onRemove={() => handleDeleteKillWord(w)}
                  />
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-400 italic">No kill words configured.</p>
            )}

            <AddRow
              placeholder='Add kill word, e.g. "idiq"'
              onAdd={handleAddKillWord}
              loading={loadingKW}
              accent="red"
            />
          </div>

          {/* Divider */}
          <div className="h-px bg-slate-100" />

          {/* ── Allowed States ── */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-emerald-100 text-emerald-600 text-[10px] font-bold">✓</span>
              <p className="text-sm font-semibold text-slate-700">Allowed States</p>
              <span className="text-xs text-slate-400">— locations we can deliver to</span>
              <span className="ml-auto inline-flex items-center rounded-full bg-emerald-50 border border-emerald-100 text-emerald-600 px-2 py-0.5 text-[11px] font-semibold">
                {allowedStates.length}
              </span>
            </div>

            {/* Info note about how restriction works */}
            <div className="mb-3 rounded-lg bg-slate-50 border border-slate-100 px-3 py-2.5 text-xs text-slate-500 leading-relaxed">
              <span className="font-semibold text-slate-600">How it works:</span> Bids for Guam, Puerto Rico, US Virgin Islands, American Samoa, and Northern Mariana Islands trigger an AI check (services → reject, hardware → pass). Adding those to this list would allow them unconditionally.
            </div>

            {allowedStates.length > 0 ? (
              <div className="flex flex-wrap gap-2 max-h-48 overflow-y-auto pr-1">
                {allowedStates.map((s) => (
                  <Tag
                    key={s}
                    label={s}
                    color="emerald"
                    onRemove={() => handleDeleteAllowedState(s)}
                  />
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-400 italic">No allowed states configured — all territories will be flagged.</p>
            )}

            <AddRow
              placeholder='Add state, e.g. "alaska"'
              onAdd={handleAddAllowedState}
              loading={loadingAS}
              accent="emerald"
            />
          </div>

          {/* Info callout */}
          <div className="rounded-xl bg-blue-50 border border-blue-100 px-4 py-3 text-xs text-blue-700 leading-relaxed">
            <span className="font-semibold">Changes take effect immediately</span> — the next scrape run will use the updated rules. Existing bids in the database are not re-evaluated.
          </div>

        </div>
      )}
    </div>
  );
}
