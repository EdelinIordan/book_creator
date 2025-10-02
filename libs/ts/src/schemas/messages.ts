import { z } from "zod";
import { AgentRole, BookStage, CritiqueSeverity } from "./enums";

const uuid = z.string().uuid();

export const CritiqueNote = z.object({
  id: uuid,
  severity: CritiqueSeverity.default("info"),
  summary: z.string().min(1).max(500),
  details: z.string().min(1),
  target_reference: z.string().min(1),
  applied: z.boolean().default(false),
});
export type CritiqueNote = z.infer<typeof CritiqueNote>;

export const AgentMessage = z.object({
  id: uuid,
  project_id: uuid,
  stage: BookStage,
  role: AgentRole,
  content: z.string().min(1),
  created_at: z.string().datetime(),
  critiques: z.array(CritiqueNote).default([]),
  resulting_artifact_ids: z.array(uuid).default([]),
});
export type AgentMessage = z.infer<typeof AgentMessage>;
