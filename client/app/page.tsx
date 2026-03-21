import Link from "next/link";
import { Navbar } from "./components/landing/Navbar";
import { HowItWorks } from "./components/landing/HowItWorks";
import { SiteFooter } from "./components/landing/SiteFooter";

// ── Scraper card data ───────────────────────────────────────────────────────

const SCRAPERS = [
  {
    href:        "/sam",
    tag:         "Federal Procurement",
    title:       "SAM.gov Scraper",
    description:
      "Automatically collect active federal solicitations from the U.S. System for Award Management. Filters out DoD, amendments, and non-procurement notices for you.",
    stats: [
      { label: "Fields extracted", value: "9" },
      { label: "Typical yield",    value: "50–500 bids" },
      { label: "Est. run time",    value: "15–40 min" },
    ],
    cta:       "Launch SAM.gov Scraper",
    badge:     "bg-blue-50 border-blue-100 text-blue-700",
    dot:       "bg-blue-500",
    btn:       "bg-blue-600 hover:bg-blue-700 shadow-blue-200",
    stripe:    "bg-blue-600",
    statColor: "text-blue-600",
  },
  {
    href:        "/septa",
    tag:         "Transit Procurement",
    title:       "SEPTA Scraper",
    description:
      "Collect open vendor quote requests from SEPTA's internal procurement portal. Authenticated with your server credentials — no manual login required.",
    stats: [
      { label: "Fields extracted", value: "4" },
      { label: "Typical yield",    value: "50–200 quotes" },
      { label: "Est. run time",    value: "1–5 min" },
    ],
    cta:       "Launch SEPTA Scraper",
    badge:     "bg-emerald-50 border-emerald-100 text-emerald-700",
    dot:       "bg-emerald-500",
    btn:       "bg-emerald-600 hover:bg-emerald-700 shadow-emerald-200",
    stripe:    "bg-emerald-600",
    statColor: "text-emerald-600",
  },
  {
    href:        "/naics",
    tag:         "Industry Classification",
    title:       "NAICS Code Scraper",
    description:
      "Scrape all 6-digit NAICS codes and industry titles from naics.com. Stored as a searchable reference dataset — search by code or keyword instantly.",
    stats: [
      { label: "Fields extracted", value: "2" },
      { label: "Total codes",      value: "~1,000+" },
      { label: "Est. run time",    value: "1–3 min" },
    ],
    cta:       "Launch NAICS Scraper",
    badge:     "bg-violet-50 border-violet-100 text-violet-700",
    dot:       "bg-violet-500",
    btn:       "bg-violet-600 hover:bg-violet-700 shadow-violet-200",
    stripe:    "bg-violet-600",
    statColor: "text-violet-600",
  },
] as const;

// ── Page ───────────────────────────────────────────────────────────────────

export default function Home() {
  return (
    <div className="min-h-screen bg-slate-50">
      <Navbar />

      {/* ── Hero ── */}
      <section className="bg-white border-b border-slate-100 py-12 sm:py-16">
        <div className="max-w-3xl mx-auto px-6 text-center">
          <span className="inline-flex items-center gap-2 rounded-full bg-blue-50 border border-blue-100 text-blue-700 px-4 py-1.5 text-xs font-semibold mb-5">
            <span className="h-1.5 w-1.5 rounded-full bg-blue-500 animate-pulse" />
            Government Procurement Intelligence Platform
          </span>
          <h1 className="text-4xl sm:text-5xl font-extrabold text-slate-900 leading-tight tracking-tight">
            Automate Your<br />
            <span className="text-blue-600">Bid Collection</span>
          </h1>
          <p className="mt-4 text-base sm:text-lg text-slate-500 max-w-xl mx-auto leading-relaxed">
            Scrape federal solicitations from{" "}
            <strong className="text-slate-700">SAM.gov</strong> and procurement
            quotes from <strong className="text-slate-700">SEPTA</strong> — with live
            progress tracking and one-click Excel export.
          </p>
        </div>
      </section>

      {/* ── Scraper Cards ── */}
      <section className="max-w-5xl mx-auto px-6 py-12 sm:py-16">
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-widest text-center mb-8">
          Choose a scraper to get started
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {SCRAPERS.map((s) => (
            <div
              key={s.href}
              className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden flex flex-col hover:-translate-y-1 transition-transform duration-300"
            >
              <Link href={s.href} className="flex flex-col h-full cursor-pointer">
                {/* Accent stripe */}
                <div className={`h-1.5 ${s.stripe}`} />

                <div className="p-7 flex flex-col gap-6 flex-1">
                  {/* Tag + title */}
                  <div className="text-center">
                    <span
                      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold ${s.badge}`}
                    >
                      <span className={`h-1.5 w-1.5 rounded-full ${s.dot}`} />
                      {s.tag}
                    </span>
                    <h2 className="mt-4 text-2xl font-extrabold text-slate-900">
                      {s.title}
                    </h2>
                  </div>

                  {/* CTA */}
                  <div className="mt-auto pt-2">
                    <div
                      className={`flex items-center justify-center gap-2 w-full rounded-xl text-white text-sm font-semibold px-5 py-3.5 shadow-lg transition-all ${s.btn}`}
                    >
                      {s.cta}
                      <span className="opacity-75">→</span>
                    </div>
                  </div>
                </div>
              </Link>
            </div>
          ))}
        </div>

        {/* Quick hint */}
        <p className="text-center text-xs text-slate-400 mt-6">
          Both scrapers can run simultaneously in independent background threads.
        </p>
      </section>

      {/* ── How It Works ── */}
      <HowItWorks />
      <SiteFooter />
    </div>
  );
}
