# Phase 9 – Research Prompt Pipeline

## Objective
Design the three-agent system that crafts, critiques, and finalises Deep Research prompts, guiding users to gather authoritative source material aligned with the book structure and user-provided 500-word research brief.

## Scope & Context
- Occurs after title selection; leverages structure and title context to shape research priorities.
- Produces three high-quality prompts via the R1 → R3 agent loop intended for external Deep Research tools (Gemini or ChatGPT web research).
- Manages user workflow for copying prompts, executing external research, and uploading resulting DOCX files back into the app.

- Agent prompts and logic for R1: Prompt Architect, R2: Prompt Critic, and R3: Prompt Finalizer. **Implemented via the research engine and Prefect stage integration.**
- Backend endpoints to request prompts, track status, register uploads, and update project stage metadata for the library. **Implemented in the FastAPI gateway.**
- Frontend Research Dashboard with copy-ready prompts, guideline editor, upload tracking, and automatic stage updates once uploads complete. **Implemented.**
- Validation checks ensuring prompts cover the breadth of chapters/subchapters and reference expected source types. **Schema-based validation exists; deeper semantic checks remain future work.**
- Upload handler now decodes base64 DOCX files, persists them under `storage/research_uploads/`, and immediately calls the doc-parser service so candidate facts are ready for Phase 10. **Implemented.**

## Milestones & Tasks
1. Implement agent trio using provider abstraction, referencing structure/topics and user research guidelines.
2. Store prompt history with rationales and critique notes for transparency.
3. Build upload pipeline to object storage (MinIO) with metadata linking documents to project and prompt ID.
4. Add UI cues reminding users to execute prompts externally and upload resulting DOCX files.
5. Validate that all three research documents are received before allowing Phase 10 to start, and sync completion back to the library view.

## Dependencies
- Final structure (Phase 5/7) and title (Phase 8).
- Provider adapters (Phase 3) for prompt generation and critique.
- Frontend infrastructure (Phase 6) for dashboard UI.
- Orchestrator (Phase 4) to manage stage completion status.

## Risks & Mitigations
- **Risk**: Prompts overlap excessively.
  - *Mitigation*: Critique agent enforces coverage map to spread focus across chapters and themes.
- **Risk**: Users forget to upload DOCX outputs.
  - *Mitigation*: Provide reminders, gating logic, and a checklist in the UI before unlocking Phase 10.

## Exit Criteria
- Users receive three actionable prompts with clear rationales and expected outcomes. **Delivered via `/projects/{id}/research`.**
- Upload metadata is recorded and DOCX files are stored under `storage/research_uploads/`; once every prompt has an upload the project advances to Fact Mapping, signalling readiness for Phase 10.
- Library dashboard reflects research status (stage badge updates from RESEARCH to FACT_MAPPING when uploads complete). **Implemented.**
- Stage emits critique text alongside prompts for transparency; richer event streaming for downstream services remains on the roadmap.

## Handoffs & Next Steps
- Expand upload handling to store actual files (currently metadata only) and hand off artefacts to Phase 10 for parsing and fact extraction.
- Provide automatic coverage summaries so Phase 10 agents understand scope and identify remaining gaps.
