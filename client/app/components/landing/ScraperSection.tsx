import type { ReactNode } from "react";

interface Field {
  name: string;
  desc: string;
}

interface Filter {
  label: string;
  desc: string;
}

export interface ScraperSectionProps {
  id: string;
  /** "blue" for SAM.gov, "emerald" for SEPTA */
  accent: "blue" | "emerald";
  badgeLabel: string;
  title: string;
  tagline: string;
  about: string[];
  sourceUrl: string;
  sourceName: string;
  fields: Field[];
  estimatedTime: string;
  typicalYield: string;
  filters: Filter[];
  tips: string[];
  form: ReactNode;
}

// ── Accent helpers ─────────────────────────────────────────────────────────────

const ACCENT = {
  blue: {
    badge:       "bg-blue-50 border-blue-100 text-blue-700",
    dot:         "bg-blue-500",
    sectionBg:   "bg-white",
    infoBg:      "bg-blue-50/40 border-blue-100",
    heading:     "text-blue-600",
    fieldIcon:   "text-blue-500",
    metricBorder:"border-blue-100 bg-blue-50",
    metricLabel: "text-blue-700",
    filterBullet:"bg-blue-400",
    tipBullet:   "bg-blue-200",
  },
  emerald: {
    badge:       "bg-emerald-50 border-emerald-100 text-emerald-700",
    dot:         "bg-emerald-500",
    sectionBg:   "bg-slate-50",
    infoBg:      "bg-emerald-50/50 border-emerald-100",
    heading:     "text-emerald-600",
    fieldIcon:   "text-emerald-500",
    metricBorder:"border-emerald-100 bg-emerald-50",
    metricLabel: "text-emerald-700",
    filterBullet:"bg-emerald-400",
    tipBullet:   "bg-emerald-200",
  },
};

// ── Component ──────────────────────────────────────────────────────────────────

export function ScraperSection({
  id,
  accent,
  badgeLabel,
  title,
  tagline,
  about,
  sourceUrl,
  sourceName,
  fields,
  estimatedTime,
  typicalYield,
  filters,
  tips,
  form,
}: ScraperSectionProps) {
  const c = ACCENT[accent];

  return (
    <section id={id} className={`${c.sectionBg} py-20 sm:py-24`}>
      <div className="max-w-6xl mx-auto px-6">

        {/* Section header */}
        <div className="mb-12">
          <span
            className={`inline-flex items-center gap-2 rounded-full border px-3.5 py-1 text-xs font-semibold ${c.badge}`}
          >
            <span className={`h-1.5 w-1.5 rounded-full ${c.dot}`} />
            {badgeLabel}
          </span>
          <h2 className="mt-4 text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
            {title}
          </h2>
          <p className="mt-2 text-base text-slate-500 max-w-xl">{tagline}</p>
        </div>

        {/* Two-column layout */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">

          {/* ── Left: Info panel ── */}
          <div className="space-y-6">

            {/* About */}
            <div className={`rounded-2xl border p-6 ${c.infoBg}`}>
              <h3 className={`text-sm font-bold uppercase tracking-widest ${c.heading} mb-3`}>
                About {sourceName}
              </h3>
              {about.map((para, i) => (
                <p key={i} className="text-sm text-slate-600 leading-relaxed mb-2 last:mb-0">
                  {para}
                </p>
              ))}
              <a
                href={sourceUrl}
                target="_blank"
                rel="noopener noreferrer"
                className={`inline-flex items-center gap-1 text-xs font-semibold mt-3 ${c.metricLabel} hover:underline`}
              >
                Visit {sourceName} ↗
              </a>
            </div>

            {/* What we extract */}
            <div className="rounded-2xl border border-slate-200 bg-white p-6">
              <h3 className="text-sm font-bold uppercase tracking-widest text-slate-400 mb-4">
                Extracted Fields
              </h3>
              <ul className="space-y-2.5">
                {fields.map(({ name, desc }) => (
                  <li key={name} className="flex items-start gap-2.5">
                    <span className={`mt-0.5 text-base font-bold ${c.fieldIcon}`}>✓</span>
                    <div>
                      <span className="text-sm font-semibold text-slate-800">{name}</span>
                      <span className="text-xs text-slate-400 ml-2">{desc}</span>
                    </div>
                  </li>
                ))}
              </ul>
            </div>

            {/* Performance metrics */}
            <div className="grid grid-cols-2 gap-3">
              <div className={`rounded-2xl border p-4 ${c.metricBorder}`}>
                <p className="text-[11px] font-bold uppercase tracking-widest text-slate-400">
                  Est. Duration
                </p>
                <p className={`text-xl font-extrabold mt-1 ${c.metricLabel}`}>
                  {estimatedTime}
                </p>
                <p className="text-xs text-slate-400 mt-0.5">per full run</p>
              </div>
              <div className={`rounded-2xl border p-4 ${c.metricBorder}`}>
                <p className="text-[11px] font-bold uppercase tracking-widest text-slate-400">
                  Typical Yield
                </p>
                <p className={`text-xl font-extrabold mt-1 ${c.metricLabel}`}>
                  {typicalYield}
                </p>
                <p className="text-xs text-slate-400 mt-0.5">records saved</p>
              </div>
            </div>

            {/* Smart filters */}
            <div className="rounded-2xl border border-slate-200 bg-white p-6">
              <h3 className="text-sm font-bold uppercase tracking-widest text-slate-400 mb-4">
                Smart Filters Applied
              </h3>
              <ul className="space-y-2.5">
                {filters.map(({ label, desc }) => (
                  <li key={label} className="flex items-start gap-2.5">
                    <span className={`mt-1.5 h-1.5 w-1.5 rounded-full shrink-0 ${c.filterBullet}`} />
                    <div>
                      <span className="text-sm font-semibold text-slate-700">{label}</span>
                      {desc && (
                        <span className="block text-xs text-slate-400 mt-0.5">{desc}</span>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            </div>

            {/* Tips */}
            <div className="rounded-2xl border border-slate-200 bg-white p-6">
              <h3 className="text-sm font-bold uppercase tracking-widest text-slate-400 mb-4">
                Tips &amp; Notes
              </h3>
              <ul className="space-y-2.5">
                {tips.map((tip, i) => (
                  <li key={i} className="flex items-start gap-2.5">
                    <span className={`mt-1.5 h-1.5 w-1.5 rounded-full shrink-0 ${c.tipBullet}`} />
                    <p className="text-xs text-slate-500 leading-relaxed">{tip}</p>
                  </li>
                ))}
              </ul>
            </div>

          </div>

          {/* ── Right: Scraper form ── */}
          <div className="lg:sticky lg:top-24">
            {form}
          </div>

        </div>
      </div>
    </section>
  );
}
