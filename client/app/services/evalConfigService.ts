import { get, post, del as apiDel } from "./api";

export interface EvalConfigData {
  kill_words:        string[];
  excluded_services: string[];
  allowed_services:  string[];
}

export async function getEvalConfig(): Promise<EvalConfigData> {
  return get<EvalConfigData>("/eval-config");
}

export async function addKillWord(value: string): Promise<void> {
  await post("/eval-config/kill-words", { value });
}

export async function deleteKillWord(value: string): Promise<void> {
  await apiDel(`/eval-config/kill-words/${encodeURIComponent(value)}`);
}

export async function addExcludedService(value: string): Promise<void> {
  await post("/eval-config/excluded-services", { value });
}

export async function deleteExcludedService(value: string): Promise<void> {
  await apiDel(`/eval-config/excluded-services/${encodeURIComponent(value)}`);
}

export async function addAllowedService(value: string): Promise<void> {
  await post("/eval-config/allowed-services", { value });
}

export async function deleteAllowedService(value: string): Promise<void> {
  await apiDel(`/eval-config/allowed-services/${encodeURIComponent(value)}`);
}
