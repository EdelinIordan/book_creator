import { useForm, Controller } from "react-hook-form";
import styles from "./ProviderForm.module.css";

export type ProviderFormValues = {
  provider: "openai" | "gemini";
  apiKey: string;
  model: string;
  temperature: number;
  maxOutputTokens?: number;
};

export function ProviderForm({
  defaultValues,
  onSubmit,
}: {
  defaultValues: ProviderFormValues;
  onSubmit: (values: ProviderFormValues) => void;
}) {
  const { control, handleSubmit } = useForm<ProviderFormValues>({ defaultValues });

  return (
    <form className={styles.form} onSubmit={handleSubmit(onSubmit)}>
      <h2>Provider Configuration</h2>
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
          rules={{ required: true }}
          render={({ field }) => <input type="password" {...field} />}
        />
      </label>
      <label>
        Model
        <Controller
          control={control}
          name="model"
          rules={{ required: true }}
          render={({ field }) => <input type="text" {...field} />}
        />
      </label>
      <label>
        Temperature
        <Controller
          control={control}
          name="temperature"
          render={({ field }) => (
            <input type="number" step="0.1" min={0} max={2} {...field} />
          )}
        />
      </label>
      <label>
        Max Output Tokens
        <Controller
          control={control}
          name="maxOutputTokens"
          render={({ field }) => <input type="number" min={16} {...field} />}
        />
      </label>
      <button type="submit">Save Settings</button>
    </form>
  );
}
