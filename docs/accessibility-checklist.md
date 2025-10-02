# Accessibility Checklist (Phase 18)

## Enhancements Delivered
- Added a global skip link in `AppLayout` so keyboard users can jump straight to main content.
- Normalised stage labels across backend and frontend, improving announcement consistency for screen readers.
- Marked asynchronous feedback (`Loading…`, success banners, budget errors) with `role="status"`/`role="alert"` and `aria-live="polite"` to ensure assistive tech receives updates.
- Ensured every stage page (Idea Intake → Writing Studio) exposes a descriptive `<h1>` that matches the workflow sidebar naming.
- Upgraded provider override dropdowns to display friendly stage names while persisting canonical enum values.

## Manual Verification Steps
- Tab through the Library Dashboard: the skip link becomes visible and focuses the main region.
- Trigger budget editing errors on a project card to confirm the alert is announced.
- Submit a regeneration action (Structure Lab, Title Hub, Story Weave, Guideline Studio, Writing Studio) and listen for the status toast via screen reader.
- Toggle the Agents & API `Save provider settings` action to check the status banner announcement.

## Follow-Up Items
- Re-run colour contrast analysis (currently based on tailwind-inspired palette) and adjust CSS variables if ratios fall below WCAG AA.
- Add keyboard shortcuts or focus traps for modal-style elements when they are introduced (currently all flows are page-level).
- Extend end-to-end tests to assert `aria-live` behaviour once automated accessibility tooling is integrated (e.g., axe-core in CI).
