/**
 * File-download helpers.
 */

/**
 * Programmatically trigger a browser file download from a URL.
 * @param url               Full URL to the file.
 * @param suggestedFilename Optional filename for the saved file.
 */
export function triggerDownload(url: string, suggestedFilename?: string): void {
  const a = document.createElement("a");
  a.href = url;
  if (suggestedFilename) a.download = suggestedFilename;
  a.rel = "noopener noreferrer";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

/**
 * Extract the bare filename from a full or relative file path.
 * Works for both forward-slash and backslash separators.
 *
 * @example extractFilename("sam_output\\bids_20260318.csv") // "bids_20260318.csv"
 */
export function extractFilename(filePath: string): string {
  return filePath.replace(/\\/g, "/").split("/").pop() ?? filePath;
}
