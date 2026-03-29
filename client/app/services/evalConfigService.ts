import { get, post, del as apiDel } from "./api";

export interface EvalConfigData {
  kill_words:    string[];
  allowed_states: string[];
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

export async function addAllowedState(value: string): Promise<void> {
  await post("/eval-config/allowed-states", { value });
}

export async function deleteAllowedState(value: string): Promise<void> {
  await apiDel(`/eval-config/allowed-states/${encodeURIComponent(value)}`);
}
