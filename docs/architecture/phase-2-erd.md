# Phase 2 – ERD Snapshot

```mermaid
erDiagram
    categories ||--o{ projects : contains
    projects ||--o{ chapters : includes
    chapters ||--o{ subchapters : includes
    subchapters ||--o{ research_facts : references
    subchapters ||--o{ emotional_layers : enriches
    subchapters ||--o{ creative_guidelines : informs
    subchapters ||--o{ draft_versions : drafts
    projects ||--o{ research_prompts : generates
    projects ||--o{ agent_messages : logs

    categories {
        uuid id
        string name
        string color_hex
        timestamp created_at
    }

    projects {
        uuid id
        uuid category_id
        string title
        enum stage
        text idea_summary
        timestamp last_updated
    }

    chapters {
        uuid id
        uuid project_id
        string title
        string summary
        int order
    }

    subchapters {
        uuid id
        uuid chapter_id
        string title
        string summary
        int order
    }

    research_prompts {
        uuid id
        uuid project_id
        text prompt_text
        json focus_subchapters
        json desired_sources
    }

    research_facts {
        uuid id
        uuid subchapter_id
        text summary
        text detail
        json citation
    }

    emotional_layers {
        uuid id
        uuid subchapter_id
        text story_hook
        text analogy
        text persona_note
    }

    creative_guidelines {
        uuid id
        uuid subchapter_id
        json objectives
        json must_include_facts
        json emotional_beats
        text narrative_voice
        json structural_reminders
        json success_metrics
        json risks
        text status
        int version
    }

    draft_versions {
        uuid id
        uuid subchapter_id
        int version_index
        text content
        enum role
    }

    agent_messages {
        uuid id
        uuid project_id
        enum stage
        enum role
        text content
        json critiques
    }
```

This ERD models the artifacts described by the Phase 2 schemas. Vector embeddings (for research facts) and analytics snapshots are stored in auxiliary tables aligned with the `ProjectProgressSnapshot` object.
