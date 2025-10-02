import { BookStructure } from "../types/book";
import { BookStage, StageTimelineRole } from "../types/stage";

const PUBLIC_API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const INTERNAL_API_BASE_URL = process.env.API_INTERNAL_BASE_URL ?? PUBLIC_API_BASE_URL;

const API_BASE_URL = typeof window === "undefined" ? INTERNAL_API_BASE_URL : PUBLIC_API_BASE_URL;

export class AuthError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "AuthError";
  }
}

export class AuthorizationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "AuthorizationError";
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const config: RequestInit = {
    credentials: "include",
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {}),
    },
  };

  const response = await fetch(`${API_BASE_URL}${path}`, config);

  if (response.status === 401) {
    const message = await response.text();
    throw new AuthError(message || "Authentication required");
  }

  if (response.status === 403) {
    const message = await response.text();
    throw new AuthorizationError(message || "Not authorised");
  }

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed with status ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const text = await response.text();
  if (!text) {
    return undefined as T;
  }

  return JSON.parse(text) as T;
}

export type Category = {
  id: number;
  name: string;
  color_hex: string;
};

export type CategoryCreatePayload = {
  name: string;
  color_hex: string;
};

export type ProjectSummary = {
  id: string;
  title: string | null;
  stage: BookStage;
  stage_label: string;
  progress: number;
  idea_summary: string | null;
  research_guidelines: string | null;
  last_updated: string;
  category: Category | null;
  guidelines_ready: boolean;
  guideline_version: number | null;
  guideline_updated_at: string | null;
  writing_ready: boolean;
  writing_updated_at: string | null;
  total_cost_usd: number;
  spend_limit_usd: number | null;
  budget_remaining_usd: number | null;
  budget_status: "unlimited" | "ok" | "warning" | "exceeded";
};

export type StructureTimelineEntry = {
  id: string;
  role: StageTimelineRole;
  title: string;
  content: string;
  timestamp: string;
};

export type StructureDetail = {
  project: ProjectSummary;
  structure: BookStructure;
  summary: string;
  critiques: string[];
  iterations: StructureTimelineEntry[];
};

export type IdeaIntakePayload = {
  category_id: number | null;
  working_title?: string;
  description: string;
  research_guidelines?: string;
};

export type IdeaIntakeResult = {
  projectId: string;
  detail: StructureDetail;
};

export type TitleOption = {
  title: string;
  rationale: string;
};

export type TitleDetail = {
  project: ProjectSummary;
  options: TitleOption[];
  shortlist: string[];
  selected_title: string | null;
  critique: string | null;
  updated_at: string;
};

export type ResearchPrompt = {
  focus_summary: string;
  focus_subchapters: string[];
  prompt_text: string;
  desired_sources: string[];
  additional_notes: string | null;
};

export type ResearchUpload = {
  id: number;
  prompt_index: number;
  filename: string;
  storage_path: string;
  notes: string | null;
  uploaded_at: string;
};

export type ResearchUploadPayload = {
  prompt_index: number;
  filename: string;
  notes?: string;
  content_base64: string;
};

export type ResearchDetail = {
  project: ProjectSummary;
  prompts: ResearchPrompt[];
  critique: string | null;
  guidelines: string | null;
  uploads: ResearchUpload[];
};

export type FactCoverage = {
  subchapter_id: string;
  fact_count: number;
};

export type MappedFact = {
  id: string;
  subchapter_id: string;
  summary: string;
  detail: string;
  citation: FactCitation;
  upload_id: number | null;
  prompt_index: number | null;
  created_at: string;
};

export type FactMappingDetail = {
  project: ProjectSummary;
  facts: MappedFact[];
  coverage: FactCoverage[];
  critique: string | null;
  updated_at: string;
};

export type PersonaProfile = {
  name: string;
  background: string;
  voice: string;
  signature_themes: string[];
  guiding_principles: string[];
};

export type FactCitation = {
  source_title: string;
  author: string | null;
  publication_date: string | null;
  url: string | null;
  page: string | null;
  source_type: string | null;
};

export type EmotionalEntry = {
  id: string;
  subchapter_id: string;
  story_hook: string;
  persona_note: string | null;
  analogy: string | null;
  emotional_goal: string | null;
  created_by: string;
  created_at: string;
};

export type EmotionalLayerDetail = {
  project: ProjectSummary;
  persona: PersonaProfile;
  entries: EmotionalEntry[];
  critique: string | null;
  updated_at: string;
};

export type GuidelineFact = {
  fact_id: string;
  summary: string;
  citation: FactCitation;
  rationale: string | null;
};

export type GuidelinePacket = {
  id: string;
  subchapter_id: string;
  objectives: string[];
  must_include_facts: GuidelineFact[];
  emotional_beats: string[];
  narrative_voice: string | null;
  structural_reminders: string[];
  success_metrics: string[];
  risks: string[];
  status: string;
  created_by: string;
  version: number;
  created_at: string;
  updated_at: string;
};

export type GuidelineDetail = {
  project: ProjectSummary;
  summary: string | null;
  critique: string | null;
  readiness: string;
  version: number;
  guidelines: GuidelinePacket[];
  updated_at: string;
};

export type SessionUser = {
  id: string;
  email: string;
  role: string;
};

export type SessionResponse = {
  user: SessionUser;
};

export async function login(email: string, password: string): Promise<SessionResponse> {
  return request<SessionResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function logout(): Promise<void> {
  await request("/auth/logout", { method: "POST" });
}

export async function fetchSession(): Promise<SessionResponse> {
  return request<SessionResponse>("/auth/session");
}

export type DraftFeedback = {
  id: string;
  message: string;
  severity: string;
  category: string | null;
  rationale: string | null;
  addressed: boolean;
  addressed_in_iteration: string | null;
};

export type DraftIterationDetail = {
  id: string;
  project_id: string;
  subchapter_id: string;
  cycle: number;
  role: string;
  content: string;
  summary: string | null;
  word_count: number | null;
  feedback: DraftFeedback[];
  created_at: string;
};

export type SubchapterDraftState = {
  subchapter_id: string;
  title: string;
  chapter_title: string | null;
  order_label: string | null;
  current_cycle: number;
  status: "draft" | "in_review" | "ready";
  iterations: DraftIterationDetail[];
  outstanding_feedback: DraftFeedback[];
  final_iteration_id: string | null;
  final_word_count: number | null;
  last_updated: string;
};

export type WritingBatch = {
  project_id: string;
  cycle_count: number;
  readiness: "draft" | "ready";
  summary: string | null;
  total_word_count: number | null;
  subchapters: SubchapterDraftState[];
  created_at: string;
  updated_at: string;
};

export type WritingDetail = {
  project: ProjectSummary;
  batch: WritingBatch;
  critique: string | null;
};

export type AgentStageMetrics = {
  average_prompt_tokens: number;
  average_completion_tokens: number;
  average_latency_ms: number;
  average_cost_usd: number;
  runs: number;
};

export async function fetchCategories(): Promise<Category[]> {
  return request<Category[]>("/categories");
}

export async function createCategory(payload: CategoryCreatePayload): Promise<Category> {
  return request<Category>("/categories", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function fetchProjects(): Promise<ProjectSummary[]> {
  return request<ProjectSummary[]>("/projects");
}

export async function deleteProject(projectId: string): Promise<void> {
  await request(`/projects/${projectId}`, {
    method: "DELETE",
  });
}

export async function createProject(payload: IdeaIntakePayload): Promise<IdeaIntakeResult> {
  const result = await request<{ project_id: string; structure: StructureDetail }>("/projects", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return { projectId: result.project_id, detail: result.structure };
}

export async function fetchStructure(projectId: string): Promise<StructureDetail> {
  return request<StructureDetail>(`/projects/${projectId}/structure`);
}

export async function regenerateStructure(projectId: string): Promise<StructureDetail> {
  return request<StructureDetail>(`/projects/${projectId}/structure/regenerate`, {
    method: "POST",
  });
}

export async function approveStructure(projectId: string): Promise<ProjectSummary> {
  const result = await request<{ project: ProjectSummary }>(
    `/projects/${projectId}/structure/approve`,
    {
      method: "POST",
    }
  );
  return result.project;
}

export async function fetchTitles(projectId: string): Promise<TitleDetail> {
  return request<TitleDetail>(`/projects/${projectId}/titles`);
}

export async function regenerateTitles(projectId: string): Promise<TitleDetail> {
  return request<TitleDetail>(`/projects/${projectId}/titles/regenerate`, {
    method: "POST",
  });
}

export async function updateTitleShortlist(projectId: string, shortlist: string[]): Promise<TitleDetail> {
  return request<TitleDetail>(`/projects/${projectId}/titles/shortlist`, {
    method: "POST",
    body: JSON.stringify({ shortlist }),
  });
}

export async function selectTitle(projectId: string, title: string): Promise<TitleDetail> {
  return request<TitleDetail>(`/projects/${projectId}/titles/select`, {
    method: "POST",
    body: JSON.stringify({ title }),
  });
}

export async function fetchResearch(projectId: string): Promise<ResearchDetail> {
  return request<ResearchDetail>(`/projects/${projectId}/research`);
}

export async function regenerateResearch(
  projectId: string,
  guidelines?: string | null
): Promise<ResearchDetail> {
  return request<ResearchDetail>(`/projects/${projectId}/research/regenerate`, {
    method: "POST",
    body: JSON.stringify({ guidelines }),
  });
}

export async function registerResearchUpload(
  projectId: string,
  payload: ResearchUploadPayload
): Promise<ResearchDetail> {
  return request<ResearchDetail>(`/projects/${projectId}/research/uploads`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function fetchEmotionalLayer(projectId: string): Promise<EmotionalLayerDetail> {
  return request<EmotionalLayerDetail>(`/projects/${projectId}/emotional`);
}

export async function fetchFactMapping(projectId: string): Promise<FactMappingDetail> {
  return request<FactMappingDetail>(`/projects/${projectId}/facts`);
}

export async function regenerateEmotionalLayer(
  projectId: string,
  personaPreferences?: string | null
): Promise<EmotionalLayerDetail> {
  return request<EmotionalLayerDetail>(`/projects/${projectId}/emotional/regenerate`, {
    method: "POST",
    body: JSON.stringify({ persona_preferences: personaPreferences ?? null }),
  });
}

export async function fetchGuidelines(projectId: string): Promise<GuidelineDetail> {
  return request<GuidelineDetail>(`/projects/${projectId}/guidelines`);
}

export async function regenerateGuidelines(
  projectId: string,
  preferences?: string | null
): Promise<GuidelineDetail> {
  return request<GuidelineDetail>(`/projects/${projectId}/guidelines/regenerate`, {
    method: "POST",
    body: JSON.stringify({ preferences: preferences ?? null }),
  });
}

export async function fetchWriting(projectId: string): Promise<WritingDetail> {
  return request<WritingDetail>(`/projects/${projectId}/writing`);
}

export async function runWriting(
  projectId: string,
  notes?: string | null
): Promise<WritingDetail> {
  return request<WritingDetail>(`/projects/${projectId}/writing/run`, {
    method: "POST",
    body: JSON.stringify({ notes: notes ?? null }),
  });
}

export async function updateProjectBudget(
  projectId: string,
  spendLimitUsd: number | null
): Promise<ProjectSummary> {
  return request<ProjectSummary>(`/projects/${projectId}/budget`, {
    method: "PATCH",
    body: JSON.stringify({ spend_limit_usd: spendLimitUsd }),
  });
}

export async function fetchAgentStageMetrics(): Promise<Record<string, AgentStageMetrics>> {
  return request<Record<string, AgentStageMetrics>>("/stats/agent-stage");
}
