# Phase 18 – Polish & Documentation Release Notes

## Highlights
- Renamed every workflow stage to its product-facing label (Idea Intake → Ready to Publish) in both backend responses and the AppLayout sidebar.
- Refreshed the Library Dashboard hero copy, improved project card messaging, and tightened CTA labels for Library Dashboard and downstream stages.
- Added accessible status messaging (`role="status"` / `role="alert"`) and a global skip link so keyboard and screen-reader users receive real-time feedback across Idea Intake, Structure Lab, Title Hub, Research Dashboard, Research Fact Map, Story Weave Lab, Guideline Studio, and Writing Studio.
- Updated provider override tooling to display the same friendly stage names while keeping enum values intact for APIs.

## Documentation Additions
- `docs/user-walkthrough.md` – step-by-step guide from authentication through writing sign-off.
- `docs/documentation-index.md` – top-level map pointing to contributor guides, architecture notes, and phase roadmaps.
- `docs/accessibility-checklist.md` – record of Phase 18 accessibility improvements, manual verification steps, and follow-up items.
- Refreshed `docs/development-setup.md` with clearer install guidance and Library Dashboard callouts.

## Known Gaps / Follow-Up
- Backend startup still relies on the deprecated FastAPI startup hook (`apps/api/app/main.py:653`); migrate to the lifespan API in Phase 19.
- Unit tests that require `python-docx` remain skipped until the dependency lands in CI (`tests/unit/test_doc_parser_service.py`).
- Colour contrast should be rechecked before launch; palette tweaks may be needed to meet WCAG AA.
- Publish automated accessibility checks (e.g., axe-core) as part of the lint/test pipeline.

## Verification Checklist
1. Run `npm --prefix apps/frontend run lint` – ensures UI/TypeScript changes compile cleanly. *(Completed)*
2. Manually tab through the Library Dashboard: confirm the skip link appears and focus shifts to `#main-content`.
3. Trigger a status message (e.g., regenerate structure) and verify the announcement via screen reader.
4. Follow `docs/user-walkthrough.md` from Idea Intake to Writing Studio; confirm stage labels in the sidebar match each section heading.
5. Review `docs/documentation-index.md` and confirm links resolve for at least one item in each section.

## Ready for Phase 19 When…
- Accessibility follow-up items are triaged (contrast, automated checks).
- Remaining backend TODOs (lifespan manager, `python-docx`) are scheduled.
- Pre-launch validation scenarios adopt the updated stage names to keep stakeholder comms aligned.
