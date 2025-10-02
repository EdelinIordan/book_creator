# Phase 6 – Frontend Scaffolding

## Objective
Create the foundational Next.js application that will host the guided wizard for the entire book-writing workflow, establishing shared layout, routing, state management, and component primitives.

## Scope & Context
- Converts the repository structure and tooling from earlier phases into a functional frontend ready to display agent progress.
- Focuses on infrastructure (design system, authentication placeholder, WebSocket integration) rather than detailed stage-specific screens, which arrive in later phases.
- Must support streaming updates from the orchestrator to reflect multi-agent activity.

- Next.js project setup with TypeScript, ESLint/Prettier, testing harness (Vitest/Playwright), and storybook (optional) for component previews.
- Global layout featuring timeline/stepper placeholders aligning with Idea, Structure, Title, Research Prompts, Research Fact Mapping, Emotional Layer, and Proper Writing stages.
- State management solution (React Query/Zustand/Redux) with patterns for optimistic updates and real-time data feeds.
- Library dashboard scaffolding with category grouping, progress indicators, and project cards fed by mock data.
- Shared UI components: cards, panels, diff viewer shell, modal, tabs, upload widgets.
- Provider settings workspace where users enter/manage API keys, default models, and per-agent LLM preferences exposed to the orchestrator.

## Milestones & Tasks
1. Scaffold Next.js app inside `apps/frontend` with Docker configuration matching Phase 1.
2. Implement design tokens and theme (light/dark) consistent with the professional authorship tone described in Phase 0.
3. Integrate API client from `libs/ts` and set up WebSocket transport for live agent updates.
4. Create placeholder routes for each major stage plus the category-based library dashboard, wiring navigation guardrails based on orchestrator status.
5. Implement mock data and visualisation for project counts per category to validate layout decisions.
6. Prototype provider settings UI (forms for API keys, default model selection, per-agent preferences) wired to temporary local storage or stub API endpoints.
7. Document component library usage and add examples for future contributors.

## Dependencies
- Phase 1 environment for Docker integration.
- Phase 2 TypeScript schemas for typing API interactions.
- Orchestrator status endpoints/events from Phase 4 for live updates.

## Risks & Mitigations
- **Risk**: UI architecture doesn’t scale to complex agent visualisations.
  - *Mitigation*: Invest in flexible layout system and component composition from the start.
- **Risk**: Real-time streaming introduces performance issues.
  - *Mitigation*: Use efficient state stores and throttle updates when many agent messages arrive.

## Exit Criteria
- Frontend builds inside Docker and locally, passing lint/test suites.
- Core layout rendered with stage placeholders and sample data from mock APIs, including category library view.
- Developer documentation covers local development flow and component storybook usage.

## Handoffs & Next Steps
- Enable Phase 7 and later phases to implement detailed screens using the shared infrastructure.
- Provide feedback loop with backend team to refine API contracts as UI patterns emerge.
