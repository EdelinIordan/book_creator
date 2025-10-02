DROP TYPE IF EXISTS project_stage;

CREATE TYPE project_stage AS ENUM (
    'IDEA',
    'STRUCTURE',
    'TITLE',
    'RESEARCH',
    'FACT_MAPPING',
    'EMOTIONAL',
    'GUIDELINES',
    'WRITING',
    'COMPLETE'
);

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT,
    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    stage project_stage NOT NULL DEFAULT 'IDEA',
    idea_summary TEXT,
    last_updated TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

INSERT INTO projects (title, category_id, stage, idea_summary)
SELECT 'Echoes of Empire', categories.id, 'STRUCTURE', 'Comparative history of empires and their administrative legacies.'
FROM categories WHERE name = 'History'
ON CONFLICT DO NOTHING;

INSERT INTO projects (title, category_id, stage, idea_summary)
SELECT 'Mind Over Habit', categories.id, 'WRITING', 'Cognitive frameworks for building sustainable habits.'
FROM categories WHERE name = 'Psychology'
ON CONFLICT DO NOTHING;

INSERT INTO projects (title, category_id, stage, idea_summary)
SELECT 'Quantum Kitchen', categories.id, 'IDEA', 'Popular science exploration of physics concepts through cooking analogies.'
FROM categories WHERE name = 'Popular Science'
ON CONFLICT DO NOTHING;

INSERT INTO projects (title, category_id, stage, idea_summary)
SELECT 'Vital Rhythms', categories.id, 'COMPLETE', 'Holistic guide to health metrics and preventive care.'
FROM categories WHERE name = 'Health'
ON CONFLICT DO NOTHING;
