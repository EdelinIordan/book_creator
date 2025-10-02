# Frontend Architecture Overview

## Technology Stack
- Next.js 14 with TypeScript
- CSS Modules for scoped styling
- React Hook Form for complex forms (provider settings)
- Zustand (placeholder) and axios ready for state management / API access

## Layout & Navigation
- `AppLayout` component provides sidebar navigation, workflow timeline, and main content area.
- Routes:
  - `/` – dashboard placeholder with project cards and quick actions.
  - `/provider-settings` – UI for managing API keys, default models, and per-stage overrides (stored locally for now).
  - `/projects/new` – Idea intake form that posts to the API, triggers structure generation, and redirects to Structure Lab.
  - `/projects/[id]/structure` – Structure Lab view showing outline, live agent timeline, and approval controls backed by the API.
  - `/projects/[id]/titles` – Title ideation workspace with shortlist, final-selection, and regeneration controls.
  - `/projects/[id]/research` – Research dashboard listing generated Deep Research prompts, optional guidelines, and upload tracking.

## Provider Settings UI
- `ProviderLongForm` handles global defaults and an override table for individual stages.
- Local storage utilities (`src/lib/provider-storage.ts`) simulate persistence until backend endpoints land.
- Form saving currently displays a status message; future work will POST to the API gateway.

## Build & Lint
- `npm run lint` (ESLint via `next lint`).
- `npm run build` generates static output; verified in Phase 6.

## Next Steps
- Integrate real API endpoints for saving provider configs (Phase 6b/Phase 7 backend work).
- Extend dashboard cards once additional stages expose detail views and actions.
- Add Playwright smoke tests after routes stabilize.
