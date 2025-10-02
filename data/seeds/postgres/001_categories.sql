CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    color_hex CHAR(7) NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

INSERT INTO categories (name, color_hex)
    VALUES ('History', '#7c3aed')
ON CONFLICT (name) DO NOTHING;

INSERT INTO categories (name, color_hex)
    VALUES ('Psychology', '#6366f1')
ON CONFLICT (name) DO NOTHING;

INSERT INTO categories (name, color_hex)
    VALUES ('Popular Science', '#14b8a6')
ON CONFLICT (name) DO NOTHING;

INSERT INTO categories (name, color_hex)
    VALUES ('Health', '#22d3ee')
ON CONFLICT (name) DO NOTHING;
