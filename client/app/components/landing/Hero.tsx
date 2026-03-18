const STATS = [
  {
    value: "9",
    label: "Fields per bid",
    sub: "SAM.gov extractions",
    color: "text-blue-600",
  },
  {
    value: "4",
    label: "Fields per quote",
    sub: "SEPTA extractions",
    color: "text-emerald-600",
  },
  {
    value: "Live",
    label: "Progress tracking",
    sub: "Real-time counter",
    color: "text-violet-600",
  },
  {
    value: ".xlsx",
    label: "Export format",
    sub: "One-click download",
    color: "text-amber-600",
  },
];

export function Hero() {
  return (
    <section
      id="top"
      className="relative overflow-hidden bg-gradient-to-b from-blue-50/60 via-slate-50 to-white pt-20 pb-24 sm:pt-28 sm:pb-32"
    >
      {/* Decorative background blobs */}
      <div
        aria-hidden
        className="pointer-events-none absolute -top-32 -left-32 h-96 w-96 rounded-full bg-blue-100/40 blur-3xl"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute -top-16 right-0 h-72 w-72 rounded-full bg-emerald-100/30 blur-3xl"
      />

      <div className="relative max-w-4xl mx-auto px-6 text-center">
        {/* Eyebrow */}
        <span className="inline-flex items-center gap-2 rounded-full bg-white border border-blue-100 text-blue-700 px-4 py-1.5 text-xs font-semibold shadow-sm mb-8">
          <span className="h-1.5 w-1.5 rounded-full bg-blue-500 animate-pulse" />
          Government Procurement Intelligence Platform
        </span>

        {/* Headline */}
        <h1 className="text-4xl sm:text-5xl lg:text-[56px] font-extrabold text-slate-900 leading-[1.12] tracking-tight">
          Automate Government Bid
          <br className="hidden sm:block" />{" "}
          <span className="text-blue-600">Collection</span> &amp; Export
        </h1>

        {/* Subheading */}
        <p className="mt-6 text-lg text-slate-500 max-w-2xl mx-auto leading-relaxed">
          Scrape{" "}
          <strong className="font-semibold text-slate-700">SAM.gov</strong>{" "}
          federal solicitations and{" "}
          <strong className="font-semibold text-slate-700">SEPTA</strong>{" "}
          procurement quotes automatically — with live progress tracking,
          PostgreSQL storage, and styled Excel exports.
        </p>

        {/* CTA buttons */}
        <div className="mt-9 flex items-center justify-center gap-3 flex-wrap">
          <a
            href="#sam"
            className="inline-flex items-center gap-2 rounded-xl bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white px-6 py-3.5 text-sm font-semibold shadow-lg shadow-blue-200 transition-all hover:-translate-y-0.5"
          >
            SAM.gov Scraper
            <span aria-hidden className="opacity-80">→</span>
          </a>
          <a
            href="#septa"
            className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 active:bg-emerald-800 text-white px-6 py-3.5 text-sm font-semibold shadow-lg shadow-emerald-200 transition-all hover:-translate-y-0.5"
          >
            SEPTA Scraper
            <span aria-hidden className="opacity-80">→</span>
          </a>
          <a
            href="#guide"
            className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 px-6 py-3.5 text-sm font-semibold transition-colors"
          >
            How It Works
          </a>
        </div>

        {/* Stats */}
        <div className="mt-16 grid grid-cols-2 sm:grid-cols-4 gap-4">
          {STATS.map(({ value, label, sub, color }) => (
            <div
              key={label}
              className="rounded-2xl bg-white border border-slate-200 shadow-sm px-5 py-5 text-left"
            >
              <p className={`text-2xl font-extrabold ${color}`}>{value}</p>
              <p className="text-xs font-semibold text-slate-700 mt-1.5">
                {label}
              </p>
              <p className="text-xs text-slate-400 mt-0.5">{sub}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
