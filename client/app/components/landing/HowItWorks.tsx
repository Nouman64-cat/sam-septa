const STEPS = [
  {
    number: "01",
    title: "Choose a Scraper",
    desc: "Select SAM.gov to collect federal government bid solicitations, or SEPTA to collect open procurement quotes from the SEPTA vendor portal.",
    icon: "🔍",
  },
  {
    number: "02",
    title: "Set Date Filters",
    desc: "Optionally narrow results by date. SAM.gov supports a full date range (from → to). SEPTA supports a single date filter. Leave blank to collect everything currently open.",
    icon: "📅",
  },
  {
    number: "03",
    title: "Start Scraping",
    desc: "Click Start. A headless Chrome browser launches on the server, navigates to the portal, and collects data page by page. SAM.gov takes 15–40 min; SEPTA takes 1–5 min.",
    icon: "▶",
  },
  {
    number: "04",
    title: "Watch Live Progress",
    desc: "A real-time counter shows exactly how many records have been saved to the database. Stop the scraper at any time — all data collected up to that point is preserved.",
    icon: "📊",
  },
  {
    number: "05",
    title: "Export to Excel",
    desc: "Once complete (or after stopping), click Export to Excel. A styled .xlsx file is generated on-demand from the database and downloads instantly to your browser.",
    icon: "⬇",
  },
];

export function HowItWorks() {
  return (
    <section id="guide" className="bg-slate-900 py-20 sm:py-28">
      <div className="max-w-6xl mx-auto px-6">

        {/* Header */}
        <div className="text-center mb-16">
          <span className="inline-flex items-center gap-2 rounded-full bg-slate-800 border border-slate-700 text-slate-400 px-4 py-1.5 text-xs font-semibold mb-6">
            User Guide
          </span>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
            How It Works
          </h2>
          <p className="mt-3 text-base text-slate-400 max-w-xl mx-auto">
            From zero to exported Excel in five steps.
          </p>
        </div>

        {/* Steps */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          {STEPS.map(({ number, title, desc, icon }, idx) => (
            <div
              key={number}
              className="relative rounded-2xl bg-slate-800 border border-slate-700 p-6 flex flex-col gap-3"
            >
              {/* Connector line (desktop only) */}
              {idx < STEPS.length - 1 && (
                <div
                  aria-hidden
                  className="hidden lg:block absolute top-8 -right-2 w-4 h-px bg-slate-600"
                />
              )}

              <div className="flex items-center justify-between">
                <span className="text-2xl">{icon}</span>
                <span className="text-xs font-bold text-slate-600 font-mono">
                  {number}
                </span>
              </div>
              <h3 className="text-sm font-bold text-white">{title}</h3>
              <p className="text-xs text-slate-400 leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>

      </div>
    </section>
  );
}
