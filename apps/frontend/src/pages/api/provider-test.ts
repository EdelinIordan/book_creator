import type { NextApiRequest, NextApiResponse } from "next";

const OPENAI_PROBE_URL = "https://api.openai.com/v1/models?limit=1";
const GEMINI_PROBE_URL = "https://generativelanguage.googleapis.com/v1beta/models?pageSize=1";

const REQUEST_TIMEOUT_MS = 10_000;

type ProviderType = "openai" | "gemini" | "mock";

type TestResponse = {
  ok: boolean;
  message?: string;
};

async function fetchWithTimeout(
  input: RequestInfo | URL,
  init: RequestInit = {},
  timeoutMs = REQUEST_TIMEOUT_MS
) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(input, { ...init, signal: controller.signal });
    return response;
  } finally {
    clearTimeout(timeout);
  }
}

async function testOpenAI(apiKey: string): Promise<TestResponse> {
  try {
    const response = await fetchWithTimeout(OPENAI_PROBE_URL, {
      headers: {
        Authorization: `Bearer ${apiKey}`,
      },
      method: "GET",
      cache: "no-store",
    });

    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      const message =
        (body as { error?: { message?: string } }).error?.message ??
        `OpenAI responded with status ${response.status}.`;
      return { ok: false, message };
    }

    return { ok: true, message: "OpenAI connection looks good." };
  } catch (error) {
    if ((error as Error).name === "AbortError") {
      return { ok: false, message: "OpenAI request timed out. Please try again." };
    }
    const message =
      error instanceof Error ? error.message : "Unknown network error while contacting OpenAI.";
    return { ok: false, message };
  }
}

async function testGemini(apiKey: string): Promise<TestResponse> {
  const url = `${GEMINI_PROBE_URL}&key=${encodeURIComponent(apiKey)}`;
  try {
    const response = await fetchWithTimeout(url, {
      method: "GET",
      cache: "no-store",
    });

    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      const message =
        ((body as { error?: { message?: string } }).error?.message ??
          `Gemini responded with status ${response.status}.`);
      return { ok: false, message };
    }

    return { ok: true, message: "Google Gemini connection looks good." };
  } catch (error) {
    if ((error as Error).name === "AbortError") {
      return { ok: false, message: "Google Gemini request timed out. Please try again." };
    }
    const message =
      error instanceof Error ? error.message : "Unknown network error while contacting Google Gemini.";
    return { ok: false, message };
  }
}

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<TestResponse | { error: string }>
) {
  if (req.method !== "POST") {
    res.setHeader("Allow", "POST");
    return res.status(405).json({ error: "Method not allowed" });
  }

  const { providerType, apiKey } = req.body as {
    providerType?: ProviderType;
    apiKey?: string;
  };

  if (!providerType || (providerType !== "openai" && providerType !== "gemini")) {
    return res.status(400).json({ error: "Unsupported provider type" });
  }

  if (!apiKey || typeof apiKey !== "string" || apiKey.trim().length === 0) {
    return res.status(400).json({ error: "API key is required" });
  }

  const trimmedKey = apiKey.trim();

  const result =
    providerType === "openai" ? await testOpenAI(trimmedKey) : await testGemini(trimmedKey);

  if (result.ok) {
    return res.status(200).json(result);
  }

  return res.status(200).json(result);
}
