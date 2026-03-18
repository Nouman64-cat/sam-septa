import Link from "next/link";

export function SiteFooter() {
  return (
    <footer className="bg-slate-900 border-t border-slate-800">
      <div className="max-w-6xl mx-auto px-6 py-8 flex flex-col sm:flex-row items-center justify-between gap-4">
        {/* Brand */}
        <div className="flex items-center gap-2.5">
          <div className="flex items-center justify-center h-7 w-7 rounded-lg bg-blue-600 select-none">
            <span className="text-white font-bold text-xs">SG</span>
          </div>
          <span className="text-sm font-bold text-slate-300">
            BidScraper Pro
          </span>
        </div>

        <p className="text-xs text-slate-500 text-center">
          Automated government procurement data collection for SAM.gov and SEPTA. All data is stored in your PostgreSQL database.
        </p>

        <div className="flex items-center gap-4 text-xs text-slate-500">
          <Link href="/sam"   className="hover:text-slate-300 transition-colors">SAM.gov</Link>
          <Link href="/septa" className="hover:text-slate-300 transition-colors">SEPTA</Link>
          <Link href="/#guide" className="hover:text-slate-300 transition-colors">Guide</Link>
        </div>
      </div>
    </footer>
  );
}
