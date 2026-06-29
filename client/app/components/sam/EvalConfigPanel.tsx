"use client";

import { useState, useEffect, useRef } from "react";
import {
  getEvalConfig,
  addKillWord,
  deleteKillWord,
  addExcludedService,
  deleteExcludedService,
  addAllowedService,
  deleteAllowedService,
} from "../../services/evalConfigService";
import { useToast } from "../../context/ToastContext";

type Accent = "red" | "amber" | "emerald";

const TAG_BASE: Record<Accent, string> = {
  red:     "bg-red-600 border-red-700 text-white",
  amber:   "bg-amber-500 border-amber-600 text-white",
  emerald: "bg-emerald-600 border-emerald-700 text-white",
};

const TAG_BTN: Record<Accent, string> = {
  red:     "text-red-200 hover:text-white hover:bg-red-800",
  amber:   "text-amber-100 hover:text-white hover:bg-amber-700",
  emerald: "text-emerald-200 hover:text-white hover:bg-emerald-800",
};

const INPUT_RING: Record<Accent, string> = {
  red:     "focus:border-red-400 focus:ring-red-200",
  amber:   "focus:border-amber-400 focus:ring-amber-200",
  emerald: "focus:border-emerald-400 focus:ring-emerald-200",
};

const BTN_COLOR: Record<Accent, string> = {
  red:     "bg-red-600 hover:bg-red-700 disabled:bg-red-300",
  amber:   "bg-amber-500 hover:bg-amber-600 disabled:bg-amber-300",
  emerald: "bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-300",
};

const localeSort = (a: string, b: string) => a.localeCompare(b);

// ── Tag chip ────────────────────────────────────────────────────────────────

function Tag({ label, color, onRemove }: Readonly<{
  label: string;
  color: Accent;
  onRemove: () => void;
}>) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-semibold ${TAG_BASE[color]}`}
    >
      <span className="font-mono capitalize">{label}</span>
      <button
        type="button"
        onClick={onRemove}
        className={`ml-0.5 w-4 h-4 flex items-center justify-center rounded-full transition-all leading-none ${TAG_BTN[color]}`}
        aria-label={`Remove ${label}`}
      >
        ×
      </button>
    </span>
  );
}

// ── Add-word input row ───────────────────────────────────────────────────────

function AddRow({ placeholder, onAdd, loading, accent }: Readonly<{
  placeholder: string;
  onAdd: (value: string) => Promise<void>;
  loading: boolean;
  accent: Accent;
}>) {
  const [val, setVal] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

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
        className={`flex-1 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:ring-2 focus:bg-white outline-none transition-all ${INPUT_RING[accent]}`}
      />
      <button
        type="button"
        onClick={handleAdd}
        disabled={loading || !val.trim()}
        className={`shrink-0 px-4 py-2 rounded-lg text-white text-sm font-semibold transition-colors disabled:cursor-not-allowed ${BTN_COLOR[accent]}`}
      >
        {loading ? "..." : "Add"}
      </button>
    </div>
  );
}

// ── Main component ───────────────────────────────────────────────────────────

export function EvalConfigPanel({ defaultOpen = false }: Readonly<{ defaultOpen?: boolean }> = {}) {
  const [killWords,        setKillWords]        = useState<string[]>([]);
  const [excludedServices, setExcludedServices] = useState<string[]>([]);
  const [allowedServices,  setAllowedServices]  = useState<string[]>([]);
  const [loadingKW,        setLoadingKW]        = useState(false);
  const [loadingExcl,      setLoadingExcl]      = useState(false);
  const [loadingAllow,     setLoadingAllow]     = useState(false);
  const [fetchError,       setFetchError]       = useState<string | null>(null);
  const [open,             setOpen]             = useState(defaultOpen);
  const { toast } = useToast();

  async function fetchConfig() {
    setFetchError(null);
    try {
      const data = await getEvalConfig();
      setKillWords(data.kill_words);
      setExcludedServices(data.excluded_services);
      setAllowedServices(data.allowed_services);
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
      setKillWords((prev) => [...prev, value].sort(localeSort));
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

  // ── Excluded service handlers (Rule B) ───────────────────────────────────
  async function handleAddExcludedService(value: string) {
    setLoadingExcl(true);
    try {
      await addExcludedService(value);
      setExcludedServices((prev) => [...prev, value].sort(localeSort));
      toast("success", "Excluded service added", `"${value}" will be rejected everywhere`);
    } catch {
      toast("error", "Failed to add excluded service", "");
    } finally {
      setLoadingExcl(false);
    }
  }

  async function handleDeleteExcludedService(value: string) {
    setLoadingExcl(true);
    try {
      await deleteExcludedService(value);
      setExcludedServices((prev) => prev.filter((s) => s !== value));
      toast("warning", "Excluded service removed", `"${value}" is no longer auto-rejected`);
    } catch {
      toast("error", "Failed to remove excluded service", "");
    } finally {
      setLoadingExcl(false);
    }
  }

  // ── Allowed service handlers (Rule C) ────────────────────────────────────
  async function handleAddAllowedService(value: string) {
    setLoadingAllow(true);
    try {
      await addAllowedService(value);
      setAllowedServices((prev) => [...prev, value].sort(localeSort));
      toast("success", "Allowed service added", `"${value}" will be pursued if in US Mainland`);
    } catch {
      toast("error", "Failed to add allowed service", "");
    } finally {
      setLoadingAllow(false);
    }
  }

  async function handleDeleteAllowedService(value: string) {
    setLoadingAllow(true);
    try {
      await deleteAllowedService(value);
      setAllowedServices((prev) => prev.filter((s) => s !== value));
      toast("warning", "Allowed service removed", `"${value}" will no longer auto-qualify`);
    } catch {
      toast("error", "Failed to remove allowed service", "");
    } finally {
      setLoadingAllow(false);
    }
  }

  const hasAny = killWords.length > 0 || excludedServices.length > 0 || allowedServices.length > 0;
  const kwPlural = killWords.length === 1 ? "" : "s";
  const headerSubtitle = hasAny
    ? `${killWords.length} kill word${kwPlural} · ${excludedServices.length} excluded · ${allowedServices.length} allowed`
    : "Configure kill words, excluded services & allowed services";

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
            <p className="text-xs text-slate-400 mt-0.5">{headerSubtitle}</p>
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

          {/* Decision flow callout */}
          <div className="rounded-xl bg-blue-50 border border-blue-100 px-4 py-3 text-xs text-blue-700 leading-relaxed">
            <span className="font-semibold">Evaluation order:</span>{" "}
            Kill word check → Hardware vs Service → Excluded list (reject anywhere) → Allowed list (pursue if US Mainland) → Location check.
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

            {/* ── Kill Words ── */}
            <div className="flex flex-col h-full">
              <div className="flex items-center gap-2 mb-3">
                <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-red-600 text-white text-[10px] font-bold">✕</span>
                <p className="text-sm font-semibold text-slate-700">Kill Words</p>
                <span className="ml-auto inline-flex items-center rounded-full bg-red-600 text-white px-2.5 py-0.5 text-[11px] font-bold">
                  {killWords.length}
                </span>
              </div>
              <p className="text-xs text-slate-400 mb-3">Instant REJECT if found anywhere in bid text.</p>

              {killWords.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {killWords.map((w) => (
                    <Tag key={w} label={w} color="red" onRemove={() => handleDeleteKillWord(w)} />
                  ))}
                </div>
              ) : (
                <p className="text-xs text-slate-400 italic">No kill words configured.</p>
              )}

              <div className="mt-auto">
                <AddRow
                  placeholder='e.g. "sources sought"'
                  onAdd={handleAddKillWord}
                  loading={loadingKW}
                  accent="red"
                />
              </div>
            </div>

            {/* ── Excluded Services (Rule B) ── */}
            <div className="flex flex-col h-full">
              <div className="flex items-center gap-2 mb-3">
                <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-amber-500 text-white text-[10px] font-bold">B</span>
                <p className="text-sm font-semibold text-slate-700">Excluded Services</p>
                <span className="ml-auto inline-flex items-center rounded-full bg-amber-500 text-white px-2.5 py-0.5 text-[11px] font-bold">
                  {excludedServices.length}
                </span>
              </div>
              <p className="text-xs text-slate-400 mb-3">REJECT regardless of location (Rule B).</p>

              {excludedServices.length > 0 ? (
                <div className="flex flex-wrap gap-2 max-h-48 overflow-y-auto pr-1">
                  {excludedServices.map((s) => (
                    <Tag key={s} label={s} color="amber" onRemove={() => handleDeleteExcludedService(s)} />
                  ))}
                </div>
              ) : (
                <p className="text-xs text-slate-400 italic">No excluded services configured.</p>
              )}

              <div className="mt-auto">
                <AddRow
                  placeholder='e.g. "custodial services"'
                  onAdd={handleAddExcludedService}
                  loading={loadingExcl}
                  accent="amber"
                />
              </div>
            </div>

            {/* ── Allowed Services (Rule C) ── */}
            <div className="flex flex-col h-full">
              <div className="flex items-center gap-2 mb-3">
                <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-emerald-600 text-white text-[10px] font-bold">C</span>
                <p className="text-sm font-semibold text-slate-700">Allowed Services</p>
                <span className="ml-auto inline-flex items-center rounded-full bg-emerald-600 text-white px-2.5 py-0.5 text-[11px] font-bold">
                  {allowedServices.length}
                </span>
              </div>
              <p className="text-xs text-slate-400 mb-3">PURSUE only if performed in US Mainland (Rule C).</p>

              {allowedServices.length > 0 ? (
                <div className="flex flex-wrap gap-2 max-h-48 overflow-y-auto pr-1">
                  {allowedServices.map((s) => (
                    <Tag key={s} label={s} color="emerald" onRemove={() => handleDeleteAllowedService(s)} />
                  ))}
                </div>
              ) : (
                <p className="text-xs text-slate-400 italic">No allowed services configured.</p>
              )}

              <div className="mt-auto">
                <AddRow
                  placeholder='e.g. "hvac installation"'
                  onAdd={handleAddAllowedService}
                  loading={loadingAllow}
                  accent="emerald"
                />
              </div>
            </div>

          </div>

          <div className="rounded-xl bg-slate-50 border border-slate-100 px-4 py-3 text-xs text-slate-500 leading-relaxed">
            <span className="font-semibold text-slate-600">Changes take effect immediately</span> — the next scrape run will use the updated rules. Existing bids in the database are not re-evaluated.
          </div>

        </div>
      )}
    </div>
  );
}
