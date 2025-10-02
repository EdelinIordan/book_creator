# Migration Scaffolding

Phase 2 introduces an Alembic environment so future phases can create versioned
migrations derived from the shared schemas.

## Usage
1. Install developer dependencies (`make install`). This includes Alembic.
2. Export the Postgres URL while working locally:
   ```bash
   export DATABASE_URL=postgresql+psycopg://book_creator:book_creator@localhost:5433/book_creator
   ```
3. Generate a new migration (placeholder example):
   ```bash
   alembic -c infra/migrations/alembic.ini revision -m "add research facts"
   ```
4. Edit the generated file under `infra/migrations/versions/` with SQL statements
   aligned with the Pydantic/Zod schemas.
5. Apply migrations against the local database:
   ```bash
   alembic -c infra/migrations/alembic.ini upgrade head
   ```

At this phase the migration directory contains only the base configuration; the
first real revision will be authored once SQLAlchemy models or explicit DDL
statements are introduced.
