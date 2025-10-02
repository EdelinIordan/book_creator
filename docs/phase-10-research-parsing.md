# Phase 10 – Research Parsing & Fact Mapping

## Objective
Transform uploaded Deep Research DOCX files into structured facts with citations and map them to every subchapter of the book through a tri-agent refinement loop, ensuring comprehensive, non-redundant coverage.

## Scope & Context
- Consumes DOCX outputs from Phase 9 and the book structure from Phase 5/7.
- Includes services for document ingestion, chunking, citation extraction, embedding, and retrieval for agents.
- Produces enriched structure entries with fact summaries and citation metadata required for emotional layering and writing stages.

## Current Implementation Snapshot
- `services/doc-parser` now exposes a `/parse` endpoint that decodes uploaded DOCX/base64 payloads, extracts paragraphs with `python-docx`, and returns normalized facts plus citation stubs.
- API uploads (`POST /projects/{id}/research/uploads`) accept base64 documents, persist files, call the parser, store fact candidates, and advance the project to the Fact Mapping stage once all prompts are covered.
- New persistence layer: `project_research_fact_candidates`, `project_research_facts`, and `project_fact_mapping` tables track candidates, finalized facts, coverage, and critiques.
- The Prefect flow handles `BookStage.FACT_MAPPING` via `fact_mapping.engine.generate_fact_mapping`, executing the M1→M3 agent loop and writing results back through `_store_fact_mapping_result`.
- `GET /projects/{id}/facts` surfaces mapped facts, coverage per subchapter, and the latest critique for downstream phases.

- DOCX parsing service (I0: Research Ingestor) converting documents to normalized Markdown/JSON, capturing source metadata (author, publication, URL, etc.).
- Fact store linked to subchapters with vector embeddings for semantic retrieval.
- Three-agent workflow per subchapter spanning M1: Fact Selector, M2: Fact Critic, and M3: Fact Implementer to assign facts, remove redundancy, and note missing coverage.
- UI enhancements showing fact assignments, citations, and redundancy warnings within the structure tree and library-level progress indicators for research integration.

## Milestones & Tasks
1. Build ingestion pipeline using chosen library (python-docx/docx2python) with error handling for malformed files.
2. Implement citation extraction heuristics or templates aligning with Phase 0 privacy and attribution requirements.
3. Integrate vector index (pgvector/Qdrant) for semantic search by agents during fact assignment.
4. Develop agent prompts ensuring every fact references specific sources and avoids duplication across subchapters.
5. Surface fact mapping in UI with controls to approve edits or flag conflicts.
6. Update library status to "Research Synthesised" once all subchapters have validated facts.

## Dependencies
- Research DOCX uploads from Phase 9.
- Structure data and schemas (Phases 2 & 5).
- Provider adapters (Phase 3) for agent reasoning.
- Frontend components (Phase 6) extended by Phase 7 structure UI.

## Risks & Mitigations
- **Risk**: Citation extraction fails for complex formatting.
  - *Mitigation*: Allow manual citation edits and provide fallback prompts asking agents to infer best-attributed source details.
- **Risk**: Large documents overwhelm processing pipeline.
  - *Mitigation*: Stream processing, chunking, and progress indicators with retry mechanisms.

## Exit Criteria
- Each subchapter contains a curated list of facts with citations and summary notes.
- Redundancy checks pass, highlighting any unresolved gaps for user intervention.
- Library dashboard shows research synthesis completed with timestamp and key stats (e.g., fact count).
- Data stored in Postgres/vector index and ready for emotional layer phase.

## Handoffs & Next Steps
- Provide enriched structure (facts + citations) to Phase 11 for emotional storytelling and to Phase 12/13 for creative guidelines and writing.
- Document known limitations in parsing for future enhancements.
