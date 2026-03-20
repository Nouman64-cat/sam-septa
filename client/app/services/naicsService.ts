import { post } from "./api";
import type { JobStartResponse, NaicsListResponse } from "../types";

const BASE_URL =
  process.env.NEXT_PUBLIC_SERVER_URL?.replace(/\/$/, "") ??
  "http://127.0.0.1:8001";

export async function scrapeNaics(): Promise<JobStartResponse> {
  return post<Record<string, never>, JobStartResponse>("/scrape/naics", {});
}

export async function listNaics(page = 1, limit = 50): Promise<NaicsListResponse> {
  const res = await fetch(`${BASE_URL}/naics?page=${page}&limit=${limit}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function searchNaics(q: string, page = 1, limit = 50): Promise<NaicsListResponse> {
  const params = new URLSearchParams({ q, page: String(page), limit: String(limit) });
  const res = await fetch(`${BASE_URL}/naics/search?${params}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function getNaicsCount(): Promise<number> {
  const res = await fetch(`${BASE_URL}/naics?page=1&limit=1`);
  if (!res.ok) return 0;
  const data: NaicsListResponse = await res.json();
  return data.total;
}
