# Phase 0 – Foundations

## Product Vision
- Deliver a local-first assistant that orchestrates a seven-stage AI workflow to produce high-quality non-fiction books from an initial 100-word idea through structure design, research synthesis, emotional layering, and multi-pass writing.
- Provide transparent, controllable progress so authors can supervise every agent exchange, accept or revise outputs, and maintain citation integrity across chapters and subchapters.
- Offer a smart library experience where projects are organised by user-defined categories (e.g., History, Psychology, Popular Science, Health) with at-a-glance tracking of stage progress, completed manuscripts, and in-flight ideas.
- Run entirely via Docker on the user’s machine, minimising cloud dependencies while still leveraging Gemini 2.5 Pro or ChatGPT 5 for reasoning and critique loops.

## Target Users & Personas
- **Solo Non-fiction Author**: domain expert who needs consistent structure, rigorous research, and engaging storytelling without hiring a large editorial staff.
- **Editorial Lead / Creative Director**: professional overseeing tone, narrative cohesion, and brand alignment across books created with the platform.
- **Research Consultant**: user who prepares Deep Research briefs and uploads findings, ensuring sources are reputable and citations remain accurate.

## Success Metrics
| Metric Type | Definition | Why it Matters |
| --- | --- | --- |
| Workflow Completion Rate | Percentage of projects that progress from idea intake through final manuscript export without manual recovery. | Validates reliability of the seven-stage orchestrated process. |
| Structure Iteration Satisfaction | Post-structure user rating (1–5 scale) on clarity and cohesion of generated chapter outlines. | Ensures the multi-agent critique cycle produces usable scaffolds. |
| Research Coverage Score | Automated check measuring percentage of extracted facts mapped to subchapters with citations. | Confirms Deep Research integration prevents missing or duplicate facts. |
| Emotional Engagement Score | User or reviewer rating on persona stories, analogies, and tone coherence. | Verifies emotional layer agents add value beyond factual accuracy. |
| Draft Acceptance Latency | Median time from writer agent output to user approval per subchapter. | Surfaces friction in the seven-step writing loop and UI. |
| Cost per Book | Total LLM spend per completed manuscript, tracked per provider configuration. | Keeps the local-first solution economically viable. |
| Library Visibility Index | Percentage of projects with accurate category tagging and up-to-date stage status within the dashboard. | Demonstrates the library UX helps users manage pipelines across multiple books. |

## Agent Roster Alignment
- **Phase 1 — Ideation**: A1 Idea Generator captures or expands the initial 100-word brief.
- **Phase 2 — Structure**: S1–S7 agents iterate from initial outline to `structure_final`, alternating proposal, critique, and implementation.
- **Phase 3 — Title Selection**: T1 Titler surfaces five options per batch with rationales for user approval.
- **Phase 4 — Research Foundation**: R1–R3 craft, critique, and finalise Deep Research prompts for external execution.
- **Phase 5 — Research Parsing**: I0 ingests DOCX findings while M1–M3 assign, critique, and finalise fact coverage at the subchapter level.
- **Phase 6 — Emotional Layer**: E1–E3 generate, critique, and commit persona-driven stories tied to citations and continuity.
- **Phase 7 — Proper Writing**: G1–G3 compile creative director guidelines; W1–W7 execute the drafting, critique, and implementation loop that delivers publication-ready subchapters.

## Non-Goals & Known Constraints
- The app does not scrape the web itself; all external research happens through user-triggered Deep Research tools, then uploaded as DOCX.
- Real-time collaborative editing is out of scope for v1; single-user control per project is assumed.
- Multi-language output is deferred until English workflow reaches quality targets.

## LLM Provider Strategy
- Support both Gemini 2.5 Pro and OpenAI ChatGPT 5 behind a unified interface so users can switch based on availability, pricing, or preference per project.
- Capture stage requirements (token windows, tool-calling needs, JSON mode) and map them to provider capabilities with fallbacks when a provider lacks a feature.
- Implement deterministic prompt templates for each agent role (structure proposer, critic, researcher, creative director, writer, etc.) with clear JSON schemas to guarantee machine-readable outputs and easy diffing.
- Maintain cost and latency logging at each agent step to inform automatic throttling or provider switching when budgets are exceeded.
- Include local mocked LLM transport for development so Phase 5+ features can be built without incurring provider cost.

## Privacy, Legal, and Compliance Considerations
- All user inputs (ideas, research guidelines, uploaded DOCX, generated drafts) stay on the local Docker stack; no data is persisted outside the user’s machine unless users export it.
- Enforce clear data retention policies: temporary artifacts stored in object storage containers with configurable TTL and manual purge controls.
- Cite sources rigorously by linking facts to original references extracted from DOCX files; surface potential citation gaps before writing progresses.
- Provide disclaimers about LLM-generated content, emphasising the user’s responsibility for final fact-checking and rights clearance.
- Offer configurable filters or warnings to avoid disallowed content (e.g., sensitive personal data) during agent runs.

## Repository Structure & Coding Standards (Draft)
```
/
├── apps/
│   ├── frontend/         # Next.js (TypeScript) wizard UI
│   └── api/              # FastAPI gateway with REST/WebSocket endpoints
├── services/
│   ├── orchestrator/     # Workflow engine (LangGraph/Prefect) and state machine definitions
│   ├── agent-workers/    # Celery/RQ workers for LLM calls and critiques
│   └── doc-parser/       # DOCX ingestion and citation extraction service
├── infra/
│   ├── docker-compose.yml
│   ├── Dockerfiles/
│   └── terraform/        # (future) cloud infra scaffolding if needed
├── libs/
│   ├── python/           # Shared Python packages (schemas, provider adapters)
│   └── ts/               # Shared TypeScript utilities (models, API clients)
├── tests/
│   ├── integration/
│   └── unit/
├── docs/
│   ├── phase-0-foundations.md
│   └── architecture/
└── .github/              # CI workflows
```

### Coding & Collaboration Conventions
- **Languages**: Python 3.11+, TypeScript 5+.
- **Style**: Ruff/Black for Python; ESLint/Prettier for TypeScript; conventional commits for history clarity.
- **Testing**: Pytest for backend/lib layers; Vitest/Playwright for frontend and end-to-end flows once available.
- **Documentation**: Markdown in `docs/`, architecture diagrams as `.drawio`/`.png` with source files checked in.
- **Branching**: Trunk-based with short-lived feature branches, protected `main` requiring lint/test checks.

## Open Questions for Phase 1
- Confirmed: Prefect 2 will serve as the orchestrator framework for coordinating stages.
- Decide on specific DOCX parsing library (python-docx vs docx2python) and citation extraction approach.
- Define minimum viable auth scheme for v1 (local user accounts vs single-user mode).
- Determine whether we need GPU support within Docker for any provider integration or future fine-tuning tasks.
- Decide on initial category taxonomy defaults and whether users can customise colours/ordering in the library UI.
