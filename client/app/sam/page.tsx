import Link from "next/link";
import { Navbar } from "../components/landing/Navbar";
import { SiteFooter } from "../components/landing/SiteFooter";
import { SamScraperForm } from "../components/sam/SamScraperForm";

export default function SamPage() {
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <Navbar />

      {/* Main — vertically centered */}
      <main className="flex-1 flex flex-col items-center justify-center px-6 py-14">

        {/* Back link */}
        <div className="w-full max-w-md mb-6">
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-700 transition-colors font-medium"
          >
            ← Back to Home
          </Link>
        </div>

        {/* Description */}
        <div className="w-full max-w-md mb-6 text-center">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-blue-50 border border-blue-100 text-blue-700 px-3 py-1 text-xs font-semibold mb-3">
            <span className="h-1.5 w-1.5 rounded-full bg-blue-500" />
            SAM.gov — Federal Procurement
          </span>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
            SAM.gov Government Bid Scraper
          </h1>
          <p className="mt-2 text-sm text-slate-500 leading-relaxed">
            Collect active federal solicitations filtered by date range.
            Results are saved directly to your PostgreSQL database and
            exportable as Excel.
          </p>
        </div>

        {/* Scraper form — centred card */}
        <div className="w-full max-w-md">
          <SamScraperForm />
        </div>

      </main>

      <SiteFooter />
    </div>
  );
}
