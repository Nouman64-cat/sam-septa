import Link from "next/link";
import { Navbar } from "../components/landing/Navbar";
import { SiteFooter } from "../components/landing/SiteFooter";
import { SamTabs } from "../components/sam/SamTabs";

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

        {/* Single-column layout */}
        <div className="max-w-4xl mx-auto items-start">
          {/* ── Tabbed scraper + evaluator ── */}
          <div className="w-full">
            <SamTabs />
          </div>

        </div>
      </main>

      <SiteFooter />
    </div>
  );
}
