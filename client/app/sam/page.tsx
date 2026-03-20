import Link from "next/link";
import { Navbar } from "../components/landing/Navbar";
import { SiteFooter } from "../components/landing/SiteFooter";
import { SamScraperForm } from "../components/sam/SamScraperForm";

export default function SamPage() {
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <Navbar />

      {/* Main content — top-aligned with smart spacing */}
      <main className="flex-1 w-full max-w-6xl mx-auto px-6 py-10">

        {/* Breadcrumb */}
        <div className="mb-8">
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-blue-600 transition-colors font-medium group"
          >
            <span className="inline-flex items-center justify-center w-6 h-6 rounded-md bg-slate-100 group-hover:bg-blue-50 transition-colors">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 12H5"/><path d="m12 19-7-7 7-7"/></svg>
            </span>
            Back to Dashboard
          </Link>
        </div>

        {/* Two-column layout */}
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-8 items-start">

          {/* ── Left column: Info panel (2/5) ── */}
          <div className="lg:col-span-2 space-y-6">
            {/* Page header */}
            <div>
              <div className="inline-flex items-center gap-2 rounded-full bg-blue-50 border border-blue-100 text-blue-700 px-3.5 py-1.5 text-xs font-semibold mb-4">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500" />
                </span>
                SAM.gov — Federal Procurement
              </div>
              <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight leading-tight">
                Government Bid<br />Scraper
              </h1>
              <p className="mt-3 text-sm text-slate-500 leading-relaxed max-w-sm">
                Collect active federal solicitations filtered by date range and
                NAICS industry codes. Results are saved directly to your PostgreSQL
                database and exportable as Excel.
              </p>
            </div>

            {/* Quick info cards */}
            <div className="space-y-3">
              {/* Data source */}
              <div className="rounded-xl bg-white border border-slate-200 p-4 flex items-start gap-3">
                <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-blue-50 shrink-0 mt-0.5">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>
                </div>
                <div>
                  <p className="text-sm font-semibold text-slate-800">Data Source</p>
                  <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">
                    Scrapes active solicitations from the official SAM.gov API, the primary source for federal procurement data.
                  </p>
                </div>
              </div>

              {/* How it works */}
              <div className="rounded-xl bg-white border border-slate-200 p-4 flex items-start gap-3">
                <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-emerald-50 shrink-0 mt-0.5">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                </div>
                <div>
                  <p className="text-sm font-semibold text-slate-800">Stored Automatically</p>
                  <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">
                    All collected bids are saved to your PostgreSQL database in real time. Export to Excel anytime.
                  </p>
                </div>
              </div>

              {/* NAICS filter */}
              <div className="rounded-xl bg-white border border-slate-200 p-4 flex items-start gap-3">
                <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-violet-50 shrink-0 mt-0.5">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#8b5cf6" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/></svg>
                </div>
                <div>
                  <p className="text-sm font-semibold text-slate-800">NAICS Filtering</p>
                  <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">
                    Optionally filter by industry classification codes to target specific sectors like construction, IT, or healthcare.
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* ── Right column: Scraper form (3/5) ── */}
          <div className="lg:col-span-3">
            <SamScraperForm />
          </div>

        </div>
      </main>

      <SiteFooter />
    </div>
  );
}
