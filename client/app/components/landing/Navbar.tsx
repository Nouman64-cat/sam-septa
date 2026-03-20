"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect } from "react";

export function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const isHome  = pathname === "/";
  const isSam   = pathname === "/sam";
  const isSepta = pathname === "/septa";
  const isNaics = pathname === "/naics";

  const navLink = (active: boolean) =>
    [
      "text-sm font-medium transition-colors",
      active ? "text-slate-900" : "text-slate-500 hover:text-slate-900",
    ].join(" ");

  return (
    <nav
      className={[
        "sticky top-0 z-50 bg-white/95 backdrop-blur-sm transition-all duration-200",
        scrolled
          ? "border-b border-slate-200 shadow-sm"
          : "border-b border-transparent",
      ].join(" ")}
    >
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center gap-8">
        {/* Brand */}
        <Link href="/" className="flex items-center gap-2.5 shrink-0 group">
          <div className="flex items-center justify-center h-8 w-8 rounded-lg bg-blue-600 group-hover:bg-blue-700 transition-colors select-none">
            <span className="text-white font-bold text-xs">SG</span>
          </div>
          <span className="font-bold text-slate-900 text-sm hidden sm:block tracking-tight">
            BidScraper <span className="text-blue-600">Pro</span>
          </span>
        </Link>

        {/* Nav links */}
        <div className="hidden md:flex items-center gap-7">
          <Link href="/"      className={navLink(isHome)}>Home</Link>
          <Link href="/sam"   className={navLink(isSam)}>SAM.gov</Link>
          <Link href="/septa" className={navLink(isSepta)}>SEPTA</Link>
          <Link href="/naics" className={navLink(isNaics)}>NAICS</Link>
          <Link href="/#guide" className="text-sm font-medium text-slate-500 hover:text-slate-900 transition-colors">
            How It Works
          </Link>
        </div>

        {/* CTAs */}
        <div className="ml-auto flex items-center gap-2">
          <Link
            href="/sam"
            className="hidden sm:inline-flex items-center rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 px-3.5 py-2 text-xs font-semibold transition-colors"
          >
            SAM.gov Scraper
          </Link>
          <Link
            href="/septa"
            className="hidden sm:inline-flex items-center rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white px-3.5 py-2 text-xs font-semibold transition-colors"
          >
            SEPTA Scraper
          </Link>
          <Link
            href="/naics"
            className="inline-flex items-center rounded-lg bg-violet-600 hover:bg-violet-700 text-white px-3.5 py-2 text-xs font-semibold transition-colors"
          >
            NAICS Codes
          </Link>
        </div>
      </div>
    </nav>
  );
}
