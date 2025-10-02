import { z } from "zod";

export const BookStage = z.enum([
  "IDEA",
  "STRUCTURE",
  "TITLE",
  "RESEARCH",
  "FACT_MAPPING",
  "EMOTIONAL",
  "GUIDELINES",
  "WRITING",
  "COMPLETE",
]);
export type BookStage = z.infer<typeof BookStage>;

export const AgentRole = z.enum([
  "idea_generator",
  "structure_architect",
  "structure_critic_i",
  "structure_editor_i",
  "structure_critic_ii",
  "structure_editor_ii",
  "structure_critic_iii",
  "structure_editor_iii",
  "titler",
  "prompt_architect",
  "prompt_critic",
  "prompt_finalizer",
  "research_ingestor",
  "fact_selector",
  "fact_critic",
  "fact_implementer",
  "emotion_author",
  "emotion_critic",
  "emotion_implementer",
  "creative_director_assistant",
  "creative_director_critic",
  "creative_director_final",
  "writer_initial",
  "writing_critic_i",
  "writing_implementation_i",
  "writing_critic_ii",
  "writing_implementation_ii",
  "writing_critic_iii",
  "writing_implementation_iii",
]);
export type AgentRole = z.infer<typeof AgentRole>;

export const CritiqueSeverity = z.enum(["info", "warning", "error"]);
export type CritiqueSeverity = z.infer<typeof CritiqueSeverity>;

export const ResearchSourceType = z.enum([
  "academic_journal",
  "book",
  "government_report",
  "news_article",
  "expert_interview",
  "dataset",
  "other",
]);
export type ResearchSourceType = z.infer<typeof ResearchSourceType>;
