const STORAGE_KEY = "book-creator-provider-settings";
const CURRENT_SCHEMA_VERSION = 2;

export type ProviderType = "openai" | "gemini" | "mock";

export type ReasoningEffort = "minimal" | "low" | "medium" | "high";
export type VerbosityLevel = "low" | "medium" | "high";

export type StoredProviderEntry = {
  id: string;
  label: string;
  type: ProviderType;
  apiKey: string;
  defaultModel: string;
  defaultTemperature: number;
  defaultTopP?: number | null;
  defaultReasoningEffort?: ReasoningEffort | "";
  defaultVerbosity?: VerbosityLevel | "";
  defaultThinkingBudget?: number | null;
  defaultIncludeThoughts?: boolean;
  maxOutputTokens?: number;
  models: ProviderModelEntry[];
};

export type ProviderSettingsStore = {
  schemaVersion: number;
  providers: StoredProviderEntry[];
  defaultProviderId: string | null;
};

export type ProviderModelEntry = {
  id: string;
  label: string;
  description?: string;
};

const OPENAI_PRESET_MODELS: ProviderModelEntry[] = [
  {
    id: "model-openai-gpt5-mini",
    label: "gpt-5-mini",
    description: "Balanced GPT-5 default with 400k context and medium reasoning depth.",
  },
  {
    id: "model-openai-gpt5",
    label: "gpt-5",
    description: "Flagship reasoning model with maximum depth and reliability.",
  },
  {
    id: "model-openai-gpt5-nano",
    label: "gpt-5-nano",
    description: "Cost-optimised GPT-5 tier for lightweight narrative tasks.",
  },
  {
    id: "model-openai-gpt5-chat",
    label: "gpt-5-chat-latest",
    description: "ChatGPT parity router with auto tool selection and search.",
  },
];

const GEMINI_PRESET_MODELS: ProviderModelEntry[] = [
  {
    id: "model-gemini-25-pro",
    label: "gemini-2.5-pro",
    description: "Premium multimodal reasoning model (1M token context).",
  },
  {
    id: "model-gemini-25-flash",
    label: "gemini-2.5-flash",
    description: "Latency-optimised Gemini 2.5 with dynamic thinking support.",
  },
  {
    id: "model-gemini-15-pro",
    label: "gemini-1.5-pro",
    description: "Legacy fallback for quota hedging and backwards compatibility.",
  },
];

const LEGACY_DEFAULT: ProviderSettingsStore = {
  schemaVersion: CURRENT_SCHEMA_VERSION,
  providers: [
    {
      id: "provider-openai",
      label: "OpenAI",
      type: "openai",
      apiKey: "",
      defaultModel: "gpt-5-mini",
      defaultTemperature: 0.4,
      defaultTopP: 0.8,
      defaultReasoningEffort: "medium",
      defaultVerbosity: "medium",
      models: OPENAI_PRESET_MODELS,
    },
    {
      id: "provider-gemini",
      label: "Google Gemini",
      type: "gemini",
      apiKey: "",
      defaultModel: "gemini-2.5-pro",
      defaultTemperature: 0.35,
      defaultTopP: 0.8,
      defaultThinkingBudget: 2048,
      defaultIncludeThoughts: false,
      models: GEMINI_PRESET_MODELS,
    },
  ],
  defaultProviderId: "provider-openai",
};

function presetModelsFor(type: ProviderType): ProviderModelEntry[] {
  if (type === "openai") {
    return OPENAI_PRESET_MODELS;
  }
  if (type === "gemini") {
    return GEMINI_PRESET_MODELS;
  }
  return [];
}

function migrateDefaultModel(type: ProviderType, label: string): string {
  if (type === "openai") {
    if (label.startsWith("gpt-4")) {
      return "gpt-5-mini";
    }
    if (label === "gpt-5-chat") {
      return "gpt-5-chat-latest";
    }
  }
  if (type === "gemini") {
    if (label.startsWith("gemini-1.5")) {
      return "gemini-2.5-pro";
    }
    if (label === "gemini-pro" || label === "gemini-pro-1.5" || label === "gemini-pro-vision") {
      return "gemini-2.5-pro";
    }
  }
  return label;
}

function normalizeProviderEntry(provider: Partial<StoredProviderEntry>): StoredProviderEntry {
  const type = provider.type ?? "openai";
  const id = provider.id ?? generateId(type);
  const baseLabel =
    type === "gemini" ? "Google Gemini" : type === "mock" ? "Mock" : "OpenAI";

  const migratedDefaultModel = migrateDefaultModel(
    type,
    provider.defaultModel ?? defaultModelFor(type)
  );

  const defaultTemperature =
    provider.defaultTemperature ?? (type === "gemini" ? 0.35 : 0.4);
  const defaultTopP =
    provider.defaultTopP ?? (type === "mock" ? null : 0.8);

  const defaultReasoningEffort =
    type === "openai"
      ? (provider.defaultReasoningEffort && provider.defaultReasoningEffort !== ""
          ? provider.defaultReasoningEffort
          : "medium")
      : undefined;

  const defaultVerbosity =
    type === "openai"
      ? (provider.defaultVerbosity && provider.defaultVerbosity !== ""
          ? (provider.defaultVerbosity as VerbosityLevel)
          : "medium")
      : undefined;

  const defaultThinkingBudget =
    type === "gemini"
      ? provider.defaultThinkingBudget ?? 2048
      : undefined;

  const defaultIncludeThoughts =
    type === "gemini" ? Boolean(provider.defaultIncludeThoughts) : undefined;

  const normalizedModels = mergeModels(
    type,
    provider.models ?? [],
    migratedDefaultModel
  );

  return {
    id,
    label: provider.label ?? baseLabel,
    type,
    apiKey: provider.apiKey ?? "",
    defaultModel: migratedDefaultModel,
    defaultTemperature,
    defaultTopP,
    defaultReasoningEffort,
    defaultVerbosity,
    defaultThinkingBudget,
    defaultIncludeThoughts,
    maxOutputTokens: provider.maxOutputTokens,
    models: normalizedModels,
  };
}

function mergeModels(
  type: ProviderType,
  models: ProviderModelEntry[],
  defaultModel: string
): ProviderModelEntry[] {
  const initial = normalizeModels({ type, models, defaultModel });
  const existingLabels = new Set(initial.map((model) => model.label));
  const merged = [...initial];

  presetModelsFor(type).forEach((preset) => {
    if (!existingLabels.has(preset.label)) {
      merged.push({
        id: preset.id ?? generateModelId(type),
        label: preset.label,
        description: preset.description,
      });
    }
  });

  const seen = new Set<string>();
  const deduped = merged.filter((model) => {
    const key = model.label.trim().toLowerCase();
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });

  const defaultIndex = deduped.findIndex((model) => model.label === defaultModel);
  if (defaultIndex > 0) {
    const [entry] = deduped.splice(defaultIndex, 1);
    deduped.unshift(entry);
  }

  return deduped;
}

function normalizeStore(store: ProviderSettingsStore): ProviderSettingsStore {
  const allowedTypes: ProviderType[] = ["openai", "gemini"];
  const byType = new Map<ProviderType, StoredProviderEntry>();

  (store.providers ?? []).forEach((provider) => {
    const type = provider.type ?? "openai";
    if (!allowedTypes.includes(type)) return;
    byType.set(type, normalizeProviderEntry(provider));
  });

  allowedTypes.forEach((type) => {
    if (!byType.has(type)) {
      byType.set(type, normalizeProviderEntry(createProviderEntry(type)));
    }
  });

  const providers = allowedTypes
    .map((type) => byType.get(type)!)
    .filter(Boolean);

  const defaultProviderId = providers.some(
    (provider) => provider.id === store.defaultProviderId
  )
    ? store.defaultProviderId
    : providers[0]?.id ?? null;

  return {
    schemaVersion: CURRENT_SCHEMA_VERSION,
    providers,
    defaultProviderId,
  };
}

export function loadProviderStore(): ProviderSettingsStore {
  if (typeof window === "undefined") return LEGACY_DEFAULT;
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) return LEGACY_DEFAULT;
  try {
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed?.providers)) {
      const providers = parsed.providers.map(
        (provider: StoredProviderEntry, index: number) =>
          normalizeProviderEntry({
            ...provider,
            id: provider.id || `provider-${index}`,
          })
      );
      const store: ProviderSettingsStore = {
        schemaVersion:
          typeof parsed.schemaVersion === "number" ? parsed.schemaVersion : 1,
        providers,
        defaultProviderId:
          parsed.defaultProviderId ?? providers[0]?.id ?? "provider-openai",
      };
      return normalizeStore(store);
    }
    if (parsed?.provider) {
      const id = `provider-${parsed.provider}`;
      const store: ProviderSettingsStore = {
        schemaVersion: 1,
        providers: [
          normalizeProviderEntry({
            id,
            label: parsed.provider === "gemini" ? "Google Gemini" : "OpenAI",
            type: parsed.provider,
            apiKey: parsed.apiKey ?? "",
            defaultModel: parsed.defaultModel ?? undefined,
            defaultTemperature: parsed.defaultTemperature ?? undefined,
            maxOutputTokens: parsed.agentOverrides?.[0]?.maxOutputTokens,
            models: parsed.models ?? [],
          }),
        ],
        defaultProviderId: id,
      };
      return normalizeStore(store);
    }
  } catch (error) {
    console.warn("Failed to parse provider store", error);
  }
  return normalizeStore(LEGACY_DEFAULT);
}

export function saveProviderStore(store: ProviderSettingsStore) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(normalizeStore(store)));
}

function generateId(type: ProviderType): string {
  return `provider-${type}-${Math.random().toString(36).slice(2, 10)}`;
}

function generateModelId(type: ProviderType): string {
  return `model-${type}-${Math.random().toString(36).slice(2, 10)}`;
}

function defaultModelFor(type: ProviderType): string {
  if (type === "gemini") return "gemini-2.5-pro";
  if (type === "mock") return "mock";
  return "gpt-5-mini";
}

function normalizeModels(provider: Partial<StoredProviderEntry>): ProviderModelEntry[] {
  const type = provider.type ?? "openai";
  const fallback = provider.defaultModel ?? defaultModelFor(type);
  const models = Array.isArray(provider.models) ? provider.models : [];

  const normalized = models.map((model, index) => {
    const label = (model?.label ?? "").trim() || `${fallback}-${index}`;
    const description = model?.description?.trim();
    return {
      id: model?.id || generateModelId(type),
      label,
      description: description && description.length > 0 ? description : undefined,
    };
  });

  if (!normalized.some((model) => model.label === fallback)) {
    normalized.unshift({
      id: generateModelId(type),
      label: fallback,
    });
  }

  return normalized;
}

export function createProviderEntry(type: ProviderType): StoredProviderEntry {
  const id = generateId(type);
  const defaultModel = defaultModelFor(type);
  const entry = normalizeProviderEntry({
    id,
    label: type === "gemini" ? "Google Gemini" : type === "mock" ? "Mock" : "OpenAI",
    type,
    apiKey: "",
    defaultModel,
    models: presetModelsFor(type).map((model) => ({
      ...model,
      id: generateModelId(type),
    })),
  });
  return entry;
}
