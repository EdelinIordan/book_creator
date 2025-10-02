import type { ReasoningEffort, VerbosityLevel } from "./provider-storage";

const STORAGE_KEY = "book-creator-agent-settings";

export type AgentRuntimeConfig = {
  providerId: string;
  model: string;
  temperature: number;
  topP?: number | null;
  maxOutputTokens?: number;
  reasoningEffort?: ReasoningEffort | "";
  verbosity?: VerbosityLevel | "";
  thinkingBudget?: number | null;
  includeThoughts?: boolean;
  systemPrompt?: string;
  userPrompt?: string;
};

export type AgentSettingsMap = Record<string, AgentRuntimeConfig>;

export function loadAgentSettings(): AgentSettingsMap {
  if (typeof window === "undefined") return {};
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) return {};
  try {
    const parsed = JSON.parse(raw) as AgentSettingsMap;
    return parsed ?? {};
  } catch (error) {
    console.warn("Failed to parse agent settings", error);
    return {};
  }
}

export function saveAgentSettings(settings: AgentSettingsMap) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
}
