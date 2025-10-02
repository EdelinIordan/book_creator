# End-to-End Walkthrough

This guide walks through the full nonfiction workflow in the Book Creator app. Each stage aligns with the on-screen labels surfaced in the sidebar workflow list.

## 1. Access & Session
1. Start the stack with `make docker-up` (or the equivalent Docker Compose command).
2. Visit `http://localhost:3100` and sign in using the admin credentials in your `.env` file (`BOOK_CREATOR_ADMIN_EMAIL` / `BOOK_CREATOR_ADMIN_PASSWORD`).
3. After authentication the Library Dashboard loads, listing any seeded or previously created projects.

## 2. Idea Intake
1. Click **New Project** on the Library Dashboard.
2. Provide an optional working title, select a category, and describe the concept in ≤100 words. Add optional research guidelines (≤500 words) if you already know the depth or sources you expect.
3. Submit the form. The orchestrator will generate the initial structure and redirect you to the Structure Lab when ready.

## 3. Structure Lab
1. Review the multi-agent outline inside the **Structure View** tab. Toggle to **Raw JSON** if you want to inspect IDs or payloads.
2. Use **Request Regeneration** if the critique timeline suggests issues. Iterations appear in the **Agent Iterations** section.
3. When satisfied, click **Approve Structure** to unlock the Title Hub.

## 4. Title Hub
1. Evaluate the shortlist and generated rationales.
2. Select a favourite, optionally edit the text inline, and confirm the final title.
3. Regenerate title options if you need additional candidates. Once confirmed, proceed to the Research Dashboard.

## 5. Research Dashboard
1. Supply extra research guidance (optional) and regenerate prompts if you adjust the brief.
2. Copy each Deep Research prompt, run it in your provider of choice (Gemini / ChatGPT Deep Research), and upload the resulting DOCX files with the **Attach Research** buttons.
3. When every prompt has at least one linked upload, continue to the Research Fact Map.

## 6. Research Fact Map
1. Inspect the coverage overview. Use the dropdown to focus on individual subchapters.
2. Address any subchapters flagged in **Needs mapping attention** by re-running the mapping agents or refining upstream research.
3. Once every subchapter contains mapped facts, advance to the Story Weave Lab.

## 7. Story Weave Lab
1. Review the persona card and critique notes. Provide optional persona preferences and regenerate if you want fresh anecdotes.
2. Ensure each subchapter entry contains the desired hooks, analogies, and emotional beats.
3. Move on to the Guideline Studio when satisfied.

## 8. Guideline Studio
1. Regenerate creative guidelines if you want to incorporate fresh preferences.
2. Filter by chapter to review per-subchapter packets. Export the JSON bundle for archival or downstream QA if needed.
3. When the readiness badge flips to **Ready for Writing**, open the Writing Studio.

## 9. Writing Studio
1. Submit optional run notes before initiating the writing loop. These hints travel with the agent cycle.
2. Monitor subchapter cards for outstanding feedback and iterate until every draft is marked **Ready**.
3. Download drafts or copy text directly from the iteration panels for final polish outside the tool.

## 10. Wrap-Up & Sign-Off
1. Return to the Library Dashboard to confirm the project’s progress bar hits 100% and the stage label reads **Ready to Publish**.
2. Archive key exports (guidelines JSON, DOCX uploads, final drafts) according to your release checklist before moving into Phase 19 pre-launch validation.

---

**Verification pointers**
- Each stage surface shows a status banner when work completes; check those to ensure handoffs are ready.
- The sidebar workflow list provides the canonical naming used throughout the docs and release materials.
- If an action fails, look for alert messages (screen-reader friendly) before retrying.
