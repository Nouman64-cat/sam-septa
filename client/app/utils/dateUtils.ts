/**
 * Date utilities shared across scraper forms.
 * All functions operate on strings in YYYY-MM-DD format (HTML date input value).
 */

const ISO_RE = /^\d{4}-\d{2}-\d{2}$/;

/** Return true when `value` is a non-empty, calendar-valid YYYY-MM-DD string. */
export function isValidDate(value: string): boolean {
  if (!value || !ISO_RE.test(value)) return false;
  const d = new Date(value);
  return !isNaN(d.getTime());
}

/**
 * Validate a from/to date range.
 * @returns An error string if validation fails, or `null` when everything is fine.
 */
export function validateDateRange(from: string, to: string): string | null {
  if (from && !isValidDate(from)) {
    return "From date is not a valid date.";
  }
  if (to && !isValidDate(to)) {
    return "To date is not a valid date.";
  }
  if (from && to && new Date(from) > new Date(to)) {
    return '"From" date cannot be later than "To" date.';
  }
  return null;
}

/** Return today's date as a YYYY-MM-DD string (local time). */
export function todayIso(): string {
  const d = new Date();
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

/** Describe the active filter mode in plain English for the UI hint. */
export function describeDateScenario(from: string, to: string): string {
  if (from && to) {
    return from === to
      ? `Exact day: ${from}`
      : `Range: ${from}  →  ${to}`;
  }
  if (from) return `From ${from} to today`;
  return "No date filter — all available bids";
}
