# Phase 17 – Security & Compliance

## Objective
Strengthen authentication, authorization, data protection, and compliance practices to safeguard user content (ideas, research, drafts) processed through the AI-powered book creation pipeline.

## Scope & Context
- Builds on local-first deployment but anticipates scenarios where multiple users or sensitive research data require stricter controls.
- Ensures privacy and citation requirements outlined in Phase 0 are enforced technically.
- Prepares groundwork for possible future cloud or collaborative deployments.

## Key Deliverables
- Authentication scheme (local user accounts or single-user lock) with secure credential storage and session management.
- Role-based access control model for projects and categories, enabling future multi-user collaboration while defaulting to single-author mode.
- Data encryption strategy for stored DOCX files, exported manuscripts, and secrets.
- Compliance documentation covering citation integrity, data retention policies, and user responsibilities.

## Milestones & Tasks
1. Implement auth middleware in API gateway, integrating with frontend login/session flows.
2. Add RBAC checks around project access, category management, file uploads, and stage approvals.
3. Configure encryption at rest for object storage volumes and secure transmission (HTTPS within Docker via reverse proxy).
4. Perform security audit of provider integrations, ensuring keys stored securely and rotated easily.
5. Update privacy notices and in-app messaging to communicate data handling practices.

## Dependencies
- Infrastructure from Phase 1 (Docker, reverse proxy setup).
- API and frontend scaffolding (Phases 4 & 6) for injecting auth flows.
- Documentation frameworks from Phase 18 to publish policy updates.

## Risks & Mitigations
- **Risk**: Security additions complicate local setup.
  - *Mitigation*: Offer development bypass modes while ensuring production profile enforces controls.
- **Risk**: Citation compliance not programmatically enforced.
  - *Mitigation*: Integrate checks from Phases 10 and 14, requiring citations before stage completion.

## Exit Criteria
- Authenticated user flow tested end-to-end with role checks.
- Sensitive data encrypted and access logs capturing significant actions (downloads, stage approvals).
- Compliance documents reviewed and stored in repo.

## Handoffs & Next Steps
- Provide security posture summary to Phase 19 for launch readiness review.
- Inform future roadmap items (collaboration, cloud sync) with current security capabilities.

## Implementation Summary (v1)
- Added password-based authentication with cookie sessions, bcrypt hashing, and RBAC enforcement across every project endpoint. Session management lives in `apps/api/app/main.py`.
- Introduced `project_members` to scope access per user and stage-specific permission checks so only owners/editors can mutate state.
- Encrypted DOCX uploads at rest using a Fernet key loaded from `BOOK_CREATOR_ENCRYPTION_KEY`.
- Delivered a Next.js login screen and auth provider that gates all existing flows, surfaces the active account, and offers one-click logout.
- Expanded `.env.example` with new security variables (admin credentials, session TTL, cookie policy) to keep local setups consistent.

## Operational Notes
- Set `BOOK_CREATOR_ADMIN_EMAIL`, `BOOK_CREATOR_ADMIN_PASSWORD`, and `BOOK_CREATOR_ENCRYPTION_KEY` before booting the API; startup fails if credentials or keys are missing.
- Session cookies default to SameSite `lax`. Toggle `BOOK_CREATOR_SESSION_COOKIE_SECURE=1` for HTTPS deployments.
- Admins automatically inherit owner access to all projects; add additional members via direct SQL until a UI is provided.
