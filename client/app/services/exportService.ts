/**
 * Export service — triggers Excel downloads generated on-the-fly by the server
 * from DB data. No files are stored on disk; Excel is streamed per request.
 */

const BASE_URL =
  process.env.NEXT_PUBLIC_SERVER_URL?.replace(/\/$/, "") ??
  "http://127.0.0.1:8001";

/**
 * Download SAM bids as a styled Excel file.
 * @param jobId  If provided, exports only that job's bids.
 *               If omitted, exports the entire sam_bids table.
 */
export function exportSam(jobId?: string): void {
  const url = jobId
    ? `${BASE_URL}/export/sam?job_id=${encodeURIComponent(jobId)}`
    : `${BASE_URL}/export/sam`;
  _triggerDownload(url);
}

/**
 * Download SEPTA quotes as a styled Excel file.
 * @param jobId  If provided, exports only that job's quotes.
 *               If omitted, exports the entire septa_quotes table.
 */
export function exportSepta(jobId?: string): void {
  const url = jobId
    ? `${BASE_URL}/export/septa?job_id=${encodeURIComponent(jobId)}`
    : `${BASE_URL}/export/septa`;
  _triggerDownload(url);
}

/** Open a URL in a hidden anchor to trigger the browser's file-save dialog. */
function _triggerDownload(url: string): void {
  const a = document.createElement("a");
  a.href = url;
  a.rel  = "noopener noreferrer";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}
