import { Controller, useFieldArray, useForm, useWatch } from "react-hook-form";
import styles from "./ProviderLongForm.module.css";
import { ReasoningEffort, VerbosityLevel } from "../lib/provider-storage";
import { BookStage } from "../types/stage";

export type AgentSetting = {
  stage: BookStage;
  model: string;
  temperature: number;
  maxOutputTokens?: number;
  topP?: number | null;
  reasoningEffort?: ReasoningEffort | "";
  verbosity?: VerbosityLevel | "";
  thinkingBudget?: number | null;
  includeThoughts?: boolean;
};

export type ProviderLongFormValues = {
  provider: "openai" | "gemini";
  apiKey: string;
  defaultModel: string;
  defaultTemperature: number;
  defaultTopP?: number | null;
  defaultReasoningEffort?: ReasoningEffort | "";
  defaultVerbosity?: VerbosityLevel | "";
  defaultThinkingBudget?: number | null;
  defaultIncludeThoughts?: boolean;
  agentOverrides: AgentSetting[];
};

const WORKFLOW_STAGE_OPTIONS: Array<{ value: BookStage; label: string }> = [
  { value: "IDEA", label: "Idea Intake" },
  { value: "STRUCTURE", label: "Structure Lab" },
  { value: "TITLE", label: "Title Hub" },
  { value: "RESEARCH", label: "Research Dashboard" },
  { value: "FACT_MAPPING", label: "Research Fact Map" },
  { value: "EMOTIONAL", label: "Story Weave Lab" },
  { value: "GUIDELINES", label: "Guideline Studio" },
  { value: "WRITING", label: "Writing Studio" },
  { value: "COMPLETE", label: "Ready to Publish" },
];

export function ProviderLongForm({
  defaultValues,
  onSubmit,
}: {
  defaultValues: ProviderLongFormValues;
  onSubmit: (values: ProviderLongFormValues) => void;
}) {
  const { control, handleSubmit } = useForm<ProviderLongFormValues>({ defaultValues });
  const providerValue = useWatch({ control, name: "provider" });
  const overrideValues = useWatch({ control, name: "agentOverrides" });
  const { fields, append, remove } = useFieldArray({ control, name: "agentOverrides" });

  return (
    <form className={styles.form} onSubmit={handleSubmit(onSubmit)}>
      <header>
        <h1>LLM Provider Settings</h1>
        <p>Configure global defaults and override specific stages when needed.</p>
      </header>
      <section className={styles.section}>
        <h2>Default Provider</h2>
        <div className={styles.row}>
          <label>
            Provider
            <Controller
              control={control}
              name="provider"
              render={({ field }) => (
                <select {...field}>
                  <option value="openai">OpenAI</option>
                  <option value="gemini">Google Gemini</option>
                </select>
              )}
            />
          </label>
          <label>
            API Key
            <Controller
              control={control}
              name="apiKey"
              render={({ field }) => <input type="password" {...field} />}
            />
          </label>
        </div>
        <div className={styles.row}>
          <label>
            Default Model
            <Controller
              control={control}
              name="defaultModel"
              render={({ field }) => <input type="text" {...field} />}
            />
          </label>
          <label>
            Default Temperature
            <Controller
              control={control}
              name="defaultTemperature"
              render={({ field }) => (
                <input type="number" step="0.1" min={0} max={2} {...field} />
              )}
            />
          </label>
        </div>
        {providerValue === "openai" && (
          <div className={styles.row}>
            <label>
              Top P (optional)
              <Controller
                control={control}
                name="defaultTopP"
                render={({ field }) => (
                  <input
                    type="number"
                    step="0.05"
                    min={0}
                    max={1}
                    value={field.value ?? ""}
                    onChange={(event) => {
                      const value = event.target.value;
                      field.onChange(value === "" ? null : Number(value));
                    }}
                  />
                )}
              />
            </label>
            <label>
              Reasoning Effort
              <Controller
                control={control}
                name="defaultReasoningEffort"
                render={({ field }) => (
                  <select
                    {...field}
                    onChange={(event) =>
                      field.onChange(event.target.value as ReasoningEffort | "")
                    }
                  >
                    <option value="">Provider default</option>
                    <option value="minimal">Minimal</option>
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                  </select>
                )}
              />
            </label>
            <label>
              Verbosity
              <Controller
                control={control}
                name="defaultVerbosity"
                render={({ field }) => (
                  <select
                    {...field}
                    onChange={(event) =>
                      field.onChange(
                        event.target.value === ""
                          ? ""
                          : (event.target.value as "low" | "medium" | "high")
                      )
                    }
                  >
                    <option value="">Provider default</option>
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                  </select>
                )}
              />
            </label>
          </div>
        )}
        {providerValue === "gemini" && (
          <div className={styles.row}>
            <label>
              Thinking Budget (tokens)
              <Controller
                control={control}
                name="defaultThinkingBudget"
                render={({ field }) => (
                  <input
                    type="number"
                    step={1}
                    value={field.value ?? ""}
                    onChange={(event) => {
                      const value = event.target.value;
                      field.onChange(value === "" ? null : Number(value));
                    }}
                    placeholder="e.g., 1024 or -1 for dynamic"
                  />
                )}
              />
            </label>
            <label className={styles.checkboxRow}>
              <Controller
                control={control}
                name="defaultIncludeThoughts"
                render={({ field }) => (
                  <input
                    type="checkbox"
                    checked={Boolean(field.value)}
                    onChange={(event) => field.onChange(event.target.checked)}
                  />
                )}
              />
              Include thought summaries by default
            </label>
          </div>
        )}
      </section>

      <section className={styles.section}>
        <div className={styles.sectionHeader}>
          <h2>Stage Overrides</h2>
          <button
            type="button"
            onClick={() =>
              append({
                stage: "STRUCTURE",
                model: defaultValues.defaultModel,
                temperature: defaultValues.defaultTemperature,
                maxOutputTokens: undefined,
                topP: defaultValues.defaultTopP ?? null,
                reasoningEffort: defaultValues.defaultReasoningEffort ?? "",
                verbosity: defaultValues.defaultVerbosity ?? "",
                thinkingBudget: defaultValues.defaultThinkingBudget ?? null,
                includeThoughts: defaultValues.defaultIncludeThoughts ?? false,
              })
            }
          >
            Add Override
          </button>
        </div>
        {fields.length === 0 ? (
          <p className={styles.emptyState}>No overrides defined. All stages will use defaults.</p>
        ) : (
          <div className={styles.table}>
            {fields.map((field, index) => {
              const override = overrideValues?.[index];
              const modelValue = override?.model?.toLowerCase() ?? "";
              const isOpenAIModel = modelValue.includes("gpt-");
              const isGeminiModel = modelValue.includes("gemini");
              return (
                <div key={field.id} className={styles.tableRow}>
                  <label>
                    Stage
                    <Controller
                      control={control}
                      name={`agentOverrides.${index}.stage`}
                      render={({ field }) => (
                        <select {...field}>
                          {WORKFLOW_STAGE_OPTIONS.map((option) => (
                            <option key={option.value} value={option.value}>
                              {option.label}
                            </option>
                          ))}
                        </select>
                      )}
                    />
                  </label>
                  <label>
                    Model
                    <Controller
                      control={control}
                      name={`agentOverrides.${index}.model`}
                      render={({ field }) => <input type="text" {...field} />}
                    />
                  </label>
                  <label>
                    Temperature
                    <Controller
                      control={control}
                      name={`agentOverrides.${index}.temperature`}
                      render={({ field }) => (
                        <input type="number" step="0.1" min={0} max={2} {...field} />
                      )}
                    />
                  </label>
                  <label>
                    Max Output Tokens
                    <Controller
                      control={control}
                      name={`agentOverrides.${index}.maxOutputTokens`}
                      render={({ field }) => <input type="number" min={16} {...field} />}
                    />
                  </label>
                  <label>
                    Top P
                    <Controller
                      control={control}
                      name={`agentOverrides.${index}.topP`}
                      render={({ field }) => (
                        <input
                          type="number"
                          step={0.05}
                          min={0}
                          max={1}
                          value={field.value ?? ""}
                          onChange={(event) => {
                            const value = event.target.value;
                            field.onChange(value === "" ? null : Number(value));
                          }}
                        />
                      )}
                    />
                  </label>
                  {isOpenAIModel && (
                    <>
                      <label>
                        Reasoning Effort
                        <Controller
                          control={control}
                          name={`agentOverrides.${index}.reasoningEffort`}
                          render={({ field }) => (
                            <select
                              {...field}
                              onChange={(event) =>
                                field.onChange(event.target.value as ReasoningEffort | "")
                              }
                            >
                              <option value="">Default</option>
                              <option value="minimal">Minimal</option>
                              <option value="low">Low</option>
                              <option value="medium">Medium</option>
                              <option value="high">High</option>
                            </select>
                          )}
                        />
                      </label>
                      <label>
                        Verbosity
                        <Controller
                          control={control}
                          name={`agentOverrides.${index}.verbosity`}
                          render={({ field }) => (
                            <select
                              {...field}
                              onChange={(event) =>
                                field.onChange(
                                  event.target.value === ""
                                    ? ""
                                    : (event.target.value as "low" | "medium" | "high")
                                )
                              }
                            >
                              <option value="">Default</option>
                              <option value="low">Low</option>
                              <option value="medium">Medium</option>
                              <option value="high">High</option>
                            </select>
                          )}
                        />
                      </label>
                    </>
                  )}
                  {isGeminiModel && (
                    <>
                      <label>
                        Thinking Budget
                        <Controller
                          control={control}
                          name={`agentOverrides.${index}.thinkingBudget`}
                          render={({ field }) => (
                            <input
                              type="number"
                              step={1}
                              value={field.value ?? ""}
                              onChange={(event) => {
                                const value = event.target.value;
                                field.onChange(value === "" ? null : Number(value));
                              }}
                              placeholder="e.g., 2048 or -1"
                            />
                          )}
                        />
                      </label>
                      <label className={styles.checkboxRow}>
                        <Controller
                          control={control}
                          name={`agentOverrides.${index}.includeThoughts`}
                          render={({ field }) => (
                            <input
                              type="checkbox"
                              checked={Boolean(field.value)}
                              onChange={(event) => field.onChange(event.target.checked)}
                            />
                          )}
                        />
                        Include thoughts
                      </label>
                    </>
                  )}
                  <button type="button" onClick={() => remove(index)}>
                    Remove
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </section>

      <footer className={styles.footer}>
        <button type="submit">Save Configuration</button>
      </footer>
    </form>
  );
}
