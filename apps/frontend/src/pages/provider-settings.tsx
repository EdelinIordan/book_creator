import { useState } from "react";
import { AppLayout } from "../layout/AppLayout";
import { ProviderLongForm, ProviderLongFormValues } from "../components/ProviderLongForm";
import styles from "./provider-settings.module.css";

const defaultConfig: ProviderLongFormValues = {
  provider: "openai",
  apiKey: "",
  defaultModel: "gpt-5-mini",
  defaultTemperature: 0.4,
  defaultTopP: 0.8,
  defaultReasoningEffort: "medium",
  defaultVerbosity: "medium",
  defaultThinkingBudget: 1024,
  defaultIncludeThoughts: false,
  agentOverrides: [
    {
      stage: "STRUCTURE",
      model: "gemini-2.5-pro",
      temperature: 0.3,
      topP: 0.7,
      thinkingBudget: 4096,
      includeThoughts: false,
    },
    {
      stage: "GUIDELINES",
      model: "gpt-5",
      temperature: 0.45,
      topP: 0.85,
      reasoningEffort: "high",
      verbosity: "high",
      maxOutputTokens: 8192,
    },
  ],
};

export default function ProviderSettingsPage() {
  const [config, setConfig] = useState(defaultConfig);
  const [status, setStatus] = useState<string>("");

  const handleSubmit = (values: ProviderLongFormValues) => {
    setConfig(values);
    setStatus("Settings saved locally. Backend integration coming soon.");
  };

  return (
    <AppLayout title="Provider Settings">
      <div className={styles.page}>
        <ProviderLongForm defaultValues={config} onSubmit={handleSubmit} />
        {status && (
          <p className={styles.status} role="status" aria-live="polite">
            {status}
          </p>
        )}
        <section className={styles.infoBox}>
          <h2>How this works</h2>
          <ol>
            <li>Enter API keys for OpenAI or Google Gemini.</li>
            <li>Choose default models and temperature for new runs.</li>
            <li>Override specific stages to use different models or caps.</li>
            <li>Coming soon: sync these settings to the backend via secure API.</li>
          </ol>
        </section>
      </div>
    </AppLayout>
  );
}
