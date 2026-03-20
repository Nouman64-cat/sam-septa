import Link from "next/link";
import { Navbar } from "../components/landing/Navbar";
import { SiteFooter } from "../components/landing/SiteFooter";
import { NaicsPage } from "../components/naics/NaicsPage";

export default function NaicsRoutePage() {
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <Navbar />

      <main className="flex-1 px-6 py-14">
        <div className="max-w-4xl mx-auto">

          <div className="mb-6">
            <Link
              href="/"
              className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-700 transition-colors font-medium"
            >
              ← Back to Home
            </Link>
          </div>

          <div className="mb-8 text-center">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-violet-50 border border-violet-100 text-violet-700 px-3 py-1 text-xs font-semibold mb-3">
              <span className="h-1.5 w-1.5 rounded-full bg-violet-500" />
              NAICS — Industry Classification
            </span>
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
              NAICS Code Reference
            </h1>
            <p className="mt-2 text-sm text-slate-500 leading-relaxed">
              Scrape all 6-digit NAICS codes and industry titles from naics.com.
              Search by code or keyword once scraped.
            </p>
          </div>

          <NaicsPage />

        </div>
      </main>

      <SiteFooter />
    </div>
  );
}
