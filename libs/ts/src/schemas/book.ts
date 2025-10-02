import { z } from "zod";
import { AgentRole, BookStage, CritiqueSeverity, ResearchSourceType } from "./enums";

const uuid = z.string().uuid();

export const IdeaBrief = z.object({
  project_id: uuid,
  working_title: z.string().max(150).nullable().optional(),
  description: z.string().min(1),
  audience: z.string().max(200).nullable().optional(),
  goals: z.array(z.string()).default([]),
  created_at: z.string().datetime(),
});
export type IdeaBrief = z.infer<typeof IdeaBrief>;

export const Subchapter = z.object({
  id: uuid,
  title: z.string().min(1).max(200),
  summary: z.string().min(1).max(1000),
  order: z.number().int().min(1),
  learning_objectives: z.array(z.string()).default([]),
  related_subchapters: z.array(uuid).default([]),
});
export type Subchapter = z.infer<typeof Subchapter>;

export const Chapter = z.object({
  id: uuid,
  title: z.string().min(1).max(200),
  summary: z.string().min(1).max(1200),
  order: z.number().int().min(1),
  subchapters: z.array(Subchapter),
  narrative_arc: z.string().max(1000).nullable().optional(),
});
export type Chapter = z.infer<typeof Chapter>;

export const BookStructure = z.object({
  project_id: uuid,
  version: z.number().int().min(1).default(1),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
  chapters: z.array(Chapter),
  synopsis: z.string().max(2000).nullable().optional(),
});
export type BookStructure = z.infer<typeof BookStructure>;

export const ResearchPrompt = z.object({
  id: uuid,
  project_id: uuid,
  focus_subchapters: z.array(uuid).default([]),
  prompt_text: z.string().min(1),
  desired_sources: z.array(ResearchSourceType).default([]),
  additional_notes: z.string().max(1000).nullable().optional(),
  created_by: AgentRole,
  created_at: z.string().datetime(),
});
export type ResearchPrompt = z.infer<typeof ResearchPrompt>;

export const Citation = z.object({
  source_title: z.string().min(1),
  author: z.string().nullable().optional(),
  publication_date: z.string().nullable().optional(),
  url: z.string().url().max(400).nullable().optional(),
  page: z.string().nullable().optional(),
  source_type: ResearchSourceType.default("other"),
});
export type Citation = z.infer<typeof Citation>;

export const ResearchFact = z.object({
  id: uuid,
  project_id: uuid,
  subchapter_id: uuid,
  summary: z.string().min(1).max(800),
  detail: z.string().min(1),
  citation: Citation,
  redundancy_key: z.string().nullable().optional(),
  created_at: z.string().datetime(),
});
export type ResearchFact = z.infer<typeof ResearchFact>;

export const PersonaProfile = z.object({
  name: z.string().min(1).max(120),
  background: z.string().min(1).max(1500),
  voice: z.string().min(1).max(600),
  signature_themes: z.array(z.string()).default([]),
  guiding_principles: z.array(z.string()).default([]),
  created_at: z.string().datetime(),
});
export type PersonaProfile = z.infer<typeof PersonaProfile>;

export const EmotionalLayerEntry = z.object({
  id: uuid,
  project_id: uuid,
  subchapter_id: uuid,
  story_hook: z.string().min(1).max(1500),
  persona_note: z.string().max(500).nullable().optional(),
  analogy: z.string().max(1000).nullable().optional(),
  emotional_goal: z.string().max(400).nullable().optional(),
  created_by: AgentRole,
  created_at: z.string().datetime(),
});
export type EmotionalLayerEntry = z.infer<typeof EmotionalLayerEntry>;

export const EmotionalLayerBatch = z.object({
  project_id: uuid,
  persona: PersonaProfile,
  entries: z.array(EmotionalLayerEntry).default([]),
  created_at: z.string().datetime(),
});
export type EmotionalLayerBatch = z.infer<typeof EmotionalLayerBatch>;

export const GuidelineFactReference = z.object({
  fact_id: uuid,
  summary: z.string().min(1).max(600),
  citation: Citation,
  rationale: z.string().max(400).nullable().optional(),
});
export type GuidelineFactReference = z.infer<typeof GuidelineFactReference>;

const guidelineStatus = z.enum(["draft", "final", "needs_review"]);
const guidelineReadiness = z.enum(["draft", "ready"]);

export const CreativeGuideline = z.object({
  id: uuid,
  project_id: uuid,
  subchapter_id: uuid,
  objectives: z.array(z.string()).min(1),
  must_include_facts: z.array(GuidelineFactReference).default([]),
  emotional_beats: z.array(z.string()).default([]),
  narrative_voice: z.string().max(400).nullable().optional(),
  structural_reminders: z.array(z.string()).default([]),
  success_metrics: z.array(z.string()).default([]),
  risks: z.array(z.string()).default([]),
  status: guidelineStatus.default("final"),
  created_by: AgentRole,
  version: z.number().int().min(1).default(1),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
  approved_at: z.string().datetime().nullable().optional(),
});
export type CreativeGuideline = z.infer<typeof CreativeGuideline>;

export const CreativeGuidelineBatch = z.object({
  project_id: uuid,
  version: z.number().int().min(1).default(1),
  summary: z.string().max(2000).nullable().optional(),
  readiness: guidelineReadiness.default("draft"),
  guidelines: z.array(CreativeGuideline).default([]),
  created_at: z.string().datetime(),
  approved_at: z.string().datetime().nullable().optional(),
});
export type CreativeGuidelineBatch = z.infer<typeof CreativeGuidelineBatch>;

export const DraftVersion = z.object({
  id: uuid,
  project_id: uuid,
  subchapter_id: uuid,
  version_index: z.number().int().min(0),
  role: AgentRole,
  content: z.string().min(1),
  linked_critiques: z.array(uuid).default([]),
  created_at: z.string().datetime(),
});
export type DraftVersion = z.infer<typeof DraftVersion>;

export const ProjectProgressSnapshot = z.object({
  project_id: uuid,
  stage: BookStage,
  percent_complete: z.number().min(0).max(100),
  completed_stages: z.array(BookStage).default([]),
  total_subchapters: z.number().int().min(0),
  completed_subchapters: z.number().int().min(0),
  updated_at: z.string().datetime(),
});
export type ProjectProgressSnapshot = z.infer<typeof ProjectProgressSnapshot>;

export const DraftFeedbackItem = z.object({
  id: uuid,
  message: z.string().min(1).max(600),
  severity: CritiqueSeverity.default("warning"),
  category: z.string().max(100).nullable().optional(),
  rationale: z.string().max(600).nullable().optional(),
  addressed: z.boolean().default(false),
  addressed_in_iteration: uuid.nullable().optional(),
});
export type DraftFeedbackItem = z.infer<typeof DraftFeedbackItem>;

export const DraftIteration = z.object({
  id: uuid,
  project_id: uuid,
  subchapter_id: uuid,
  cycle: z.number().int().min(0),
  role: AgentRole,
  content: z.string().min(1),
  summary: z.string().max(600).nullable().optional(),
  word_count: z.number().int().min(0).nullable().optional(),
  feedback: z.array(DraftFeedbackItem).default([]),
  created_at: z.string().datetime(),
});
export type DraftIteration = z.infer<typeof DraftIteration>;

const writingStatus = z.enum(["draft", "in_review", "ready"]);

export const SubchapterDraftState = z.object({
  subchapter_id: uuid,
  title: z.string().min(1).max(200),
  chapter_title: z.string().max(200).nullable().optional(),
  order_label: z.string().nullable().optional(),
  current_cycle: z.number().int().min(0).default(0),
  status: writingStatus.default("draft"),
  iterations: z.array(DraftIteration).default([]),
  outstanding_feedback: z.array(DraftFeedbackItem).default([]),
  final_iteration_id: uuid.nullable().optional(),
  final_word_count: z.number().int().min(0).nullable().optional(),
  last_updated: z.string().datetime(),
});
export type SubchapterDraftState = z.infer<typeof SubchapterDraftState>;

export const WritingBatch = z.object({
  project_id: uuid,
  cycle_count: z.number().int().min(1).max(5).default(3),
  readiness: z.enum(["draft", "ready"]).default("draft"),
  summary: z.string().max(2000).nullable().optional(),
  subchapters: z.array(SubchapterDraftState).default([]),
  total_word_count: z.number().int().min(0).nullable().optional(),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
});
export type WritingBatch = z.infer<typeof WritingBatch>;
