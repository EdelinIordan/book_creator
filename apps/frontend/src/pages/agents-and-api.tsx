import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { AppLayout } from "../layout/AppLayout";
import {
  loadProviderStore,
  saveProviderStore,
  ProviderSettingsStore,
  ProviderType,
  StoredProviderEntry,
  createProviderEntry,
  ProviderModelEntry,
  ReasoningEffort,
  VerbosityLevel,
} from "../lib/provider-storage";
import {
  AgentRuntimeConfig,
  AgentSettingsMap,
  loadAgentSettings,
  saveAgentSettings,
} from "../lib/agents-storage";
import { AGENT_ROSTER, AgentRosterItem } from "../lib/agents-roster";
import { BookStage } from "../types/stage";
import {
  AgentStageMetrics,
  fetchAgentStageMetrics,
} from "../lib/api";
import styles from "./agents-and-api.module.css";
import { createPortal } from "react-dom";

const PROVIDER_TYPE_OPTIONS: Array<{ value: ProviderType; label: string }> = [
  { value: "openai", label: "OpenAI" },
  { value: "gemini", label: "Google Gemini" },
  { value: "mock", label: "Mock" },
];

const STAGE_LABEL: Record<BookStage, string> = {
  IDEA: "Idea Intake",
  STRUCTURE: "Structure Lab",
  TITLE: "Title Hub",
  RESEARCH: "Research Dashboard",
  FACT_MAPPING: "Research Fact Map",
  EMOTIONAL: "Story Weave Lab",
  GUIDELINES: "Guideline Studio",
  WRITING: "Writing Studio",
  COMPLETE: "Ready to Publish",
};

const NAV_TABS: Array<{ id: "providers" | "catalog" | "roster"; label: string; blurb: string }> = [
  {
    id: "providers",
    label: "Providers",
    blurb: "Manage API credentials, defaults, and connection checks for OpenAI and Google Gemini.",
  },
  {
    id: "catalog",
    label: "Model Catalog",
    blurb: "Curate reusable model presets so teams can swap variants without hunting for IDs.",
  },
  {
    id: "roster",
    label: "Agent Roster",
    blurb: "Assign providers, models, and reasoning budgets to each stage-ready agent profile.",
  },
];

type PromptModalState = {
  agentId: string;
  agentName: string;
  systemDraft: string;
  userDraft: string;
  systemOriginal: string;
  userOriginal: string;
};

export default function AgentsAndApiPage() {
  const [providerStore, setProviderStore] = useState<ProviderSettingsStore | null>(null);
  const [agentSettings, setAgentSettings] = useState<AgentSettingsMap>({});
  const [loading, setLoading] = useState(true);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [stageMetrics, setStageMetrics] = useState<Record<string, AgentStageMetrics>>({});
  const [connectionStatus, setConnectionStatus] = useState<Record<string, "idle" | "testing" | "success" | "error">>({});
  const [modelDrafts, setModelDrafts] = useState<Record<string, { label: string; description: string }>>({});
  const [modelEditing, setModelEditing] = useState<Record<string, string | null>>({});
  const [activeTab, setActiveTab] = useState<"providers" | "catalog" | "roster">("providers");
  const [promptModal, setPromptModal] = useState<PromptModalState | null>(null);
  const [isClient, setIsClient] = useState(false);
  const promptSystemRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    setProviderStore(loadProviderStore());
    setAgentSettings(loadAgentSettings());
    setLoading(false);
  }, []);

  useEffect(() => {
    setIsClient(true);
  }, []);

  useEffect(() => {
    fetchAgentStageMetrics()
      .then((metrics) => setStageMetrics(metrics))
      .catch((error) => console.warn("Failed to load agent metrics", error));
  }, []);

  useEffect(() => {
    if (!promptModal) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setPromptModal(null);
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [promptModal]);

  useEffect(() => {
    if (promptModal && promptSystemRef.current) {
      promptSystemRef.current.focus({ preventScroll: true });
    }
  }, [promptModal]);

  useEffect(() => {
    if (!providerStore) return;
    setConnectionStatus((prev) => {
      const next: Record<string, "idle" | "testing" | "success" | "error"> = {};
      providerStore.providers
        .filter((provider) => provider.type !== "mock")
        .forEach((provider) => {
          next[provider.id] = prev[provider.id] ?? "idle";
        });
      return next;
    });
  }, [providerStore]);

  useEffect(() => {
    if (!providerStore) return;
    setModelDrafts((drafts) => {
      const next: Record<string, { label: string; description: string }> = {};
      providerStore.providers
        .filter((provider) => provider.type !== "mock")
        .forEach((provider) => {
          next[provider.id] = drafts[provider.id] ?? { label: "", description: "" };
        });
      return next;
    });
  }, [providerStore]);

  useEffect(() => {
    if (!providerStore) return;
    setModelEditing((prev) => {
      const next: Record<string, string | null> = {};
      providerStore.providers
        .filter((provider) => provider.type !== "mock")
        .forEach((provider) => {
          const current = prev[provider.id] ?? null;
          const exists = (provider.models ?? []).some((model) => model.id === current);
          next[provider.id] = exists ? current : null;
        });
      return next;
    });
  }, [providerStore]);

  const defaultProviderId = useMemo(() => {
    const store = providerStore ?? loadProviderStore();
    if (!store.providers.length) {
      const openai = createProviderEntry("openai");
      const gemini = createProviderEntry("gemini");
      const nextStore: ProviderSettingsStore = {
        schemaVersion: store.schemaVersion ?? 2,
        providers: [openai, gemini],
        defaultProviderId: openai.id,
      };
      setProviderStore(nextStore);
      saveProviderStore(nextStore);
      return openai.id;
    }
    return store.defaultProviderId ?? store.providers[0].id;
  }, [providerStore]);

  const deriveAgentDefaults = useCallback(
    (
      providerEntry: StoredProviderEntry | undefined,
      providerIdOverride?: string
    ): AgentRuntimeConfig => {
      const providerType = providerEntry?.type ?? "openai";
      const fallbackModel =
        providerType === "gemini"
          ? "gemini-2.5-pro"
          : providerType === "mock"
          ? "mock"
          : "gpt-5-mini";

      return {
        providerId: providerIdOverride ?? providerEntry?.id ?? defaultProviderId ?? "provider-openai",
        model: providerEntry?.defaultModel ?? fallbackModel,
      temperature: providerEntry?.defaultTemperature ?? 0.4,
      topP:
        providerEntry?.defaultTopP !== undefined
          ? providerEntry.defaultTopP
          : providerType === "mock"
          ? null
          : 0.8,
      maxOutputTokens: providerEntry?.maxOutputTokens,
      reasoningEffort:
        providerType === "openai"
          ? providerEntry?.defaultReasoningEffort ?? "medium"
          : "",
      verbosity:
        providerType === "openai"
          ? (providerEntry?.defaultVerbosity as VerbosityLevel | undefined) ?? "medium"
          : "",
      thinkingBudget:
        providerType === "gemini"
          ? providerEntry?.defaultThinkingBudget ?? 2048
          : null,
      includeThoughts:
        providerType === "gemini"
          ? providerEntry?.defaultIncludeThoughts ?? false
          : false,
      };
    },
    [defaultProviderId]
  );

  const groupedAgents = useMemo(() => {
    return AGENT_ROSTER.reduce<Record<BookStage, AgentRosterItem[]>>((acc, agent) => {
      if (!acc[agent.stage]) {
        acc[agent.stage] = [];
      }
      acc[agent.stage].push(agent);
      return acc;
    }, {
      IDEA: [],
      STRUCTURE: [],
      TITLE: [],
      RESEARCH: [],
      FACT_MAPPING: [],
      EMOTIONAL: [],
      GUIDELINES: [],
      WRITING: [],
      COMPLETE: [],
    });
  }, []);

  const rosterById = useMemo(() => {
    const map = new Map<string, AgentRosterItem>();
    AGENT_ROSTER.forEach((agent) => {
      map.set(agent.id, agent);
    });
    return map;
  }, []);

  const buildAgentDefaults = useCallback(
    (agentId: string, providerIdOverride?: string): AgentRuntimeConfig => {
      const rosterEntry = rosterById.get(agentId);
      const providerId = providerIdOverride ?? defaultProviderId;
      const providerEntry = providerStore?.providers.find((provider) => provider.id === providerId);
      const base = deriveAgentDefaults(providerEntry, providerId);
      return {
        ...base,
        systemPrompt: rosterEntry?.defaultSystemPrompt ?? "",
        userPrompt: rosterEntry?.defaultUserPrompt ?? "",
      };
    },
    [defaultProviderId, deriveAgentDefaults, providerStore, rosterById]
  );

  const handleProviderEntryChange = (
    providerId: string,
    field: keyof StoredProviderEntry,
    value: string | number | boolean | null | undefined
  ) => {
    setProviderStore((prev) => {
      if (!prev) return prev;
      const providers = prev.providers.map((provider) => {
        if (provider.id !== providerId) return provider;

        const nextEntry: StoredProviderEntry = {
          ...provider,
          [field]: value,
        } as StoredProviderEntry;

        if (field === "defaultModel" && typeof value === "string") {
          const trimmedValue = value.trim();
          if (trimmedValue.length > 0) {
            const models = provider.models ?? [];
            const exists = models.some((model) => model.label === trimmedValue);
            if (!exists) {
              const modelId = `model-${provider.type}-${Math.random().toString(36).slice(2, 10)}`;
              nextEntry.models = [
                {
                  id: modelId,
                  label: trimmedValue,
                  description: "Custom default",
                },
                ...models,
              ];
            }
          }
        }

        return nextEntry;
      });
      return { ...prev, providers };
    });
    if (field === "apiKey") {
      setConnectionStatus((prev) => ({ ...prev, [providerId]: "idle" }));
    }
  };

  const handleProviderSave = () => {
    if (providerStore) {
      saveProviderStore(providerStore);
      setStatusMessage("Provider settings saved locally.");
    }
  };

  const handleTestProviderConnection = async (providerId: string) => {
    if (!providerStore) return;
    const provider = providerStore.providers.find((entry) => entry.id === providerId);
    if (!provider) return;
    setConnectionStatus((prev) => ({ ...prev, [providerId]: "testing" }));
    await new Promise((resolve) => setTimeout(resolve, 700));
    const ok = provider.type === "mock" || provider.apiKey.trim().length >= 8;
    setConnectionStatus((prev) => ({ ...prev, [providerId]: ok ? "success" : "error" }));
  };

  const handleModelDraftChange = (
    providerId: string,
    field: "label" | "description",
    value: string
  ) => {
    setModelDrafts((prev) => ({
      ...prev,
      [providerId]: {
        ...prev[providerId],
        [field]: value,
      },
    }));
  };

  const handleStartEditModelEntry = (providerId: string, model: ProviderModelEntry) => {
    setModelDrafts((prev) => ({
      ...prev,
      [providerId]: {
        label: model.label,
        description: model.description ?? "",
      },
    }));
    setModelEditing((prev) => ({ ...prev, [providerId]: model.id }));
    setStatusMessage(`Editing ${model.label}`);
  };

  const handleCancelEditModelEntry = (providerId: string) => {
    setModelEditing((prev) => ({ ...prev, [providerId]: null }));
    setModelDrafts((prev) => ({ ...prev, [providerId]: { label: "", description: "" } }));
  };

  const handleSubmitModelEntry = (providerId: string) => {
    const draft = modelDrafts[providerId];
    const editingId = modelEditing[providerId];
    if (!draft) return;
    const label = draft.label.trim();
    if (!label) return;
    const description = draft.description.trim();

    let didUpdate = false;
    let status: string | null = null;

    setProviderStore((prev) => {
      if (!prev) return prev;
      const index = prev.providers.findIndex((provider) => provider.id === providerId);
      if (index === -1) return prev;
      const provider = prev.providers[index];
      const models = provider.models ?? [];

      if (!editingId) {
        const duplicate = models.some(
          (model) => model.label.toLowerCase() === label.toLowerCase()
        );
        if (duplicate) {
          status = "A model with this name already exists.";
          return prev;
        }
        const newModel: ProviderModelEntry = {
          id: `model-${provider.type}-${Math.random().toString(36).slice(2, 8)}`,
          label,
          description: description || undefined,
        };
        const nextProvider = {
          ...provider,
          models: [...models, newModel],
          defaultModel: provider.defaultModel || label,
        };
        const providers = [...prev.providers];
        providers[index] = nextProvider;
        const nextStore = { ...prev, providers };
        saveProviderStore(nextStore);
        didUpdate = true;
        status = "Model added.";
        return nextStore;
      }

      const currentModel = models.find((model) => model.id === editingId);
      if (!currentModel) {
        status = "Could not find model to edit.";
        return prev;
      }
      const duplicate = models.some(
        (model) => model.id !== editingId && model.label.toLowerCase() === label.toLowerCase()
      );
      if (duplicate) {
        status = "A model with this name already exists.";
        return prev;
      }
      const nextModels = models.map((model) =>
        model.id === editingId
          ? { ...model, label, description: description || undefined }
          : model
      );
      const nextProvider = {
        ...provider,
        models: nextModels,
        defaultModel:
          provider.defaultModel === currentModel.label ? label : provider.defaultModel,
      };
      const providers = [...prev.providers];
      providers[index] = nextProvider;
      const nextStore = { ...prev, providers };
      saveProviderStore(nextStore);
      didUpdate = true;
      status = "Model updated.";
      return nextStore;
    });

    if (status) {
      setStatusMessage(status);
    }
    if (didUpdate) {
      setModelEditing((prev) => ({ ...prev, [providerId]: null }));
      setModelDrafts((prev) => ({ ...prev, [providerId]: { label: "", description: "" } }));
    }
  };

  const handleRemoveModelEntry = (providerId: string, modelId: string) => {
    setProviderStore((prev) => {
      if (!prev) return prev;
      const index = prev.providers.findIndex((provider) => provider.id === providerId);
      if (index === -1) return prev;
      const provider = prev.providers[index];
      const models = provider.models ?? [];
      if (models.length <= 1) {
        setStatusMessage("Keep at least one model for each provider.");
        return prev;
      }
      const target = models.find((model) => model.id === modelId);
      if (!target) return prev;
      const remaining = models.filter((model) => model.id !== modelId);
      const nextProvider = {
        ...provider,
        models: remaining,
        defaultModel:
          provider.defaultModel === target.label
            ? remaining[0]?.label ?? provider.defaultModel
            : provider.defaultModel,
      };
      const providers = [...prev.providers];
      providers[index] = nextProvider;
      const nextStore = { ...prev, providers };
      saveProviderStore(nextStore);
      return nextStore;
    });
    setModelEditing((prev) => ({
      ...prev,
      [providerId]: prev[providerId] === modelId ? null : prev[providerId],
    }));
    if (modelEditing[providerId] === modelId) {
      setModelDrafts((prev) => ({ ...prev, [providerId]: { label: "", description: "" } }));
    }
  };

  const handleAgentConfigChange = (
    agentId: string,
    field: keyof AgentRuntimeConfig,
    value: string | number | boolean | null | undefined
  ) => {
    setAgentSettings((prev) => {
      const next: AgentSettingsMap = { ...prev };
      const existing = next[agentId] ?? buildAgentDefaults(agentId);
      next[agentId] = {
        ...existing,
        [field]: value,
      } as AgentRuntimeConfig;
      return next;
    });
  };

  const handleAgentProviderChange = (agentId: string, providerId: string) => {
    setAgentSettings((prev) => {
      const next: AgentSettingsMap = { ...prev };
      const previous = prev[agentId];
      const defaults = buildAgentDefaults(agentId, providerId);
      next[agentId] = {
        ...defaults,
        systemPrompt: previous?.systemPrompt ?? defaults.systemPrompt,
        userPrompt: previous?.userPrompt ?? defaults.userPrompt,
      };
      return next;
    });
  };

  useEffect(() => {
    if (!loading) {
      saveAgentSettings(agentSettings);
    }
  }, [agentSettings, loading]);

  useEffect(() => {
    if (!providerStore) return;
    const providerIds = new Set(providerStore.providers.map((provider) => provider.id));
    setAgentSettings((prev) => {
      const next: AgentSettingsMap = {};
      const normalizeNullableNumber = (value: number | null | undefined) =>
        value === undefined ? null : value;
      const isSameConfig = (a?: AgentRuntimeConfig, b?: AgentRuntimeConfig) => {
        if (!a || !b) return false;
        return (
          a.providerId === b.providerId &&
          a.model === b.model &&
          a.temperature === b.temperature &&
          normalizeNullableNumber(a.topP) === normalizeNullableNumber(b.topP) &&
          (a.reasoningEffort ?? "") === (b.reasoningEffort ?? "") &&
          (a.verbosity ?? "") === (b.verbosity ?? "") &&
          normalizeNullableNumber(a.thinkingBudget) ===
            normalizeNullableNumber(b.thinkingBudget) &&
          Boolean(a.includeThoughts) === Boolean(b.includeThoughts) &&
          normalizeNullableNumber(a.maxOutputTokens) ===
            normalizeNullableNumber(b.maxOutputTokens) &&
          (a.systemPrompt ?? "") === (b.systemPrompt ?? "") &&
          (a.userPrompt ?? "") === (b.userPrompt ?? "")
        );
      };

      let changed = false;
      for (const [agentId, config] of Object.entries(prev)) {
        if (providerIds.has(config.providerId)) {
          const providerEntry = providerStore.providers.find(
            (provider) => provider.id === config.providerId
          );
          const defaults = buildAgentDefaults(agentId, config.providerId);
          const updated: AgentRuntimeConfig = {
            ...defaults,
            ...config,
            topP:
              config.topP !== undefined ? config.topP : defaults.topP,
            thinkingBudget:
              config.thinkingBudget !== undefined
                ? config.thinkingBudget
                : defaults.thinkingBudget,
            systemPrompt: config.systemPrompt ?? defaults.systemPrompt,
            userPrompt: config.userPrompt ?? defaults.userPrompt,
          };
          next[agentId] = updated;
          if (!changed && !isSameConfig(config, updated)) {
            changed = true;
          }
        } else {
          next[agentId] = buildAgentDefaults(agentId);
          changed = true;
        }
      }
      if (!changed) {
        return prev;
      }
      return next;
    });
  }, [providerStore, buildAgentDefaults]);

  const handleResetAgents = () => {
    const defaults: AgentSettingsMap = {};
    AGENT_ROSTER.forEach((agent) => {
      defaults[agent.id] = buildAgentDefaults(agent.id);
    });
    setAgentSettings(defaults);
    saveAgentSettings(defaults);
    setStatusMessage("All agent configurations reset to defaults.");
  };

  const getAgentConfig = (agentId: string): AgentRuntimeConfig => {
    const stored = agentSettings[agentId];
    const defaults = buildAgentDefaults(agentId);
    if (!stored) {
      return defaults;
    }
    return {
      ...defaults,
      ...stored,
      systemPrompt: stored.systemPrompt ?? defaults.systemPrompt,
      userPrompt: stored.userPrompt ?? defaults.userPrompt,
    };
  };

  const handleOpenPromptModal = (agentId: string) => {
    const config = getAgentConfig(agentId);
    const rosterEntry = rosterById.get(agentId);
    setPromptModal({
      agentId,
      agentName: rosterEntry?.name ?? agentId,
      systemDraft: config.systemPrompt ?? "",
      userDraft: config.userPrompt ?? "",
      systemOriginal: config.systemPrompt ?? "",
      userOriginal: config.userPrompt ?? "",
    });
  };

  const handleClosePromptModal = () => {
    setPromptModal(null);
  };

  const handlePromptDraftChange = (field: "systemDraft" | "userDraft", value: string) => {
    setPromptModal((prev) => (prev ? { ...prev, [field]: value } : prev));
  };

  const handleRestorePromptDefaults = () => {
    setPromptModal((prev) => {
      if (!prev) return prev;
      const defaults = buildAgentDefaults(prev.agentId);
      return {
        ...prev,
        systemDraft: defaults.systemPrompt ?? "",
        userDraft: defaults.userPrompt ?? "",
      };
    });
  };

  const handleSavePrompts = () => {
    if (!promptModal) return;
    const { agentId, agentName, systemDraft, userDraft } = promptModal;
    setAgentSettings((prev) => {
      const next: AgentSettingsMap = { ...prev };
      const existing = next[agentId] ?? buildAgentDefaults(agentId);
      next[agentId] = {
        ...existing,
        systemPrompt: systemDraft,
        userPrompt: userDraft,
      };
      return next;
    });
    setStatusMessage(`Prompts updated for ${agentName}.`);
    setPromptModal(null);
  };

  const promptModalHasChanges = Boolean(
    promptModal &&
      (promptModal.systemDraft !== promptModal.systemOriginal ||
        promptModal.userDraft !== promptModal.userOriginal)
  );

  const providerOptions = (providerStore?.providers ?? [])
    .filter((provider) => provider.type !== "mock")
    .map((provider) => ({
      value: provider.id,
      label: provider.label,
    }));

  const renderProviderPanel = () => (
    <section className={styles.section}>
      <header className={styles.sectionHeader}>
        <div className={styles.sectionTitle}>
          <h2>Provider Credentials</h2>
          <p className={styles.sectionLead}>
            Store API keys and execution defaults for the providers your agents rely on. All credentials remain on this
            device.
          </p>
        </div>
        <div className={styles.sectionActions}>
          <button type="button" className={styles.secondaryButton} onClick={handleProviderSave}>
            Save provider settings
          </button>
        </div>
      </header>

      <div className={styles.tableWrapper}>
        <table className={styles.providerTable}>
          <thead>
            <tr>
              <th>Provider</th>
              <th>API key</th>
              <th>Connection</th>
            </tr>
          </thead>
          <tbody>
            {providerStore?.providers
              .filter((provider) => provider.type !== "mock")
              .map((provider) => {
                const status = connectionStatus[provider.id] ?? "idle";
                const statusLabel =
                  status === "success"
                    ? "Connected"
                    : status === "error"
                    ? "Failed"
                    : status === "testing"
                    ? "Testing…"
                    : "Unknown";
                return (
                  <tr key={provider.id}>
                    <td>
                      <div className={styles.providerInfo}>
                        <span className={styles.providerLabel}>{provider.label}</span>
                        <span className={styles.providerMeta}>
                          {provider.type === "gemini" ? "Google Gemini API" : "OpenAI API"}
                        </span>
                      </div>
                    </td>
                    <td>
                      <input
                        type="password"
                        className={styles.inputControl}
                        value={provider.apiKey}
                        onChange={(event) =>
                          handleProviderEntryChange(provider.id, "apiKey", event.target.value)
                        }
                        placeholder="sk-..."
                      />
                    </td>
                    <td className={styles.connectionCell}>
                      <span
                        className={`${styles.connectionBadge} ${
                          status === "success"
                            ? styles.connectionBadgeSuccess
                            : status === "error"
                            ? styles.connectionBadgeError
                            : status === "testing"
                            ? styles.connectionBadgeTesting
                            : styles.connectionBadgeIdle
                        }`}
                      >
                        {statusLabel}
                      </span>
                      <button
                        type="button"
                        className={styles.linkButton}
                        onClick={() => handleTestProviderConnection(provider.id)}
                        disabled={status === "testing"}
                      >
                        {status === "testing" ? "Testing…" : "Test"}
                      </button>
                    </td>
                  </tr>
                );
              })}
          </tbody>
        </table>
      </div>

      <p className={styles.helper}>
        Need help connecting to OpenAI or Gemini? See the <Link href="/provider-settings">legacy provider guide</Link>.
      </p>
    </section>
  );

  const renderModelCatalogPanel = () => (
    <section className={styles.section}>
      <header className={styles.sectionHeader}>
        <div className={styles.sectionTitle}>
          <h2>Model Catalog</h2>
          <p className={styles.sectionLead}>
            Keep a curated list of approved models per provider so teams can switch variants with confidence.
          </p>
        </div>
      </header>

      <div className={styles.modelsSection}>
        {providerStore?.providers
          .filter((provider) => provider.type !== "mock")
          .map((provider) => {
            const models = provider.models ?? [];
            const draft = modelDrafts[provider.id] ?? { label: "", description: "" };
            const editingId = modelEditing[provider.id];
            return (
              <article key={provider.id} className={styles.modelsCard}>
                <header className={styles.modelsHeader}>
                  <div>
                    <h3>{provider.label}</h3>
                    <p className={styles.modelsSubhead}>
                      {models.length} {models.length === 1 ? "model" : "models"} curated · Default {" "}
                      <span className={styles.modelsSubheadAccent}>{provider.defaultModel}</span>
                    </p>
                  </div>
                </header>
                <div className={styles.tableWrapper}>
                  <table className={styles.modelsTable}>
                    <thead>
                      <tr>
                        <th>Model</th>
                        <th className={styles.modelDescriptionHead}>Notes</th>
                        <th className={styles.modelActionsHead}>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {models.map((model) => {
                        const isEditing = editingId === model.id;
                        const isDefault = provider.defaultModel === model.label;
                        return (
                          <tr
                            key={model.id}
                            className={`${styles.modelRow} ${isEditing ? styles.modelRowEditing : ""}`}
                          >
                            <td>
                              <div className={styles.modelInfo}>
                                <span className={styles.modelLabel}>{model.label}</span>
                                {isDefault && <span className={styles.modelBadge}>Default</span>}
                              </div>
                            </td>
                            <td>
                              <p className={styles.modelDescription}>{model.description || "No description yet."}</p>
                            </td>
                            <td className={styles.modelActionGroup}>
                              <button
                                type="button"
                                className={`${styles.secondaryButton} ${styles.smallButton}`}
                                onClick={() => handleStartEditModelEntry(provider.id, model)}
                              >
                                {isEditing ? "Editing" : "Edit"}
                              </button>
                              <button
                                type="button"
                                className={`${styles.dangerButton} ${styles.smallButton}`}
                                onClick={() => handleRemoveModelEntry(provider.id, model.id)}
                                disabled={models.length <= 1}
                              >
                                Remove
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                      <tr className={styles.modelDraftRow}>
                        <td>
                          <input
                            type="text"
                            className={styles.inputControl}
                            placeholder="e.g. gpt-5-mini"
                            value={draft.label}
                            onChange={(event) => handleModelDraftChange(provider.id, "label", event.target.value)}
                          />
                        </td>
                        <td>
                          <input
                            type="text"
                            className={styles.inputControl}
                            placeholder="Optional description"
                            value={draft.description}
                            onChange={(event) =>
                              handleModelDraftChange(provider.id, "description", event.target.value)
                            }
                          />
                        </td>
                        <td className={styles.modelActionGroup}>
                          <button
                            type="button"
                            className={`${styles.secondaryButton} ${styles.smallButton}`}
                            onClick={() => handleSubmitModelEntry(provider.id)}
                            disabled={!draft.label.trim()}
                          >
                            {editingId ? "Update model" : "Add model"}
                          </button>
                          {editingId && (
                            <button
                              type="button"
                              className={`${styles.ghostButton} ${styles.smallButton}`}
                              onClick={() => handleCancelEditModelEntry(provider.id)}
                            >
                              Cancel
                            </button>
                          )}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </article>
            );
          })}
      </div>
    </section>
  );

  const renderRosterPanel = () => (
    <section className={styles.section}>
      <header className={styles.sectionHeader}>
        <div className={styles.sectionTitle}>
          <h2>Agent Roster</h2>
          <p className={styles.sectionLead}>
            Configure which provider, model, and reasoning style each workflow agent should use. Settings are stored
            locally and applied during orchestration runs.
          </p>
        </div>
        <div className={styles.sectionActions}>
          <button type="button" className={styles.ghostButton} onClick={handleResetAgents}>
            Reset all agents
          </button>
        </div>
      </header>

      {Object.entries(groupedAgents).map(([stage, agents]) => {
        if (agents.length === 0) return null;
        const metrics = stageMetrics[stage as BookStage];
        return (
          <div key={stage} className={styles.stageBlock}>
            <div className={styles.stageHeader}>
              <h3>{STAGE_LABEL[stage as BookStage]}</h3>
              {metrics && (
                <ul className={styles.metricList}>
                  <li>{`${Math.round(
                    (metrics.average_prompt_tokens ?? 0) + (metrics.average_completion_tokens ?? 0)
                  )} avg tokens`}</li>
                  <li>{`${metrics.average_latency_ms.toFixed(0)} ms avg latency`}</li>
                  <li>{`$${metrics.average_cost_usd.toFixed(4)} avg cost`}</li>
                </ul>
              )}
            </div>

            <div className={styles.agentGrid}>
              {agents.map((agent) => {
                const config = getAgentConfig(agent.id);
                const providerEntry = providerStore?.providers.find((provider) => provider.id === config.providerId);
                const providerType = providerEntry?.type ?? "openai";
                const models = providerEntry?.models ?? [];
                const fallbackModel = providerEntry?.defaultModel ?? config.model;
                const temperatureValue =
                  typeof config.temperature === "number"
                    ? config.temperature
                    : providerEntry?.defaultTemperature ?? 0.4;
                const inferredTopPDefault =
                  providerEntry?.defaultTopP !== undefined
                    ? providerEntry.defaultTopP
                    : providerType === "gemini"
                    ? 0.9
                    : 0.8;
                const topPUsesDefault = config.topP === null || config.topP === undefined;
                const topPValue = topPUsesDefault ? inferredTopPDefault : (config.topP as number);

                return (
                  <article key={agent.id} className={styles.agentCard}>
                    <header className={styles.agentCardHeader}>
                      <div className={styles.agentTitleBlock}>
                        <h4>{agent.name}</h4>
                        <p>{agent.description}</p>
                      </div>
                      <span className={styles.roleBadge}>{agent.role.replace(/_/g, " ")}</span>
                    </header>

                    <div className={styles.agentCardBody}>
                      <div className={styles.providerRow}>
                        <label className={styles.field}>
                          <span>Provider</span>
                          <select
                            className={styles.inputControl}
                            value={config.providerId}
                            onChange={(event) => handleAgentProviderChange(agent.id, event.target.value)}
                          >
                            {providerOptions.map((option) => (
                              <option key={option.value} value={option.value}>
                                {option.label}
                              </option>
                            ))}
                            {!providerOptions.some((option) => option.value === config.providerId) && (
                              <option value={config.providerId}>Unknown provider</option>
                            )}
                          </select>
                        </label>
                        <label className={styles.field}>
                          <span>Model</span>
                          <select
                            className={styles.inputControl}
                            value={config.model || fallbackModel || ""}
                            onChange={(event) => handleAgentConfigChange(agent.id, "model", event.target.value)}
                          >
                            {models.map((model) => (
                              <option key={model.id} value={model.label}>
                                {model.label}
                              </option>
                            ))}
                            {fallbackModel && !models.some((model) => model.label === fallbackModel) && (
                              <option value={fallbackModel}>{fallbackModel} (custom)</option>
                            )}
                          </select>
                        </label>
                      </div>

                      <div className={styles.sliderGroup}>
                        <div className={styles.sliderControl}>
                          <div className={styles.sliderLabel}>
                            <span>Temperature</span>
                            <span>{temperatureValue.toFixed(2)}</span>
                          </div>
                          <input
                            type="range"
                            min={0}
                            max={1.5}
                            step={0.05}
                            value={temperatureValue}
                            onChange={(event) =>
                              handleAgentConfigChange(agent.id, "temperature", Number(event.target.value))
                            }
                          />
                        </div>

                        <div className={styles.sliderControl}>
                          <div className={styles.sliderLabel}>
                            <span>Top P</span>
                            <span>{topPUsesDefault ? "Provider default" : topPValue.toFixed(2)}</span>
                          </div>
                          <input
                            type="range"
                            min={0}
                            max={1}
                            step={0.01}
                            value={topPValue}
                            disabled={topPUsesDefault}
                            onChange={(event) =>
                              handleAgentConfigChange(agent.id, "topP", Number(event.target.value))
                            }
                          />
                          <label className={styles.checkboxInline}>
                            <input
                              type="checkbox"
                              checked={topPUsesDefault}
                              onChange={(event) => {
                                const useDefault = event.target.checked;
                                if (useDefault) {
                                  handleAgentConfigChange(agent.id, "topP", null);
                                } else {
                                  handleAgentConfigChange(agent.id, "topP", inferredTopPDefault);
                                }
                              }}
                            />
                            Use provider default
                          </label>
                        </div>
                      </div>

                      <details className={styles.detailsBlock}>
                        <summary>Advanced provider controls</summary>
                        {providerType === "openai" ? (
                          <div className={styles.advancedGrid}>
                            <label className={styles.field}>
                              <span>Reasoning effort</span>
                              <select
                                className={styles.inputControl}
                                value={config.reasoningEffort ?? ""}
                                onChange={(event) =>
                                  handleAgentConfigChange(
                                    agent.id,
                                    "reasoningEffort",
                                    event.target.value as ReasoningEffort | ""
                                  )
                                }
                              >
                                <option value="">Provider default</option>
                                <option value="minimal">Minimal</option>
                                <option value="low">Low</option>
                                <option value="medium">Medium</option>
                                <option value="high">High</option>
                              </select>
                            </label>
                            <label className={styles.field}>
                              <span>Verbosity</span>
                              <select
                                className={styles.inputControl}
                                value={config.verbosity ?? ""}
                                onChange={(event) =>
                                  handleAgentConfigChange(
                                    agent.id,
                                    "verbosity",
                                    event.target.value as VerbosityLevel | ""
                                  )
                                }
                              >
                                <option value="">Provider default</option>
                                <option value="low">Low</option>
                                <option value="medium">Medium</option>
                                <option value="high">High</option>
                              </select>
                            </label>
                            <label className={styles.field}>
                              <span>Max output tokens</span>
                              <input
                                type="number"
                                className={styles.inputControl}
                                placeholder="Provider default"
                                value={config.maxOutputTokens ?? ""}
                                onChange={(event) => {
                                  const raw = event.target.value;
                                  handleAgentConfigChange(
                                    agent.id,
                                    "maxOutputTokens",
                                    raw === "" ? null : Number(raw)
                                  );
                                }}
                              />
                            </label>
                          </div>
                        ) : providerType === "gemini" ? (
                          <div className={styles.advancedGrid}>
                            <label className={styles.field}>
                              <span>Thinking budget</span>
                              <input
                                type="number"
                                className={styles.inputControl}
                                placeholder="Provider default"
                                value={config.thinkingBudget ?? ""}
                                onChange={(event) => {
                                  const raw = event.target.value;
                                  handleAgentConfigChange(
                                    agent.id,
                                    "thinkingBudget",
                                    raw === "" ? null : Number(raw)
                                  );
                                }}
                              />
                            </label>
                            <label className={styles.checkboxInline}>
                              <input
                                type="checkbox"
                                checked={Boolean(config.includeThoughts)}
                                onChange={(event) =>
                                  handleAgentConfigChange(agent.id, "includeThoughts", event.target.checked)
                                }
                              />
                              Include reasoning traces
                            </label>
                            <label className={styles.field}>
                              <span>Max output tokens</span>
                              <input
                                type="number"
                                className={styles.inputControl}
                                placeholder="Provider default"
                                value={config.maxOutputTokens ?? ""}
                                onChange={(event) => {
                                  const raw = event.target.value;
                                  handleAgentConfigChange(
                                    agent.id,
                                    "maxOutputTokens",
                                    raw === "" ? null : Number(raw)
                                  );
                                }}
                              />
                            </label>
                          </div>
                        ) : (
                          <p className={styles.muted}>Advanced controls not available for this provider.</p>
                        )}
                      </details>

                      <div className={styles.agentActions}>
                        <button
                          type="button"
                          className={styles.secondaryButton}
                          onClick={() => handleOpenPromptModal(agent.id)}
                        >
                          Edit prompts
                        </button>
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>
          </div>
        );
      })}
    </section>
  );

  const renderActivePanel = () => {
    switch (activeTab) {
      case "providers":
        return renderProviderPanel();
      case "catalog":
        return renderModelCatalogPanel();
      case "roster":
        return renderRosterPanel();
      default:
        return null;
    }
  };

  if (!providerStore) {
    return (
      <AppLayout title="Agents & API">
        <div className={styles.page}>
          <p role="status" aria-live="polite">Loading providers…</p>
        </div>
      </AppLayout>
    );
  }

  const activeTabMeta = NAV_TABS.find((tab) => tab.id === activeTab);

  return (
    <AppLayout title="Agents & API">
      <div className={styles.page}>
        <header className={styles.pageHeader}>
          <div className={styles.pageTitleBlock}>
            <h1>Agents & API</h1>
            <p className={styles.pageLead}>
              Configure the infrastructure that powers agent orchestration, from provider credentials to curated models and per-stage agent profiles.
            </p>
          </div>
          <nav className={styles.tabBar} role="tablist" aria-label="Agents & API sections">
            {NAV_TABS.map((tab) => (
              <button
                key={tab.id}
                type="button"
                role="tab"
                aria-selected={activeTab === tab.id}
                className={`${styles.tabButton} ${activeTab === tab.id ? styles.tabButtonActive : ""}`}
                onClick={() => setActiveTab(tab.id)}
              >
                {tab.label}
              </button>
            ))}
          </nav>
          {activeTabMeta && <p className={styles.tabDescription}>{activeTabMeta.blurb}</p>}
        </header>

        {statusMessage && (
          <div className={styles.statusBanner} role="status" aria-live="polite">
            {statusMessage}
          </div>
        )}

        {renderActivePanel()}
      </div>
      {isClient &&
        promptModal &&
        createPortal(
          <div
            className={styles.modalOverlay}
            role="presentation"
            onClick={(event) => {
              if (event.target === event.currentTarget) {
                handleClosePromptModal();
              }
            }}
          >
            <div
              className={`${styles.modal} ${styles.promptModal}`}
              role="dialog"
              aria-modal="true"
              aria-labelledby="prompt-editor-title"
              onClick={(event) => event.stopPropagation()}
            >
              <header className={styles.modalHeader}>
                <h2 id="prompt-editor-title">{promptModal.agentName} prompts</h2>
                <button
                  type="button"
                  className={styles.modalClose}
                  onClick={handleClosePromptModal}
                  aria-label="Close prompt editor"
                >
                  ×
                </button>
              </header>
              <div className={styles.modalBody}>
                <p className={styles.modalHelper}>
                  Adjust the system and user prompts for this agent. Changes are saved locally and applied on the next
                  run.
                </p>
                <div className={styles.modalGrid}>
                  <label>
                    <span>System prompt</span>
                    <textarea
                      ref={promptSystemRef}
                      className={styles.textArea}
                      rows={6}
                      value={promptModal.systemDraft}
                      onChange={(event) => handlePromptDraftChange("systemDraft", event.target.value)}
                    />
                  </label>
                  <label>
                    <span>User prompt</span>
                    <textarea
                      className={styles.textArea}
                      rows={8}
                      value={promptModal.userDraft}
                      onChange={(event) => handlePromptDraftChange("userDraft", event.target.value)}
                    />
                  </label>
                </div>
              </div>
              <footer className={styles.modalFooter}>
                <button type="button" className={styles.linkButton} onClick={handleRestorePromptDefaults}>
                  Restore defaults
                </button>
                <div className={styles.modalButtons}>
                  <button type="button" className={styles.ghostButton} onClick={handleClosePromptModal}>
                    Cancel
                  </button>
                  <button
                    type="button"
                    className={styles.primaryButton}
                    onClick={handleSavePrompts}
                    disabled={!promptModalHasChanges}
                  >
                    Save prompts
                  </button>
                </div>
              </footer>
            </div>
          </div>,
          document.body
        )}
    </AppLayout>
  );
}
