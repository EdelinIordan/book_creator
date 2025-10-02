"""Idea intake and structure management API for the Book Creator stack."""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import logging
import os
import re
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from time import perf_counter
from typing import Any, Callable, Optional
from uuid import UUID, uuid4

import bcrypt
import httpx
import psycopg
from cryptography.fernet import Fernet
from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from book_creator_schemas.enums import AgentRole, BookStage
from book_creator_schemas.utils.validators import ensure_max_word_count
from book_creator_schemas.models.book import (
    CreativeGuidelineBatch,
    EmotionalLayerBatch,
    FactMappingBatch,
    GuidelineFactReference,
    PersonaProfile,
    ResearchFactCandidate,
    SubchapterFactCoverage,
    TitleBatch,
    DraftFeedbackItem,
    DraftIteration,
    WritingBatch,
)

from book_creator_observability import (
    log_context,
    observe_stage_duration,
    setup_fastapi_metrics,
    setup_logging,
)


DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is required")

# psycopg connection URLs do not use SQLAlchemy's driver suffix.
PG_CONNINFO = DATABASE_URL.replace("+psycopg", "")

ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://orchestrator:9100")
ORCHESTRATOR_TIMEOUT_SECONDS = float(os.getenv("ORCHESTRATOR_TIMEOUT", "60"))

DOC_PARSER_URL = os.getenv("DOC_PARSER_URL", "http://doc_parser:9200")
DOC_PARSER_TIMEOUT_SECONDS = float(os.getenv("DOC_PARSER_TIMEOUT", "30"))

ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("BOOK_CREATOR_ALLOWED_ORIGINS", "http://localhost:3100").split(",")
    if origin.strip()
]

STORAGE_ROOT = os.getenv("STORAGE_ROOT", os.path.join(os.getcwd(), "storage"))
RESEARCH_UPLOADS_DIR = os.path.join(STORAGE_ROOT, "research_uploads")

# Shared connection pool for lightweight data access.
POOL = ConnectionPool(PG_CONNINFO, min_size=1, max_size=10, open=True)

SERVICE_NAME = "api"
setup_logging(SERVICE_NAME)
logger = logging.getLogger(__name__)

STAGE_PROGRESS: dict[BookStage, int] = {
    BookStage.IDEA: 10,
    BookStage.STRUCTURE: 25,
    BookStage.TITLE: 35,
    BookStage.RESEARCH: 45,
    BookStage.FACT_MAPPING: 55,
    BookStage.EMOTIONAL: 65,
    BookStage.GUIDELINES: 75,
    BookStage.WRITING: 90,
    BookStage.COMPLETE: 100,
}

STAGE_FRIENDLY_LABELS: dict[BookStage, str] = {
    BookStage.IDEA: "Idea Intake",
    BookStage.STRUCTURE: "Structure Lab",
    BookStage.TITLE: "Title Hub",
    BookStage.RESEARCH: "Research Dashboard",
    BookStage.FACT_MAPPING: "Research Fact Map",
    BookStage.EMOTIONAL: "Story Weave Lab",
    BookStage.GUIDELINES: "Guideline Studio",
    BookStage.WRITING: "Writing Studio",
    BookStage.COMPLETE: "Ready to Publish",
}

AUTH_COOKIE_NAME = os.getenv("BOOK_CREATOR_SESSION_COOKIE_NAME", "book_creator_session")
SESSION_TTL_MINUTES = int(os.getenv("BOOK_CREATOR_SESSION_TTL_MINUTES", "720"))
SESSION_TTL = timedelta(minutes=max(SESSION_TTL_MINUTES, 1))
SESSION_COOKIE_SECURE = os.getenv("BOOK_CREATOR_SESSION_COOKIE_SECURE", "0") == "1"
SESSION_COOKIE_SAMESITE = os.getenv("BOOK_CREATOR_SESSION_COOKIE_SAMESITE", "lax")
SESSION_COOKIE_DOMAIN = os.getenv("BOOK_CREATOR_SESSION_COOKIE_DOMAIN")

ENCRYPTION_KEY = os.getenv("BOOK_CREATOR_ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    raise RuntimeError(
        "BOOK_CREATOR_ENCRYPTION_KEY environment variable is required. Generate a Fernet key and set it before starting the API."
    )

try:
    FERNET = Fernet(ENCRYPTION_KEY)
except ValueError as exc:  # pragma: no cover - configuration error
    raise RuntimeError("BOOK_CREATOR_ENCRYPTION_KEY must be a valid Fernet key") from exc

DEFAULT_ADMIN_EMAIL = os.getenv("BOOK_CREATOR_ADMIN_EMAIL", "admin@local").strip().lower()
DEFAULT_ADMIN_PASSWORD = os.getenv("BOOK_CREATOR_ADMIN_PASSWORD")

GLOBAL_ROLE_PRIORITY: dict[str, int] = {
    "member": 1,
    "admin": 10,
}

PROJECT_ROLE_PRIORITY: dict[str, int] = {
    "viewer": 1,
    "editor": 5,
    "owner": 10,
}

HEX_COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")


class Category(BaseModel):
    id: int
    name: str
    color_hex: str


class CategoryCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    color_hex: str = Field(..., description="Hex color code including the leading #")

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Category name cannot be empty")
        return cleaned

    @field_validator("color_hex")
    @classmethod
    def validate_color(cls, value: str) -> str:
        color = value.strip().upper()
        if not HEX_COLOR_PATTERN.match(color):
            raise ValueError("Color must be a hex code like #A1B2C3")
        return color


class ProjectSummary(BaseModel):
    id: UUID
    title: Optional[str]
    stage: BookStage
    stage_label: str
    progress: int = Field(ge=0, le=100)
    idea_summary: Optional[str]
    research_guidelines: Optional[str]
    last_updated: datetime
    category: Optional[Category] = None
    guidelines_ready: bool = Field(default=False)
    guideline_version: Optional[int] = None
    guideline_updated_at: Optional[datetime] = None
    writing_ready: bool = Field(default=False)
    writing_updated_at: Optional[datetime] = None
    total_cost_usd: float = Field(default=0.0, ge=0)
    spend_limit_usd: Optional[float] = Field(default=None, ge=0)
    budget_remaining_usd: Optional[float] = Field(default=None)
    budget_status: str = Field(default="unlimited")


class SessionUser(BaseModel):
    id: UUID
    email: str
    role: str


class SessionResponse(BaseModel):
    user: SessionUser


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def normalise_email(cls, value: str) -> str:
        return value.strip().lower()


class StructureTimelineEntry(BaseModel):
    id: str
    role: str
    title: str
    content: str
    timestamp: datetime


class StructureDetail(BaseModel):
    project: ProjectSummary
    structure: dict[str, Any]
    summary: str
    critiques: list[str]
    iterations: list[StructureTimelineEntry]


class IdeaIntakeRequest(BaseModel):
    category_id: Optional[int] = Field(None, description="Optional existing category identifier")
    working_title: Optional[str] = Field(None, max_length=150)
    description: str = Field(..., description="Up to 100 words describing the book concept")
    research_guidelines: Optional[str] = Field(
        None,
        max_length=2000,
        description="Optional research guidance (up to 2000 characters)",
    )

    @field_validator("description")
    @classmethod
    def validate_word_count(cls, value: str) -> str:
        ensure_max_word_count(value, limit=100, field_name="Idea description")
        return value.strip()

    @field_validator("research_guidelines")
    @classmethod
    def validate_guidelines(cls, value: Optional[str]) -> Optional[str]:
        if value:
            ensure_max_word_count(value, limit=500, field_name="Research guidelines")
            return value.strip()
        return value


class IdeaIntakeResponse(BaseModel):
    project_id: UUID
    structure: StructureDetail


class ApproveStructureResponse(BaseModel):
    project: ProjectSummary


class TitleOptionModel(BaseModel):
    title: str
    rationale: str


class TitleDetail(BaseModel):
    project: ProjectSummary
    options: list[TitleOptionModel]
    shortlist: list[str]
    selected_title: Optional[str]
    critique: Optional[str]
    updated_at: datetime


class ShortlistUpdateRequest(BaseModel):
    shortlist: list[str] = Field(default_factory=list)


class SelectTitleRequest(BaseModel):
    title: str


class ResearchPromptModel(BaseModel):
    focus_summary: str
    focus_subchapters: list[str]
    prompt_text: str
    desired_sources: list[str]
    additional_notes: Optional[str] = None


class ResearchUploadModel(BaseModel):
    id: int
    prompt_index: int
    filename: str
    storage_path: str
    notes: Optional[str]
    uploaded_at: datetime
    word_count: int
    paragraph_count: int


class ResearchDetail(BaseModel):
    project: ProjectSummary
    prompts: list[ResearchPromptModel]
    critique: Optional[str]
    guidelines: Optional[str]
    uploads: list[ResearchUploadModel]


class ResearchUploadRequest(BaseModel):
    prompt_index: int = Field(..., ge=0)
    filename: str = Field(..., min_length=1, max_length=255)
    notes: Optional[str] = Field(None, max_length=500)
    content_base64: str = Field(..., description="Base64-encoded research document")


class ResearchRegenerateRequest(BaseModel):
    guidelines: Optional[str] = Field(None, max_length=2000)


class FactCitationModel(BaseModel):
    source_title: str
    author: Optional[str] = None
    publication_date: Optional[str] = None
    url: Optional[str] = None
    page: Optional[str] = None
    source_type: Optional[str] = None


class MappedFactModel(BaseModel):
    id: UUID
    subchapter_id: UUID
    summary: str
    detail: str
    citation: FactCitationModel
    upload_id: Optional[int]
    prompt_index: Optional[int]
    created_at: datetime


class FactCoverageModel(BaseModel):
    subchapter_id: UUID
    fact_count: int = Field(..., ge=0)


class FactMappingDetail(BaseModel):
    project: ProjectSummary
    facts: list[MappedFactModel]
    coverage: list[FactCoverageModel]
    critique: Optional[str]
    updated_at: datetime


class PersonaProfileModel(BaseModel):
    name: str
    background: str
    voice: str
    signature_themes: list[str] = Field(default_factory=list)
    guiding_principles: list[str] = Field(default_factory=list)


class EmotionalEntryModel(BaseModel):
    id: UUID
    subchapter_id: UUID
    story_hook: str
    persona_note: Optional[str] = None
    analogy: Optional[str] = None
    emotional_goal: Optional[str] = None
    created_by: str
    created_at: datetime


class EmotionalLayerDetail(BaseModel):
    project: ProjectSummary
    persona: PersonaProfileModel
    entries: list[EmotionalEntryModel]
    critique: Optional[str]
    updated_at: datetime


class EmotionalRegenerateRequest(BaseModel):
    persona_preferences: Optional[str] = Field(None, max_length=2000)


class GuidelineFactModel(BaseModel):
    fact_id: UUID
    summary: str
    citation: FactCitationModel
    rationale: Optional[str] = None


class GuidelinePacketModel(BaseModel):
    id: UUID
    subchapter_id: UUID
    objectives: list[str]
    must_include_facts: list[GuidelineFactModel]
    emotional_beats: list[str]
    narrative_voice: Optional[str] = None
    structural_reminders: list[str]
    success_metrics: list[str]
    risks: list[str]
    status: str
    created_by: str
    version: int
    created_at: datetime
    updated_at: datetime


class GuidelineDetail(BaseModel):
    project: ProjectSummary
    summary: Optional[str]
    critique: Optional[str]
    readiness: str
    version: int
    guidelines: list[GuidelinePacketModel]
    updated_at: datetime


class GuidelineRegenerateRequest(BaseModel):
    preferences: Optional[str] = Field(None, max_length=2000)


class WritingDetail(BaseModel):
    project: ProjectSummary
    batch: WritingBatch
    critique: Optional[str]


class WritingRunRequest(BaseModel):
    notes: Optional[str] = Field(None, max_length=2000)


class BudgetUpdateRequest(BaseModel):
    spend_limit_usd: Optional[float] = Field(None, ge=0)


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:  # pragma: no cover - corrupt hash
        return False


def _generate_session_token() -> str:
    return secrets.token_urlsafe(48)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _is_admin_user(user: SessionUser) -> bool:
    return GLOBAL_ROLE_PRIORITY.get(user.role, 0) >= GLOBAL_ROLE_PRIORITY.get("admin", 100)


def _purge_expired_sessions() -> None:
    with POOL.connection() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM user_sessions WHERE expires_at < NOW()")
        conn.commit()


def _create_session_record(
    user_id: UUID,
    token: str,
    expires_at: datetime,
    ip_address: Optional[str],
    user_agent: Optional[str],
) -> None:
    token_hash = _hash_token(token)
    with POOL.connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO user_sessions (id, user_id, token_hash, expires_at, ip_address, user_agent)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (token_hash) DO UPDATE
            SET user_id = EXCLUDED.user_id,
                expires_at = EXCLUDED.expires_at,
                ip_address = EXCLUDED.ip_address,
                user_agent = EXCLUDED.user_agent,
                created_at = NOW(),
                last_seen_at = NOW()
            """,
            (
                uuid4(),
                user_id,
                token_hash,
                expires_at,
                ip_address,
                (user_agent or "")[:512],
            ),
        )
        conn.commit()


def _delete_session_record(token: str) -> None:
    token_hash = _hash_token(token)
    with POOL.connection() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM user_sessions WHERE token_hash = %s", (token_hash,))
        conn.commit()


def _lookup_session_user(token: str) -> Optional[SessionUser]:
    token_hash = _hash_token(token)
    now = datetime.utcnow()
    with POOL.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT s.id AS session_id, s.expires_at, u.id AS user_id, u.email, u.role
            FROM user_sessions s
            JOIN app_users u ON u.id = s.user_id
            WHERE s.token_hash = %s
            """,
            (token_hash,),
        )
        row = cur.fetchone()
        if not row:
            return None
        if row["expires_at"] < now:
            cur.execute("DELETE FROM user_sessions WHERE id = %s", (row["session_id"],))
            conn.commit()
            return None
        cur.execute("UPDATE user_sessions SET last_seen_at = NOW() WHERE id = %s", (row["session_id"],))
        conn.commit()
    return SessionUser(id=row["user_id"], email=row["email"], role=row["role"])


def _get_user_by_email(email: str) -> Optional[dict[str, Any]]:
    with POOL.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT id, email, password_hash, role FROM app_users WHERE email = %s",
            (email,),
        )
        return cur.fetchone()


def _create_user(email: str, password: str, role: str) -> SessionUser:
    user_id = uuid4()
    password_hash = _hash_password(password)
    with POOL.connection() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO app_users (id, email, password_hash, role) VALUES (%s, %s, %s, %s)",
            (user_id, email, password_hash, role),
        )
        conn.commit()
    return SessionUser(id=user_id, email=email, role=role)


def _ensure_admin_memberships(admin_id: UUID) -> None:
    with POOL.connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO project_members (project_id, user_id, role)
            SELECT p.id, %s, 'owner'
            FROM projects p
            ON CONFLICT (project_id, user_id) DO NOTHING
            """,
            (admin_id,),
        )
        conn.commit()


def _ensure_default_admin() -> None:
    with POOL.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT id FROM app_users ORDER BY created_at ASC LIMIT 1")
        row = cur.fetchone()
        if row:
            _ensure_admin_memberships(row["id"])
            return

    if not DEFAULT_ADMIN_PASSWORD:
        raise RuntimeError(
            "BOOK_CREATOR_ADMIN_PASSWORD must be set before starting the API when no users exist"
        )

    admin = _create_user(DEFAULT_ADMIN_EMAIL, DEFAULT_ADMIN_PASSWORD, "admin")
    _ensure_admin_memberships(admin.id)
    logger.info("Default admin user initialised", extra={"email": DEFAULT_ADMIN_EMAIL})


def _set_project_membership(project_id: UUID, user_id: UUID, role: str) -> None:
    with POOL.connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO project_members (project_id, user_id, role)
            VALUES (%s, %s, %s)
            ON CONFLICT (project_id, user_id) DO UPDATE SET role = EXCLUDED.role
            """,
            (project_id, user_id, role),
        )
        conn.commit()


def _fetch_project_membership(user_id: UUID, project_id: UUID) -> Optional[str]:
    with POOL.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT role FROM project_members WHERE user_id = %s AND project_id = %s",
            (user_id, project_id),
        )
        row = cur.fetchone()
    if not row:
        return None
    return row["role"]


async def _ensure_project_access(project_id: UUID, user: SessionUser, required_role: str) -> None:
    if _is_admin_user(user):
        return
    role = await run_in_threadpool(_fetch_project_membership, user.id, project_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if PROJECT_ROLE_PRIORITY.get(role, 0) < PROJECT_ROLE_PRIORITY.get(required_role, 0):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient project permissions")


def require_role(min_role: str = "member") -> Callable[[Request], Any]:
    async def dependency(request: Request) -> SessionUser:
        token = request.cookies.get(AUTH_COOKIE_NAME)
        if not token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
        user = await run_in_threadpool(_lookup_session_user, token)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired or invalid")
        if GLOBAL_ROLE_PRIORITY.get(user.role, 0) < GLOBAL_ROLE_PRIORITY.get(min_role, 0):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient global permissions")
        return user

    return dependency

app = FastAPI(title="Book Creator API", version="0.2.0")
setup_fastapi_metrics(app, service_name=SERVICE_NAME)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/auth/login", response_model=SessionResponse, tags=["auth"])
async def login(payload: LoginRequest, response: Response, request: Request) -> SessionResponse:
    email = payload.email
    user_row = await run_in_threadpool(_get_user_by_email, email)
    if not user_row or not _verify_password(payload.password, user_row["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = _generate_session_token()
    expires_at = datetime.utcnow() + SESSION_TTL
    client = request.client
    ip_address = client.host if client else None
    user_agent = request.headers.get("user-agent")
    await run_in_threadpool(_create_session_record, user_row["id"], token, expires_at, ip_address, user_agent)

    response.set_cookie(
        AUTH_COOKIE_NAME,
        token,
        max_age=int(SESSION_TTL.total_seconds()),
        httponly=True,
        secure=SESSION_COOKIE_SECURE,
        samesite=SESSION_COOKIE_SAMESITE,
        domain=SESSION_COOKIE_DOMAIN,
        path="/",
    )

    session_user = SessionUser(id=user_row["id"], email=user_row["email"], role=user_row["role"])
    logger.info("User logged in", extra={"user_id": str(session_user.id), "email": session_user.email})
    return SessionResponse(user=session_user)


@app.post("/auth/logout", tags=["auth"])
async def logout(
    response: Response,
    request: Request,
    current_user: SessionUser = Depends(require_role("member")),
) -> dict[str, str]:
    token = request.cookies.get(AUTH_COOKIE_NAME)
    if token:
        await run_in_threadpool(_delete_session_record, token)
    response.delete_cookie(
        AUTH_COOKIE_NAME,
        domain=SESSION_COOKIE_DOMAIN,
        path="/",
    )
    logger.info("User logged out", extra={"user_id": str(current_user.id), "email": current_user.email})
    return {"status": "logged_out"}


@app.get("/auth/session", response_model=SessionResponse, tags=["auth"])
async def session(current_user: SessionUser = Depends(require_role("member"))) -> SessionResponse:
    return SessionResponse(user=current_user)


@app.on_event("startup")
def _on_startup() -> None:
    _initialise_schema()
    _ensure_default_admin()
    _purge_expired_sessions()
    Path(RESEARCH_UPLOADS_DIR).mkdir(parents=True, exist_ok=True)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    """Simple readiness check."""

    return {"status": "ok"}


@app.get("/categories", response_model=list[Category], tags=["catalogue"])
async def list_categories(
    current_user: SessionUser = Depends(require_role("member")),
) -> list[Category]:
    return await run_in_threadpool(_fetch_categories)


@app.post("/categories", response_model=Category, status_code=status.HTTP_201_CREATED, tags=["catalogue"])
async def create_category(
    payload: CategoryCreateRequest,
    current_user: SessionUser = Depends(require_role("member")),
) -> Category:
    try:
        return await run_in_threadpool(_insert_category, payload)
    except psycopg.errors.UniqueViolation as exc:  # pragma: no cover - depends on DB state
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Category already exists") from exc


@app.get("/projects", response_model=list[ProjectSummary], tags=["projects"])
async def list_projects(
    current_user: SessionUser = Depends(require_role("member")),
) -> list[ProjectSummary]:
    return await run_in_threadpool(_fetch_projects, current_user)


@app.post("/projects", response_model=IdeaIntakeResponse, status_code=status.HTTP_201_CREATED, tags=["projects"])
async def create_project(
    payload: IdeaIntakeRequest,
    current_user: SessionUser = Depends(require_role("member")),
) -> IdeaIntakeResponse:
    try:
        project_id = await run_in_threadpool(_insert_project, payload, current_user.id)
    except psycopg.errors.ForeignKeyViolation as exc:  # pragma: no cover - depends on DB state
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown category") from exc

    try:
        await _run_structure_stage(project_id, payload.description)
    except httpx.HTTPError as exc:  # pragma: no cover - network/runtime failures
        await run_in_threadpool(_mark_project_failed, project_id)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Structure generation failed") from exc

    detail = await run_in_threadpool(_fetch_structure_detail, project_id)
    return IdeaIntakeResponse(project_id=project_id, structure=detail)


@app.get("/projects/{project_id}/structure", response_model=StructureDetail, tags=["projects"])
async def get_structure(
    project_id: UUID,
    current_user: SessionUser = Depends(require_role("member")),
) -> StructureDetail:
    await _ensure_project_access(project_id, current_user, "viewer")
    return await run_in_threadpool(_fetch_structure_detail, project_id)


@app.post("/projects/{project_id}/structure/regenerate", response_model=StructureDetail, tags=["projects"])
async def regenerate_structure(
    project_id: UUID,
    current_user: SessionUser = Depends(require_role("member")),
) -> StructureDetail:
    await _ensure_project_access(project_id, current_user, "editor")
    project = await run_in_threadpool(_fetch_project_core, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    idea_summary = project.get("idea_summary")
    if not idea_summary:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project is missing an idea summary")

    await _run_structure_stage(project_id, idea_summary)
    return await run_in_threadpool(_fetch_structure_detail, project_id)


@app.post("/projects/{project_id}/structure/approve", response_model=ApproveStructureResponse, tags=["projects"])
async def approve_structure(
    project_id: UUID,
    current_user: SessionUser = Depends(require_role("member")),
) -> ApproveStructureResponse:
    await _ensure_project_access(project_id, current_user, "editor")
    updated = await run_in_threadpool(_update_project_stage, project_id, BookStage.TITLE)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    try:
        await _run_title_stage(project_id)
    except httpx.HTTPError as exc:  # pragma: no cover - depends on network/provider state
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Title generation failed") from exc
    return ApproveStructureResponse(project=updated)


@app.get("/projects/{project_id}/titles", response_model=TitleDetail, tags=["projects"])
async def get_titles(
    project_id: UUID,
    current_user: SessionUser = Depends(require_role("member")),
) -> TitleDetail:
    await _ensure_project_access(project_id, current_user, "viewer")
    detail = await run_in_threadpool(_fetch_title_detail, project_id)
    if detail is None:
        await _run_title_stage(project_id)
        detail = await run_in_threadpool(_fetch_title_detail, project_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Title data unavailable")
    return detail


@app.post("/projects/{project_id}/titles/regenerate", response_model=TitleDetail, tags=["projects"])
async def regenerate_titles(
    project_id: UUID,
    current_user: SessionUser = Depends(require_role("member")),
) -> TitleDetail:
    await _ensure_project_access(project_id, current_user, "editor")
    await _run_title_stage(project_id)
    detail = await run_in_threadpool(_fetch_title_detail, project_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Title regeneration failed")
    return detail


@app.post("/projects/{project_id}/titles/shortlist", response_model=TitleDetail, tags=["projects"])
async def update_shortlist(
    project_id: UUID,
    payload: ShortlistUpdateRequest,
    current_user: SessionUser = Depends(require_role("member")),
) -> TitleDetail:
    await _ensure_project_access(project_id, current_user, "editor")
    await run_in_threadpool(_update_title_shortlist, project_id, payload.shortlist)
    detail = await run_in_threadpool(_fetch_title_detail, project_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Title data unavailable")
    return detail


@app.post("/projects/{project_id}/titles/select", response_model=TitleDetail, tags=["projects"])
async def select_title(
    project_id: UUID,
    payload: SelectTitleRequest,
    current_user: SessionUser = Depends(require_role("member")),
) -> TitleDetail:
    await _ensure_project_access(project_id, current_user, "editor")
    await run_in_threadpool(_select_title, project_id, payload.title)
    try:
        await _run_research_stage(project_id, None)
    except httpx.HTTPError:
        # Research prompt generation failures should not block title confirmation.
        pass
    detail = await run_in_threadpool(_fetch_title_detail, project_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Title data unavailable")
    return detail


@app.get("/projects/{project_id}/research", response_model=ResearchDetail, tags=["projects"])
async def get_research(
    project_id: UUID,
    current_user: SessionUser = Depends(require_role("member")),
) -> ResearchDetail:
    await _ensure_project_access(project_id, current_user, "viewer")
    detail = await run_in_threadpool(_fetch_research_detail, project_id)
    if detail is None:
        await _run_research_stage(project_id, None)
        detail = await run_in_threadpool(_fetch_research_detail, project_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Research prompts unavailable")
    return detail


@app.post(
    "/projects/{project_id}/research/regenerate",
    response_model=ResearchDetail,
    tags=["projects"],
)
async def regenerate_research(
    project_id: UUID,
    payload: ResearchRegenerateRequest | None = None,
    current_user: SessionUser = Depends(require_role("member")),
) -> ResearchDetail:
    await _ensure_project_access(project_id, current_user, "editor")
    guidelines = payload.guidelines if payload else None
    await _run_research_stage(project_id, guidelines)
    detail = await run_in_threadpool(_fetch_research_detail, project_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Research prompts unavailable")
    return detail


@app.post(
    "/projects/{project_id}/research/uploads",
    response_model=ResearchDetail,
    tags=["projects"],
)
async def register_research_upload(
    project_id: UUID,
    payload: ResearchUploadRequest,
    current_user: SessionUser = Depends(require_role("member")),
) -> ResearchDetail:
    await _ensure_project_access(project_id, current_user, "editor")
    detail = await _handle_research_upload(project_id, payload)
    return detail


@app.get("/projects/{project_id}/facts", response_model=FactMappingDetail, tags=["projects"])
async def get_fact_mapping(
    project_id: UUID,
    current_user: SessionUser = Depends(require_role("member")),
) -> FactMappingDetail:
    await _ensure_project_access(project_id, current_user, "viewer")
    detail = await run_in_threadpool(_fetch_fact_mapping_detail, project_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fact mapping unavailable")
    return detail


@app.get("/projects/{project_id}/emotional", response_model=EmotionalLayerDetail, tags=["projects"])
async def get_emotional_layer(
    project_id: UUID,
    current_user: SessionUser = Depends(require_role("member")),
) -> EmotionalLayerDetail:
    await _ensure_project_access(project_id, current_user, "viewer")
    detail = await run_in_threadpool(_fetch_emotional_layer_detail, project_id)
    if detail is None:
        try:
            ran = await _run_emotional_stage(project_id, None)
        except httpx.HTTPError as exc:  # pragma: no cover - provider/network errors
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Emotional layer generation failed") from exc
        if not ran:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Fact mapping must be completed before the emotional layer can run",
            )
        detail = await run_in_threadpool(_fetch_emotional_layer_detail, project_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emotional layer unavailable")
    return detail


@app.post(
    "/projects/{project_id}/emotional/regenerate",
    response_model=EmotionalLayerDetail,
    tags=["projects"],
)
async def regenerate_emotional_layer(
    project_id: UUID,
    payload: EmotionalRegenerateRequest | None = None,
    current_user: SessionUser = Depends(require_role("member")),
) -> EmotionalLayerDetail:
    await _ensure_project_access(project_id, current_user, "editor")
    persona_preferences = payload.persona_preferences if payload else None
    try:
        ran = await _run_emotional_stage(project_id, persona_preferences)
    except httpx.HTTPError as exc:  # pragma: no cover - provider/network errors
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Emotional layer regeneration failed") from exc
    if not ran:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Fact mapping results are required before regenerating the emotional layer",
        )

    detail = await run_in_threadpool(_fetch_emotional_layer_detail, project_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emotional layer unavailable")
    return detail


@app.get("/projects/{project_id}/guidelines", response_model=GuidelineDetail, tags=["projects"])
async def get_guidelines(
    project_id: UUID,
    current_user: SessionUser = Depends(require_role("member")),
) -> GuidelineDetail:
    await _ensure_project_access(project_id, current_user, "viewer")
    detail = await run_in_threadpool(_fetch_guideline_detail, project_id)
    if detail is None:
        try:
            ran = await _run_guidelines_stage(project_id, None)
        except httpx.HTTPError as exc:  # pragma: no cover - provider/network errors
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Guideline generation failed") from exc
        if not ran:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Emotional layer must be completed before creative guidelines can run",
            )
        detail = await run_in_threadpool(_fetch_guideline_detail, project_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guidelines unavailable")
    return detail


@app.post(
    "/projects/{project_id}/guidelines/regenerate",
    response_model=GuidelineDetail,
    tags=["projects"],
)
async def regenerate_guidelines(
    project_id: UUID,
    payload: GuidelineRegenerateRequest | None = None,
    current_user: SessionUser = Depends(require_role("member")),
) -> GuidelineDetail:
    await _ensure_project_access(project_id, current_user, "editor")
    preferences = payload.preferences if payload else None
    try:
        ran = await _run_guidelines_stage(project_id, preferences)
    except httpx.HTTPError as exc:  # pragma: no cover - provider/network errors
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Guideline regeneration failed") from exc
    if not ran:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Emotional layer must be completed before creative guidelines can run",
        )
    detail = await run_in_threadpool(_fetch_guideline_detail, project_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guidelines unavailable")
    return detail


@app.get("/projects/{project_id}/writing", response_model=WritingDetail, tags=["projects"])
async def get_writing_detail(
    project_id: UUID,
    current_user: SessionUser = Depends(require_role("member")),
) -> WritingDetail:
    await _ensure_project_access(project_id, current_user, "viewer")
    detail = await run_in_threadpool(_fetch_writing_detail, project_id)
    if detail is None:
        try:
            ran = await _run_writing_stage(project_id, None)
        except httpx.HTTPError as exc:  # pragma: no cover - provider/network errors
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Writing orchestration failed") from exc
        if not ran:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Creative guidelines must be ready before writing can begin",
            )
        detail = await run_in_threadpool(_fetch_writing_detail, project_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Writing detail unavailable")
    return detail


@app.post(
    "/projects/{project_id}/writing/run",
    response_model=WritingDetail,
    tags=["projects"],
)
async def run_writing_stage(
    project_id: UUID,
    payload: WritingRunRequest | None = None,
    current_user: SessionUser = Depends(require_role("member")),
) -> WritingDetail:
    await _ensure_project_access(project_id, current_user, "editor")
    notes = payload.notes.strip() if payload and payload.notes else None
    try:
        ran = await _run_writing_stage(project_id, notes)
    except httpx.HTTPError as exc:  # pragma: no cover - provider/network errors
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Writing orchestration failed") from exc
    if not ran:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Creative guidelines must be ready before writing can begin",
        )

    detail = await run_in_threadpool(_fetch_writing_detail, project_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Writing detail unavailable")
    return detail


@app.patch(
    "/projects/{project_id}/budget",
    response_model=ProjectSummary,
    tags=["projects"],
)
async def update_project_budget(
    project_id: UUID,
    payload: BudgetUpdateRequest,
    current_user: SessionUser = Depends(require_role("member")),
) -> ProjectSummary:
    await _ensure_project_access(project_id, current_user, "owner")
    await run_in_threadpool(_set_project_budget, project_id, payload.spend_limit_usd)
    summary = await run_in_threadpool(_fetch_project_summary, project_id)
    if summary is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return summary


@app.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["projects"])
async def delete_project(
    project_id: UUID,
    current_user: SessionUser = Depends(require_role("member")),
) -> Response:
    await _ensure_project_access(project_id, current_user, "owner")
    deleted = await run_in_threadpool(_delete_project, project_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/stats/agent-stage", tags=["stats"])
async def agent_stage_stats(
    current_user: SessionUser = Depends(require_role("admin")),
) -> dict[str, Any]:
    return await run_in_threadpool(_fetch_agent_stage_metrics)


def _initialise_schema() -> None:
    """Ensure tables required for Phase 7 exist."""

    ddl = """
    CREATE TABLE IF NOT EXISTS app_users (
        id UUID PRIMARY KEY,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'member',
        created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS user_sessions (
        id UUID PRIMARY KEY,
        user_id UUID REFERENCES app_users(id) ON DELETE CASCADE,
        token_hash TEXT NOT NULL UNIQUE,
        expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
        created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
        last_seen_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
        ip_address TEXT,
        user_agent TEXT
    );

    CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id
        ON user_sessions(user_id);

    CREATE TABLE IF NOT EXISTS categories (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL UNIQUE,
        color_hex CHAR(7) NOT NULL CHECK (color_hex ~ '^#[0-9A-Fa-f]{6}$'),
        created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_categories_name_lower
        ON categories (LOWER(name));

    ALTER TABLE projects
        ADD COLUMN IF NOT EXISTS category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL;

    CREATE TABLE IF NOT EXISTS project_members (
        project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
        user_id UUID REFERENCES app_users(id) ON DELETE CASCADE,
        role TEXT NOT NULL,
        added_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
        PRIMARY KEY (project_id, user_id)
    );

    CREATE TABLE IF NOT EXISTS project_structures (
        project_id UUID PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
        structure JSONB NOT NULL,
        summary TEXT NOT NULL,
        critiques JSONB NOT NULL,
        updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS project_titles (
        project_id UUID PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
        batch JSONB NOT NULL,
        critique TEXT,
        shortlist JSONB NOT NULL DEFAULT '[]'::jsonb,
        selected_title TEXT,
        updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
        approved_at TIMESTAMP WITHOUT TIME ZONE
    );

    ALTER TABLE projects ADD COLUMN IF NOT EXISTS research_guidelines TEXT;
    ALTER TABLE projects ADD COLUMN IF NOT EXISTS total_cost_cents BIGINT NOT NULL DEFAULT 0;
    ALTER TABLE projects ADD COLUMN IF NOT EXISTS spend_limit_cents BIGINT;

    CREATE TABLE IF NOT EXISTS project_research_prompts (
        project_id UUID PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
        prompts JSONB NOT NULL,
        critique TEXT,
        guidelines TEXT,
        updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS project_research_uploads (
        id SERIAL PRIMARY KEY,
        project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
        prompt_index INTEGER NOT NULL,
        filename TEXT NOT NULL,
        storage_path TEXT NOT NULL,
        notes TEXT,
        uploaded_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
        word_count INTEGER DEFAULT 0,
        paragraph_count INTEGER DEFAULT 0
    );

    ALTER TABLE project_research_uploads
        ADD COLUMN IF NOT EXISTS word_count INTEGER DEFAULT 0;

    ALTER TABLE project_research_uploads
        ADD COLUMN IF NOT EXISTS paragraph_count INTEGER DEFAULT 0;

    CREATE TABLE IF NOT EXISTS project_research_fact_candidates (
        id UUID PRIMARY KEY,
        project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
        upload_id INTEGER REFERENCES project_research_uploads(id) ON DELETE CASCADE,
        prompt_index INTEGER,
        source_filename TEXT,
        summary TEXT NOT NULL,
        detail TEXT NOT NULL,
        citation JSONB NOT NULL,
        created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_fact_candidates_project
        ON project_research_fact_candidates(project_id);

    CREATE TABLE IF NOT EXISTS project_research_facts (
        id UUID PRIMARY KEY,
        project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
        subchapter_id UUID NOT NULL,
        upload_id INTEGER REFERENCES project_research_uploads(id) ON DELETE SET NULL,
        prompt_index INTEGER,
        summary TEXT NOT NULL,
        detail TEXT NOT NULL,
        citation JSONB NOT NULL,
        created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_research_facts_project
        ON project_research_facts(project_id);

    CREATE INDEX IF NOT EXISTS idx_research_facts_subchapter
        ON project_research_facts(subchapter_id);

    CREATE TABLE IF NOT EXISTS project_fact_mapping (
        project_id UUID PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
        batch JSONB NOT NULL,
        coverage JSONB NOT NULL,
        critique TEXT,
        updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS project_emotional_persona (
        project_id UUID PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
        persona JSONB NOT NULL,
        critique TEXT,
        updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS project_emotional_entries (
        id UUID PRIMARY KEY,
        project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
        subchapter_id UUID NOT NULL,
        story_hook TEXT NOT NULL,
        persona_note TEXT,
        analogy TEXT,
        emotional_goal TEXT,
        created_by TEXT NOT NULL,
        created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_emotional_entries_project
        ON project_emotional_entries(project_id);

    CREATE INDEX IF NOT EXISTS idx_emotional_entries_subchapter
        ON project_emotional_entries(subchapter_id);

    CREATE TABLE IF NOT EXISTS project_guideline_runs (
        project_id UUID PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
        batch JSONB NOT NULL,
        critique TEXT,
        summary TEXT,
        readiness TEXT NOT NULL DEFAULT 'draft',
        version INTEGER NOT NULL DEFAULT 1,
        updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
        approved_at TIMESTAMP WITHOUT TIME ZONE
    );

    CREATE TABLE IF NOT EXISTS project_guideline_packets (
        id UUID PRIMARY KEY,
        project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
        subchapter_id UUID NOT NULL,
        objectives JSONB NOT NULL,
        must_include_facts JSONB NOT NULL,
        emotional_beats JSONB NOT NULL,
        narrative_voice TEXT,
        structural_reminders JSONB NOT NULL,
        success_metrics JSONB NOT NULL,
        risks JSONB NOT NULL,
        status TEXT NOT NULL,
        created_by TEXT NOT NULL,
        version INTEGER NOT NULL,
        created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_guideline_packets_project
        ON project_guideline_packets(project_id);

    CREATE INDEX IF NOT EXISTS idx_guideline_packets_subchapter
        ON project_guideline_packets(subchapter_id);

    CREATE TABLE IF NOT EXISTS project_writing_runs (
        project_id UUID PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
        batch JSONB NOT NULL,
        summary TEXT,
        critique TEXT,
        readiness TEXT NOT NULL DEFAULT 'draft',
        cycle_count INTEGER NOT NULL DEFAULT 3,
        total_word_count INTEGER,
        updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS project_writing_iterations (
        id UUID PRIMARY KEY,
        project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
        subchapter_id UUID NOT NULL,
        cycle INTEGER NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        summary TEXT,
        word_count INTEGER,
        feedback JSONB NOT NULL,
        created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_writing_iterations_project
        ON project_writing_iterations(project_id);

    CREATE INDEX IF NOT EXISTS idx_writing_iterations_subchapter
        ON project_writing_iterations(subchapter_id);

    CREATE TABLE IF NOT EXISTS agent_stage_metrics (
        stage TEXT PRIMARY KEY,
        total_runs BIGINT NOT NULL DEFAULT 0,
        total_prompt_tokens BIGINT NOT NULL DEFAULT 0,
        total_completion_tokens BIGINT NOT NULL DEFAULT 0,
        total_latency_ms DOUBLE PRECISION NOT NULL DEFAULT 0,
        total_cost_usd DOUBLE PRECISION NOT NULL DEFAULT 0,
        updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
    );
    """
    with POOL.connection() as conn, conn.cursor() as cur:
        cur.execute(ddl)
        conn.commit()


def _fetch_categories() -> list[Category]:
    with POOL.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT id, name, color_hex FROM categories ORDER BY name ASC")
        return [Category(**row) for row in cur.fetchall()]


def _insert_category(payload: CategoryCreateRequest) -> Category:
    with POOL.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            INSERT INTO categories (name, color_hex)
            VALUES (%s, %s)
            RETURNING id, name, color_hex
            """,
            (payload.name, payload.color_hex),
        )
        row = cur.fetchone()
        conn.commit()
    if row is None:  # pragma: no cover - unexpected DB state
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create category")
    return Category(**row)


def _fetch_projects(user: SessionUser) -> list[ProjectSummary]:
    base_query = """
        SELECT
            p.id,
            p.title,
            p.idea_summary,
            p.research_guidelines,
            p.stage::text AS stage,
            p.last_updated,
            p.total_cost_cents,
            p.spend_limit_cents,
            c.id AS category_id,
            c.name AS category_name,
            c.color_hex AS category_color,
            COALESCE(g.readiness = 'ready', false) AS guidelines_ready,
            g.version AS guideline_version,
            g.updated_at AS guideline_updated_at,
            COALESCE(w.readiness = 'ready', false) AS writing_ready,
            w.updated_at AS writing_updated_at
        FROM projects p
        LEFT JOIN categories c ON c.id = p.category_id
        LEFT JOIN project_guideline_runs g ON g.project_id = p.id
        LEFT JOIN project_writing_runs w ON w.project_id = p.id
    """

    params: tuple[Any, ...] = ()
    if _is_admin_user(user):
        query = base_query + " ORDER BY p.last_updated DESC"
    else:
        query = (
            base_query
            + " JOIN project_members pm ON pm.project_id = p.id WHERE pm.user_id = %s ORDER BY p.last_updated DESC"
        )
        params = (user.id,)

    with POOL.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, params)
        rows = cur.fetchall()
    return [_row_to_project_summary(row) for row in rows]


def _fetch_project_summary(project_id: UUID) -> Optional[ProjectSummary]:
    query = """
        SELECT
            p.id,
            p.title,
            p.idea_summary,
            p.research_guidelines,
            p.stage::text AS stage,
            p.last_updated,
            p.total_cost_cents,
            p.spend_limit_cents,
            c.id AS category_id,
            c.name AS category_name,
            c.color_hex AS category_color,
            COALESCE(g.readiness = 'ready', false) AS guidelines_ready,
            g.version AS guideline_version,
            g.updated_at AS guideline_updated_at,
            COALESCE(w.readiness = 'ready', false) AS writing_ready,
            w.updated_at AS writing_updated_at
        FROM projects p
        LEFT JOIN categories c ON c.id = p.category_id
        LEFT JOIN project_guideline_runs g ON g.project_id = p.id
        LEFT JOIN project_writing_runs w ON w.project_id = p.id
        WHERE p.id = %s
    """
    with POOL.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, (project_id,))
        row = cur.fetchone()
    if not row:
        return None
    return _row_to_project_summary(row)


def _insert_project(payload: IdeaIntakeRequest, user_id: UUID) -> UUID:
    project_id = uuid4()
    title = (payload.working_title or "Untitled Project").strip() or "Untitled Project"
    with POOL.connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO projects (id, title, category_id, idea_summary, research_guidelines)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                project_id,
                title,
                payload.category_id,
                payload.description.strip(),
                (payload.research_guidelines or "").strip() or None,
            ),
        )
        cur.execute(
            """
            INSERT INTO project_members (project_id, user_id, role)
            VALUES (%s, %s, 'owner')
            ON CONFLICT (project_id, user_id) DO UPDATE SET role = 'owner'
            """,
            (project_id, user_id),
        )
        conn.commit()
    return project_id


def _mark_project_failed(project_id: UUID) -> None:
    with POOL.connection() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE projects SET last_updated = NOW() WHERE id = %s",
            (project_id,),
        )
        conn.commit()


async def _run_structure_stage(project_id: UUID, idea_text: str) -> None:
    stage_name = BookStage.STRUCTURE.value
    await _guard_project_budget(project_id)
    start_time = perf_counter()
    outcome = "success"
    with log_context(project_id=str(project_id), stage=stage_name):
        logger.info("Submitting structure stage to orchestrator")
        try:
            payload = {
                "project_id": str(project_id),
                "stages": [
                    {
                        "stage": stage_name,
                        "prompt": idea_text,
                    }
                ],
            }
            async with httpx.AsyncClient(
                base_url=ORCHESTRATOR_URL,
                timeout=ORCHESTRATOR_TIMEOUT_SECONDS,
            ) as client:
                response = await client.post("/orchestrator/run", json=payload)
            response.raise_for_status()
            data = response.json()
            stages = data.get("stages", [])
            if not stages:
                raise httpx.HTTPError("Orchestrator returned no stage output")

            stage_result = next(
                (stage for stage in stages if stage.get("stage") == stage_name),
                stages[0],
            )
            structure = stage_result.get("structured_output")
            if not isinstance(structure, dict):
                raise httpx.HTTPError("Structured output missing for structure stage")
            critiques = stage_result.get("extras", {}).get("critiques", [])
            summary = stage_result.get("output", "")

            await run_in_threadpool(
                _save_structure_result,
                project_id,
                structure,
                summary,
                critiques,
            )
            await run_in_threadpool(
                _record_stage_metrics,
                BookStage.STRUCTURE,
                stage_result,
            )
            await run_in_threadpool(_apply_stage_cost, project_id, stage_result)
            logger.info(
                "Structure stage persisted",
                extra={
                    "model": stage_result.get("model"),
                    "prompt_tokens": int(stage_result.get("prompt_tokens") or 0),
                    "completion_tokens": int(stage_result.get("completion_tokens") or 0),
                    "latency_ms": float(stage_result.get("latency_ms") or 0.0),
                    "critique_count": len(critiques),
                },
            )
        except Exception:
            outcome = "error"
            logger.exception("Structure stage execution failed")
            raise
        finally:
            observe_stage_duration(
                stage=stage_name,
                duration_seconds=perf_counter() - start_time,
                service_name=SERVICE_NAME,
                status=outcome,
            )


def _save_structure_result(project_id: UUID, structure: dict[str, Any], summary: str, critiques: list[str]) -> None:
    with POOL.connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO project_structures (project_id, structure, summary, critiques, updated_at)
            VALUES (%s, %s, %s, %s, NOW())
            ON CONFLICT (project_id) DO UPDATE
            SET structure = EXCLUDED.structure,
                summary = EXCLUDED.summary,
                critiques = EXCLUDED.critiques,
                updated_at = NOW()
            """,
            (project_id, structure, summary, critiques),
        )
        cur.execute(
            """
            UPDATE projects
            SET stage = %s,
                last_updated = NOW()
            WHERE id = %s
            """,
            (BookStage.STRUCTURE.value, project_id),
        )
        conn.commit()


async def _run_title_stage(project_id: UUID) -> None:
    stage_name = BookStage.TITLE.value
    start_time = perf_counter()
    outcome = "success"
    with log_context(project_id=str(project_id), stage=stage_name):
        logger.info("Submitting title stage to orchestrator")
        try:
            structure_payload = _fetch_structure_payload(project_id)
            if structure_payload is None:
                raise httpx.HTTPError("Structure must be generated before title ideation")

            synopsis = (
                (structure_payload.get("summary") or "").strip()
                or (
                    (structure_payload.get("structure") or {}).get("synopsis")
                    if isinstance(structure_payload.get("structure"), dict)
                    else None
                )
                or (structure_payload.get("idea_summary") or "").strip()
            )
            if not synopsis:
                raise httpx.HTTPError("Synopsis unavailable for title generation")

            await _guard_project_budget(project_id)

            payload = {
                "project_id": str(project_id),
                "stages": [
                    {
                        "stage": stage_name,
                        "prompt": synopsis,
                    }
                ],
            }
            async with httpx.AsyncClient(
                base_url=ORCHESTRATOR_URL,
                timeout=ORCHESTRATOR_TIMEOUT_SECONDS,
            ) as client:
                response = await client.post("/orchestrator/run", json=payload)
            response.raise_for_status()
            data = response.json()
            stages = data.get("stages", [])
            if not stages:
                raise httpx.HTTPError("Orchestrator returned no stage output")
            stage_result = next(
                (stage for stage in stages if stage.get("stage") == stage_name),
                stages[0],
            )
            batch_payload = stage_result.get("structured_output")
            if not isinstance(batch_payload, dict):
                raise httpx.HTTPError("Structured output missing for title stage")
            batch = TitleBatch.model_validate(batch_payload)
            critique = stage_result.get("extras", {}).get("critique")

            await run_in_threadpool(_save_title_result, project_id, batch, critique)
            await run_in_threadpool(_record_stage_metrics, BookStage.TITLE, stage_result)
            await run_in_threadpool(_apply_stage_cost, project_id, stage_result)
            logger.info(
                "Title stage persisted",
                extra={
                    "model": stage_result.get("model"),
                    "prompt_tokens": int(stage_result.get("prompt_tokens") or 0),
                    "completion_tokens": int(stage_result.get("completion_tokens") or 0),
                    "latency_ms": float(stage_result.get("latency_ms") or 0.0),
                    "option_count": len(batch.options),
                },
            )
        except Exception:
            outcome = "error"
            logger.exception("Title stage execution failed")
            raise
        finally:
            observe_stage_duration(
                stage=stage_name,
                duration_seconds=perf_counter() - start_time,
                service_name=SERVICE_NAME,
                status=outcome,
            )


async def _parse_research_document(
    filename: str, content_base64: str, prompt_index: int | None
) -> dict[str, Any]:
    request_payload = {
        "filename": filename,
        "content_base64": content_base64,
        "prompt_index": prompt_index,
    }
    async with httpx.AsyncClient(base_url=DOC_PARSER_URL, timeout=DOC_PARSER_TIMEOUT_SECONDS) as client:
        response = await client.post("/parse", json=request_payload)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):  # pragma: no cover - defensive guard
        raise httpx.HTTPError("Document parser returned unexpected payload")
    return data


def _fetch_project_core(project_id: UUID) -> Optional[dict[str, Any]]:
    query = """
        SELECT id, title, idea_summary, research_guidelines, stage::text AS stage
        FROM projects
        WHERE id = %s
    """
    with POOL.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, (project_id,))
        return cur.fetchone()


def _fetch_structure_payload(project_id: UUID) -> Optional[dict[str, Any]]:
    query = """
        SELECT
            p.idea_summary,
            p.research_guidelines,
            s.structure,
            s.summary
        FROM project_structures s
        JOIN projects p ON p.id = s.project_id
        WHERE s.project_id = %s
    """
    with POOL.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, (project_id,))
        return cur.fetchone()


def _save_research_upload_file(
    project_id: UUID,
    prompt_index: int,
    filename: str,
    content: bytes,
) -> tuple[str, str]:
    os.makedirs(RESEARCH_UPLOADS_DIR, exist_ok=True)
    safe_name = filename.strip().replace("/", "-").replace("\\", "-") or "upload.docx"
    storage_path = os.path.join(
        RESEARCH_UPLOADS_DIR,
        f"{project_id}-{prompt_index}-{safe_name}",
    )
    encrypted_content = FERNET.encrypt(content)
    with open(storage_path, "wb") as handle:
        handle.write(encrypted_content)
    return storage_path, safe_name


def _save_title_result(project_id: UUID, batch: TitleBatch, critique: Optional[str]) -> None:
    batch_json = batch.model_dump(mode="json")
    with POOL.connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO project_titles (project_id, batch, critique, shortlist, selected_title, updated_at, approved_at)
            VALUES (%s, %s, %s, '[]'::jsonb, NULL, NOW(), NULL)
            ON CONFLICT (project_id) DO UPDATE
            SET batch = EXCLUDED.batch,
                critique = EXCLUDED.critique,
                shortlist = '[]'::jsonb,
                selected_title = NULL,
                updated_at = NOW(),
                approved_at = NULL
            """,
            (project_id, batch_json, critique),
        )
        conn.commit()


async def _handle_research_upload(project_id: UUID, payload: ResearchUploadRequest) -> ResearchDetail:
    stage_name = BookStage.RESEARCH.value
    with log_context(project_id=str(project_id), stage=stage_name):
        logger.info(
            "Received research upload",
            extra={
                "filename": payload.filename,
                "prompt_index": payload.prompt_index,
            },
        )
        try:
            raw_bytes = base64.b64decode(payload.content_base64)
        except (binascii.Error, ValueError) as exc:
            logger.exception("Failed to decode uploaded research document")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid document encoding") from exc

        storage_path, safe_filename = await run_in_threadpool(
            _save_research_upload_file,
            project_id,
            payload.prompt_index,
            payload.filename,
            raw_bytes,
        )
        logger.info("Stored research upload", extra={"storage_path": storage_path})

        parse_result = await _parse_research_document(
            payload.filename,
            payload.content_base64,
            payload.prompt_index,
        )

        facts = parse_result.get("facts") or []
        logger.info(
            "Parsed research upload",
            extra={
                "fact_count": len(facts),
                "word_count": int(parse_result.get("word_count") or 0),
                "paragraph_count": int(parse_result.get("paragraph_count") or 0),
            },
        )

        ready_for_mapping = await run_in_threadpool(
            _record_research_upload,
            project_id,
            payload.prompt_index,
            safe_filename,
            storage_path,
            payload.notes,
            parse_result,
        )

        logger.info(
            "Research upload recorded",
            extra={"ready_for_mapping": ready_for_mapping},
        )

        if ready_for_mapping:
            try:
                await _run_fact_mapping_stage(project_id)
            except httpx.HTTPError:
                logger.warning("Fact mapping stage failed after research upload", exc_info=True)

        detail = await run_in_threadpool(_fetch_research_detail, project_id)
        if detail is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Research prompts unavailable")
        return detail


def _record_research_upload(
    project_id: UUID,
    prompt_index: int,
    filename: str,
    storage_path: str,
    notes: Optional[str],
    parse_result: dict[str, Any],
) -> bool:
    facts = parse_result.get("facts") or []
    word_count = int(parse_result.get("word_count") or 0)
    paragraph_count = int(parse_result.get("paragraph_count") or len(facts))

    with POOL.connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO project_research_uploads (project_id, prompt_index, filename, storage_path, notes, uploaded_at, word_count, paragraph_count)
            VALUES (%s, %s, %s, %s, %s, NOW(), %s, %s)
            RETURNING id
            """,
            (
                project_id,
                prompt_index,
                filename,
                storage_path,
                notes,
                word_count,
                paragraph_count,
            ),
        )
        upload_id = cur.fetchone()[0]

        for fact in facts:
            detail = (fact.get("detail") or "").strip()
            if not detail:
                continue
            summary = (fact.get("summary") or detail[:160]).strip()
            citation_payload = fact.get("citation") or {}
            cur.execute(
                """
                INSERT INTO project_research_fact_candidates (id, project_id, upload_id, prompt_index, source_filename, summary, detail, citation, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, NOW())
                """,
                (
                    uuid4(),
                    project_id,
                    upload_id,
                    prompt_index,
                    filename,
                    summary,
                    detail,
                    json.dumps(citation_payload),
                ),
            )

        # Determine whether all prompts now have uploads
        cur.execute(
            "SELECT prompts FROM project_research_prompts WHERE project_id = %s",
            (project_id,),
        )
        row = cur.fetchone()
        prompt_count = 0
        if row and row[0]:
            prompts_content = row[0]
            if isinstance(prompts_content, dict):
                prompt_count = len(prompts_content.get("prompts", []))

        cur.execute(
            "SELECT COUNT(DISTINCT prompt_index) FROM project_research_uploads WHERE project_id = %s",
            (project_id,),
        )
        uploaded_count = cur.fetchone()[0] or 0

        ready_for_mapping = bool(prompt_count and uploaded_count >= prompt_count)
        if ready_for_mapping:
            cur.execute(
                """
                UPDATE projects
                SET stage = %s,
                    last_updated = NOW()
                WHERE id = %s
                """,
                (BookStage.FACT_MAPPING.value, project_id),
            )

        conn.commit()

    return ready_for_mapping


def _fetch_title_detail(project_id: UUID) -> Optional[TitleDetail]:
    query = """
        SELECT
            p.id,
            p.title,
            p.idea_summary,
            p.stage::text AS stage,
            p.last_updated,
            p.total_cost_cents,
            p.spend_limit_cents,
            c.id AS category_id,
            c.name AS category_name,
            c.color_hex AS category_color,
            t.batch,
            t.critique,
            t.shortlist,
            t.selected_title,
            t.updated_at
        FROM projects p
        LEFT JOIN categories c ON c.id = p.category_id
        JOIN project_titles t ON t.project_id = p.id
        WHERE p.id = %s
    """
    with POOL.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, (project_id,))
        row = cur.fetchone()
    if not row:
        return None

    project = _row_to_project_summary(row)
    try:
        batch = TitleBatch.model_validate(row["batch"])
    except Exception as exc:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Stored title batch invalid") from exc

    shortlist = row["shortlist"] or []
    if not isinstance(shortlist, list):
        shortlist = []

    options = [TitleOptionModel(title=option.title, rationale=option.rationale) for option in batch.options]
    return TitleDetail(
        project=project,
        options=options,
        shortlist=[str(item) for item in shortlist],
        selected_title=row.get("selected_title"),
        critique=row.get("critique"),
        updated_at=row["updated_at"],
    )


def _update_title_shortlist(project_id: UUID, shortlist: list[str]) -> None:
    with POOL.connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            UPDATE project_titles
            SET shortlist = %s::jsonb,
                updated_at = NOW()
            WHERE project_id = %s
            """,
            (json.dumps(list(dict.fromkeys(shortlist))), project_id),  # remove duplicates, preserve order
        )
        if cur.rowcount == 0:
            conn.rollback()
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project titles not found")
        conn.commit()


def _select_title(project_id: UUID, title: str) -> None:
    with POOL.connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            UPDATE project_titles
            SET selected_title = %s,
                approved_at = NOW(),
                updated_at = NOW()
            WHERE project_id = %s
            """,
            (title, project_id),
        )
        if cur.rowcount == 0:
            conn.rollback()
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project titles not found")
        conn.commit()
    result = _update_project_stage(project_id, BookStage.RESEARCH)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")


async def _run_research_stage(project_id: UUID, guidelines_override: str | None) -> None:
    stage_name = BookStage.RESEARCH.value
    start_time = perf_counter()
    outcome = "success"
    with log_context(project_id=str(project_id), stage=stage_name):
        logger.info("Submitting research stage to orchestrator")
        try:
            structure_payload = _fetch_structure_payload(project_id)
            if structure_payload is None:
                raise httpx.HTTPError("Structure must be generated before research planning")

            structure = structure_payload.get("structure") if isinstance(structure_payload, dict) else None
            structure_summary = _summarise_structure(structure)
            synopsis = (
                (structure_payload.get("summary") if isinstance(structure_payload, dict) else None)
                or (structure.get("synopsis") if isinstance(structure, dict) else None)
                or (structure_payload.get("idea_summary") if isinstance(structure_payload, dict) else "")
            )
            guidelines = (
                guidelines_override
                if guidelines_override is not None
                else (
                    structure_payload.get("research_guidelines")
                    if isinstance(structure_payload, dict)
                    else None
                )
            ) or ""

            request_payload = {
                "synopsis": synopsis,
                "structure_summary": structure_summary,
                "guidelines": guidelines,
            }

            await _guard_project_budget(project_id)

            async with httpx.AsyncClient(
                base_url=ORCHESTRATOR_URL,
                timeout=ORCHESTRATOR_TIMEOUT_SECONDS,
            ) as client:
                response = await client.post(
                    "/orchestrator/run",
                    json={
                        "project_id": str(project_id),
                        "stages": [
                            {
                                "stage": stage_name,
                                "prompt": json.dumps(request_payload),
                            }
                        ],
                    },
                )
            response.raise_for_status()
            data = response.json()
            stages = data.get("stages", [])
            if not stages:
                raise httpx.HTTPError("Orchestrator returned no stage output")
            stage_result = next(
                (stage for stage in stages if stage.get("stage") == stage_name),
                stages[0],
            )
            batch_payload = stage_result.get("structured_output")
            if not isinstance(batch_payload, dict):
                raise httpx.HTTPError("Structured output missing for research stage")
            critique = stage_result.get("extras", {}).get("critique")

            await run_in_threadpool(
                _save_research_prompts,
                project_id,
                batch_payload,
                critique,
                guidelines,
            )
            await run_in_threadpool(
                _record_stage_metrics,
                BookStage.RESEARCH,
                stage_result,
            )
            await run_in_threadpool(_apply_stage_cost, project_id, stage_result)
            logger.info(
                "Research stage persisted",
                extra={
                    "model": stage_result.get("model"),
                    "prompt_tokens": int(stage_result.get("prompt_tokens") or 0),
                    "completion_tokens": int(stage_result.get("completion_tokens") or 0),
                    "latency_ms": float(stage_result.get("latency_ms") or 0.0),
                },
            )
        except Exception:
            outcome = "error"
            logger.exception("Research stage execution failed")
            raise
        finally:
            observe_stage_duration(
                stage=stage_name,
                duration_seconds=perf_counter() - start_time,
                service_name=SERVICE_NAME,
                status=outcome,
            )


def _save_research_prompts(
    project_id: UUID,
    batch_payload: dict[str, Any],
    critique: Optional[str],
    guidelines: str,
) -> None:
    prompts_json = json.dumps(batch_payload)
    with POOL.connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO project_research_prompts (project_id, prompts, critique, guidelines, updated_at)
            VALUES (%s, %s::jsonb, %s, %s, NOW())
            ON CONFLICT (project_id) DO UPDATE
            SET prompts = EXCLUDED.prompts,
                critique = EXCLUDED.critique,
                guidelines = EXCLUDED.guidelines,
                updated_at = NOW()
            """,
            (project_id, prompts_json, critique, guidelines or None),
        )
        cur.execute("DELETE FROM project_research_uploads WHERE project_id = %s", (project_id,))
        cur.execute(
            "DELETE FROM project_research_fact_candidates WHERE project_id = %s",
            (project_id,),
        )
        cur.execute(
            "DELETE FROM project_research_facts WHERE project_id = %s",
            (project_id,),
        )
        cur.execute("DELETE FROM project_fact_mapping WHERE project_id = %s", (project_id,))
        cur.execute(
            """
            UPDATE projects
            SET stage = %s,
                research_guidelines = COALESCE(%s, research_guidelines),
                last_updated = NOW()
            WHERE id = %s
            """,
            (BookStage.RESEARCH.value, guidelines or None, project_id),
        )
        conn.commit()


def _fetch_research_detail(project_id: UUID) -> ResearchDetail | None:
    query = """
        SELECT
            p.id,
            p.title,
            p.idea_summary,
            p.research_guidelines,
            p.stage::text AS stage,
            p.last_updated,
            p.total_cost_cents,
            p.spend_limit_cents,
            c.id AS category_id,
            c.name AS category_name,
            c.color_hex AS category_color,
            r.prompts,
            r.critique,
            r.guidelines AS stored_guidelines
        FROM projects p
        LEFT JOIN categories c ON c.id = p.category_id
        JOIN project_research_prompts r ON r.project_id = p.id
        WHERE p.id = %s
    """
    with POOL.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, (project_id,))
        row = cur.fetchone()
    if not row:
        return None

    project = _row_to_project_summary(row)
    prompts_raw = row.get("prompts") or {}
    prompts_list = prompts_raw.get("prompts") if isinstance(prompts_raw, dict) else None
    if prompts_list is None:
        prompts_list = []
    prompts = [
        ResearchPromptModel(
            focus_summary=item.get("focus_summary", ""),
            focus_subchapters=[str(sub) for sub in item.get("focus_subchapters", [])],
            prompt_text=item.get("prompt_text", ""),
            desired_sources=[str(src) for src in item.get("desired_sources", [])],
            additional_notes=item.get("additional_notes"),
        )
        for item in prompts_list
    ]
    uploads = _fetch_research_uploads(project_id)
    guidelines = row.get("stored_guidelines") or project.research_guidelines

    return ResearchDetail(
        project=project,
        prompts=prompts,
        critique=row.get("critique"),
        guidelines=guidelines,
        uploads=uploads,
    )


def _build_fact_mapping_payload(project_id: UUID) -> Optional[dict[str, Any]]:
    structure_payload = _fetch_structure_payload(project_id)
    if not structure_payload:
        return None
    structure = structure_payload.get("structure")
    if not structure:
        return None

    with POOL.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT id, upload_id, prompt_index, source_filename, summary, detail, citation
            FROM project_research_fact_candidates
            WHERE project_id = %s
            ORDER BY created_at ASC
            """,
            (project_id,),
        )
        candidate_rows = cur.fetchall()

    if not candidate_rows:
        return None

    candidates: list[dict[str, Any]] = []
    for row in candidate_rows:
        candidate_data = {
            "id": str(row["id"]),
            "project_id": str(project_id),
            "upload_id": row.get("upload_id"),
            "prompt_index": row.get("prompt_index"),
            "source_filename": row.get("source_filename"),
            "summary": row.get("summary", ""),
            "detail": row.get("detail", ""),
            "citation": row.get("citation") or {},
        }
        candidate = ResearchFactCandidate.model_validate(candidate_data)
        candidates.append(candidate.model_dump(mode="json"))

    return {
        "project_id": str(project_id),
        "structure": structure,
        "candidates": candidates,
    }


async def _run_fact_mapping_stage(project_id: UUID) -> None:
    stage_name = BookStage.FACT_MAPPING.value
    payload = await run_in_threadpool(_build_fact_mapping_payload, project_id)
    if not payload:
        with log_context(project_id=str(project_id), stage=stage_name):
            logger.info("Skipping fact mapping stage until research uploads complete")
        return

    await _guard_project_budget(project_id)

    start_time = perf_counter()
    outcome = "success"
    with log_context(project_id=str(project_id), stage=stage_name):
        logger.info("Submitting fact mapping stage to orchestrator")
        try:
            async with httpx.AsyncClient(
                base_url=ORCHESTRATOR_URL,
                timeout=ORCHESTRATOR_TIMEOUT_SECONDS,
            ) as client:
                response = await client.post(
                    "/orchestrator/run",
                    json={
                        "project_id": str(project_id),
                        "stages": [
                            {
                                "stage": stage_name,
                                "prompt": json.dumps(payload),
                            }
                        ],
                    },
                )
            response.raise_for_status()
            data = response.json()
            stages = data.get("stages", [])
            if not stages:
                raise httpx.HTTPError("Orchestrator returned no stage output")
            stage_result = next(
                (stage for stage in stages if stage.get("stage") == stage_name),
                stages[0],
            )
            await run_in_threadpool(
                _store_fact_mapping_result,
                project_id,
                stage_result,
            )
            await run_in_threadpool(
                _record_stage_metrics,
                BookStage.FACT_MAPPING,
                stage_result,
            )
            await run_in_threadpool(_apply_stage_cost, project_id, stage_result)
            logger.info(
                "Fact mapping stage persisted",
                extra={
                    "model": stage_result.get("model"),
                    "prompt_tokens": int(stage_result.get("prompt_tokens") or 0),
                    "completion_tokens": int(stage_result.get("completion_tokens") or 0),
                    "latency_ms": float(stage_result.get("latency_ms") or 0.0),
                    "fact_count": len((stage_result.get("structured_output") or {}).get("facts", [])),
                },
            )
        except Exception:
            outcome = "error"
            logger.exception("Fact mapping stage execution failed")
            raise
        finally:
            observe_stage_duration(
                stage=stage_name,
                duration_seconds=perf_counter() - start_time,
                service_name=SERVICE_NAME,
                status=outcome,
            )


def _store_fact_mapping_result(project_id: UUID, stage_result: dict[str, Any]) -> None:
    structured_output = stage_result.get("structured_output")
    if not isinstance(structured_output, dict):
        raise httpx.HTTPError("Structured output missing for fact mapping stage")

    batch = FactMappingBatch.model_validate(structured_output)
    extras = stage_result.get("extras") or {}
    if not batch.coverage and extras.get("coverage"):
        batch.coverage = [
            SubchapterFactCoverage.model_validate(item)
            for item in extras.get("coverage", [])
            if item
        ]

    facts_payload = [fact for fact in batch.facts]
    with POOL.connection() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM project_research_facts WHERE project_id = %s", (project_id,))
        for fact in facts_payload:
            # Ensure UUID instances
            fact_id = UUID(str(fact.id))
            subchapter_id = UUID(str(fact.subchapter_id))
            citation_json = json.dumps(
                fact.citation.model_dump(mode="json"), ensure_ascii=False
            )
            cur.execute(
                """
                INSERT INTO project_research_facts (id, project_id, subchapter_id, upload_id, prompt_index, summary, detail, citation, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, NOW())
                """,
                (
                    fact_id,
                    project_id,
                    subchapter_id,
                    fact.upload_id,
                    fact.prompt_index,
                    fact.summary,
                    fact.detail,
                    citation_json,
                ),
            )

        coverage_payload = [
            item.model_dump(mode="json") for item in (batch.coverage or [])
        ]
        cur.execute(
            """
            INSERT INTO project_fact_mapping (project_id, batch, coverage, critique, updated_at)
            VALUES (%s, %s::jsonb, %s::jsonb, %s, NOW())
            ON CONFLICT (project_id) DO UPDATE
            SET batch = EXCLUDED.batch,
                coverage = EXCLUDED.coverage,
                critique = EXCLUDED.critique,
                updated_at = NOW()
            """,
            (
                project_id,
                json.dumps(batch.model_dump(mode="json"), ensure_ascii=False),
                json.dumps(coverage_payload, ensure_ascii=False),
                extras.get("critique"),
            ),
        )

        cur.execute(
            """
            UPDATE projects
            SET stage = %s,
                last_updated = NOW()
            WHERE id = %s
            """,
            (BookStage.EMOTIONAL.value, project_id),
        )
        conn.commit()


def _fetch_fact_mapping_detail(project_id: UUID) -> Optional[FactMappingDetail]:
    query = """
        SELECT
            p.id,
            p.title,
            p.idea_summary,
            p.research_guidelines,
            p.stage::text AS stage,
            p.last_updated,
            p.total_cost_cents,
            p.spend_limit_cents,
            c.id AS category_id,
            c.name AS category_name,
            c.color_hex AS category_color,
            fm.coverage,
            fm.critique,
            fm.updated_at
        FROM project_fact_mapping fm
        JOIN projects p ON p.id = fm.project_id
        LEFT JOIN categories c ON c.id = p.category_id
        WHERE p.id = %s
    """
    with POOL.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, (project_id,))
        row = cur.fetchone()
    if not row:
        return None

    project = _row_to_project_summary(row)
    coverage_payload = row.get("coverage") or []
    coverage: list[FactCoverageModel] = []
    for item in coverage_payload:
        if not item:
            continue
        coverage.append(
            FactCoverageModel(
                subchapter_id=UUID(str(item.get("subchapter_id"))),
                fact_count=int(item.get("fact_count") or 0),
            )
        )

    facts = _fetch_mapped_facts(project_id)
    return FactMappingDetail(
        project=project,
        facts=facts,
        coverage=coverage,
        critique=row.get("critique"),
        updated_at=row["updated_at"],
    )


def _fetch_emotional_layer_detail(project_id: UUID) -> Optional[EmotionalLayerDetail]:
    query = """
        SELECT
            p.id,
            p.title,
            p.idea_summary,
            p.research_guidelines,
            p.stage::text AS stage,
            p.last_updated,
            p.total_cost_cents,
            p.spend_limit_cents,
            c.id AS category_id,
            c.name AS category_name,
            c.color_hex AS category_color,
            ep.persona,
            ep.critique,
            ep.updated_at
        FROM project_emotional_persona ep
        JOIN projects p ON p.id = ep.project_id
        LEFT JOIN categories c ON c.id = p.category_id
        WHERE ep.project_id = %s
    """
    with POOL.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, (project_id,))
        row = cur.fetchone()
    if not row:
        return None

    project = _row_to_project_summary(row)
    persona_payload = row.get("persona") or {}
    if not persona_payload:
        return None

    persona = PersonaProfileModel(
        name=persona_payload.get("name", ""),
        background=persona_payload.get("background", ""),
        voice=persona_payload.get("voice", ""),
        signature_themes=[str(item) for item in persona_payload.get("signature_themes", []) if item],
        guiding_principles=[str(item) for item in persona_payload.get("guiding_principles", []) if item],
    )

    entries: list[EmotionalEntryModel] = []
    with POOL.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT id, subchapter_id, story_hook, persona_note, analogy, emotional_goal, created_by, created_at
            FROM project_emotional_entries
            WHERE project_id = %s
            ORDER BY created_at ASC
            """,
            (project_id,),
        )
        entry_rows = cur.fetchall()

    for entry in entry_rows:
        entries.append(
            EmotionalEntryModel(
                id=entry["id"],
                subchapter_id=entry["subchapter_id"],
                story_hook=entry["story_hook"],
                persona_note=entry.get("persona_note"),
                analogy=entry.get("analogy"),
                emotional_goal=entry.get("emotional_goal"),
                created_by=str(entry.get("created_by") or AgentRole.EMOTION_IMPLEMENTER.value),
                created_at=entry["created_at"],
            )
        )

    return EmotionalLayerDetail(
        project=project,
        persona=persona,
        entries=entries,
        critique=row.get("critique"),
        updated_at=row["updated_at"],
    )


def _fetch_mapped_facts(project_id: UUID) -> list[MappedFactModel]:
    query = """
        SELECT id, subchapter_id, summary, detail, citation, upload_id, prompt_index, created_at
        FROM project_research_facts
        WHERE project_id = %s
        ORDER BY created_at ASC
    """
    with POOL.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, (project_id,))
        rows = cur.fetchall()

    facts: list[MappedFactModel] = []
    for row in rows:
        citation_payload = row.get("citation") or {}
        citation_model = FactCitationModel(
            source_title=citation_payload.get("source_title") or "",
            author=citation_payload.get("author"),
            publication_date=citation_payload.get("publication_date"),
            url=citation_payload.get("url"),
            page=citation_payload.get("page"),
            source_type=citation_payload.get("source_type"),
        )
        facts.append(
            MappedFactModel(
                id=row["id"],
                subchapter_id=row["subchapter_id"],
                summary=row["summary"],
                detail=row["detail"],
                citation=citation_model,
                upload_id=row.get("upload_id"),
                prompt_index=row.get("prompt_index"),
                created_at=row["created_at"],
            )
        )
    return facts


def _build_emotional_payload(
    project_id: UUID, persona_preferences: Optional[str]
) -> Optional[dict[str, Any]]:
    structure_payload = _fetch_structure_payload(project_id)
    if not structure_payload:
        return None

    facts = _fetch_mapped_facts(project_id)
    if not facts:
        return None

    project = _fetch_project_core(project_id)
    if not project:
        return None

    persona_snapshot = _fetch_emotional_persona(project_id)
    selected_title = _fetch_selected_title(project_id) or project.get("title")

    structure = structure_payload.get("structure") or {}
    synopsis = (
        structure_payload.get("summary")
        or (structure.get("synopsis") if isinstance(structure, dict) else None)
        or project.get("idea_summary")
        or ""
    )

    facts_payload = [
        {
            "id": str(fact.id),
            "subchapter_id": str(fact.subchapter_id),
            "summary": fact.summary,
            "detail": fact.detail,
            "citation": fact.citation.model_dump(mode="json"),
        }
        for fact in facts
    ]

    payload: dict[str, Any] = {
        "project_id": str(project_id),
        "structure": structure,
        "facts": facts_payload,
        "title": selected_title or project.get("idea_summary") or "Untitled Manuscript",
        "synopsis": synopsis,
        "idea_summary": project.get("idea_summary") or synopsis,
        "research_guidelines": project.get("research_guidelines") or "",
        "persona_preferences": persona_preferences or None,
    }

    if persona_snapshot:
        payload["persona"] = persona_snapshot.get("persona")
        payload["previous_critique"] = persona_snapshot.get("critique")

    return payload


def _fetch_selected_title(project_id: UUID) -> Optional[str]:
    query = "SELECT selected_title FROM project_titles WHERE project_id = %s"
    with POOL.connection() as conn, conn.cursor() as cur:
        cur.execute(query, (project_id,))
        row = cur.fetchone()
    if row and row[0]:
        return row[0]
    query = "SELECT title FROM projects WHERE id = %s"
    with POOL.connection() as conn, conn.cursor() as cur:
        cur.execute(query, (project_id,))
        row = cur.fetchone()
    return row[0] if row and row[0] else None


def _fetch_emotional_persona(project_id: UUID) -> Optional[dict[str, Any]]:
    query = "SELECT persona, critique FROM project_emotional_persona WHERE project_id = %s"
    with POOL.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, (project_id,))
        row = cur.fetchone()
    return row if row else None


async def _run_emotional_stage(project_id: UUID, persona_preferences: Optional[str]) -> bool:
    stage_name = BookStage.EMOTIONAL.value
    payload = await run_in_threadpool(_build_emotional_payload, project_id, persona_preferences)
    if not payload:
        with log_context(project_id=str(project_id), stage=stage_name):
            logger.info("Skipping emotional stage until fact mapping is ready")
        return False

    start_time = perf_counter()
    outcome = "success"
    with log_context(project_id=str(project_id), stage=stage_name):
        logger.info("Submitting emotional stage to orchestrator")
        try:
            await _guard_project_budget(project_id)
            async with httpx.AsyncClient(
                base_url=ORCHESTRATOR_URL,
                timeout=ORCHESTRATOR_TIMEOUT_SECONDS,
            ) as client:
                response = await client.post(
                    "/orchestrator/run",
                    json={
                        "project_id": str(project_id),
                        "stages": [
                            {
                                "stage": stage_name,
                                "prompt": json.dumps(payload),
                            }
                        ],
                    },
                )
            response.raise_for_status()
            data = response.json()
            stages = data.get("stages", [])
            if not stages:
                raise httpx.HTTPError("Orchestrator returned no stage output")
            stage_result = next(
                (stage for stage in stages if stage.get("stage") == stage_name),
                stages[0],
            )
            structured_output = stage_result.get("structured_output")
            if not isinstance(structured_output, dict):
                raise httpx.HTTPError("Structured output missing for emotional stage")

            batch = EmotionalLayerBatch.model_validate(structured_output)
            critique = stage_result.get("extras", {}).get("critique")
            await run_in_threadpool(
                _save_emotional_layer_result,
                project_id,
                batch,
                critique,
            )
            await run_in_threadpool(
                _record_stage_metrics,
                BookStage.EMOTIONAL,
                stage_result,
            )
            await run_in_threadpool(_apply_stage_cost, project_id, stage_result)
            logger.info(
                "Emotional stage persisted",
                extra={
                    "model": stage_result.get("model"),
                    "prompt_tokens": int(stage_result.get("prompt_tokens") or 0),
                    "completion_tokens": int(stage_result.get("completion_tokens") or 0),
                    "latency_ms": float(stage_result.get("latency_ms") or 0.0),
                    "entry_count": len(batch.entries),
                },
            )
            return True
        except Exception:
            outcome = "error"
            logger.exception("Emotional stage execution failed")
            raise
        finally:
            observe_stage_duration(
                stage=stage_name,
                duration_seconds=perf_counter() - start_time,
                service_name=SERVICE_NAME,
                status=outcome,
            )


def _save_emotional_layer_result(
    project_id: UUID,
    batch: EmotionalLayerBatch,
    critique: Optional[str],
) -> None:
    persona_payload = batch.persona.model_dump(mode="json")
    entries = batch.entries or []

    with POOL.connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO project_emotional_persona (project_id, persona, critique, updated_at)
            VALUES (%s, %s::jsonb, %s, NOW())
            ON CONFLICT (project_id) DO UPDATE
            SET persona = EXCLUDED.persona,
                critique = EXCLUDED.critique,
                updated_at = NOW()
            """,
            (project_id, json.dumps(persona_payload, ensure_ascii=False), critique),
        )

        cur.execute("DELETE FROM project_emotional_entries WHERE project_id = %s", (project_id,))

        for entry in entries:
            created_by = entry.created_by.value if isinstance(entry.created_by, AgentRole) else str(entry.created_by)
            cur.execute(
                """
                INSERT INTO project_emotional_entries (
                    id, project_id, subchapter_id, story_hook, persona_note, analogy, emotional_goal, created_by, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    UUID(str(entry.id)),
                    project_id,
                    UUID(str(entry.subchapter_id)),
                    entry.story_hook,
                    entry.persona_note,
                    entry.analogy,
                    entry.emotional_goal,
                    created_by,
                    entry.created_at,
                ),
            )

        cur.execute(
            """
            UPDATE projects
            SET stage = %s,
                last_updated = NOW()
            WHERE id = %s
            """,
            (BookStage.GUIDELINES.value, project_id),
        )
        conn.commit()


def _fetch_guideline_packets(project_id: UUID) -> list[GuidelinePacketModel]:
    query = """
        SELECT
            id,
            subchapter_id,
            objectives,
            must_include_facts,
            emotional_beats,
            narrative_voice,
            structural_reminders,
            success_metrics,
            risks,
            status,
            created_by,
            version,
            created_at,
            updated_at
        FROM project_guideline_packets
        WHERE project_id = %s
        ORDER BY created_at ASC
    """
    with POOL.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, (project_id,))
        rows = cur.fetchall()

    packets: list[GuidelinePacketModel] = []
    for row in rows:
        objectives = [str(item) for item in row.get("objectives") or [] if item]
        emotional_beats = [str(item) for item in row.get("emotional_beats") or [] if item]
        structural_reminders = [str(item) for item in row.get("structural_reminders") or [] if item]
        success_metrics = [str(item) for item in row.get("success_metrics") or [] if item]
        risks = [str(item) for item in row.get("risks") or [] if item]

        fact_payloads = row.get("must_include_facts") or []
        fact_models: list[GuidelineFactModel] = []
        for fact in fact_payloads:
            if not fact:
                continue
            citation_payload = fact.get("citation") or {}
            fact_models.append(
                GuidelineFactModel(
                    fact_id=UUID(str(fact.get("fact_id"))),
                    summary=fact.get("summary", ""),
                    citation=FactCitationModel(
                        source_title=citation_payload.get("source_title") or "",
                        author=citation_payload.get("author"),
                        publication_date=citation_payload.get("publication_date"),
                        url=citation_payload.get("url"),
                        page=citation_payload.get("page"),
                        source_type=citation_payload.get("source_type"),
                    ),
                    rationale=fact.get("rationale"),
                )
            )

        packets.append(
            GuidelinePacketModel(
                id=row["id"],
                subchapter_id=row["subchapter_id"],
                objectives=objectives,
                must_include_facts=fact_models,
                emotional_beats=emotional_beats,
                narrative_voice=row.get("narrative_voice"),
                structural_reminders=structural_reminders,
                success_metrics=success_metrics,
                risks=risks,
                status=row.get("status") or "draft",
                created_by=str(row.get("created_by") or AgentRole.CREATIVE_DIRECTOR_FINAL.value),
                version=int(row.get("version") or 1),
                created_at=row.get("created_at"),
                updated_at=row.get("updated_at"),
            )
        )

    return packets


def _fetch_guideline_detail(project_id: UUID) -> Optional[GuidelineDetail]:
    query = """
        SELECT
            p.id,
            p.title,
            p.idea_summary,
            p.research_guidelines,
            p.stage::text AS stage,
            p.last_updated,
            p.total_cost_cents,
            p.spend_limit_cents,
            c.id AS category_id,
            c.name AS category_name,
            c.color_hex AS category_color,
            COALESCE(g.readiness = 'ready', false) AS guidelines_ready,
            g.version AS guideline_version,
            g.updated_at AS guideline_updated_at,
            g.summary AS guideline_summary,
            g.critique AS guideline_critique,
            g.readiness,
            g.version,
            g.updated_at
        FROM project_guideline_runs g
        JOIN projects p ON p.id = g.project_id
        LEFT JOIN categories c ON c.id = p.category_id
        WHERE g.project_id = %s
    """
    with POOL.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, (project_id,))
        row = cur.fetchone()
    if not row:
        return None

    project = _row_to_project_summary(row)
    packets = _fetch_guideline_packets(project_id)

    return GuidelineDetail(
        project=project,
        summary=row.get("guideline_summary"),
        critique=row.get("guideline_critique"),
        readiness=row.get("readiness") or "draft",
        version=int(row.get("version") or (project.guideline_version or 1)),
        guidelines=packets,
        updated_at=row["updated_at"],
    )


def _fetch_writing_detail(project_id: UUID) -> Optional[WritingDetail]:
    query = """
        SELECT
            p.id,
            p.title,
            p.idea_summary,
            p.research_guidelines,
            p.stage::text AS stage,
            p.last_updated,
            p.total_cost_cents,
            p.spend_limit_cents,
            c.id AS category_id,
            c.name AS category_name,
            c.color_hex AS category_color,
            COALESCE(g.readiness = 'ready', false) AS guidelines_ready,
            g.version AS guideline_version,
            g.updated_at AS guideline_updated_at,
            COALESCE(w.readiness = 'ready', false) AS writing_ready,
            w.updated_at AS writing_updated_at,
            w.summary AS writing_summary,
            w.critique AS writing_critique,
            w.readiness AS writing_readiness,
            w.cycle_count AS writing_cycle_count,
            w.total_word_count AS writing_total_word_count,
            w.batch AS writing_batch
        FROM project_writing_runs w
        JOIN projects p ON p.id = w.project_id
        LEFT JOIN categories c ON c.id = p.category_id
        LEFT JOIN project_guideline_runs g ON g.project_id = p.id
        WHERE w.project_id = %s
    """
    with POOL.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, (project_id,))
        row = cur.fetchone()
    if not row:
        return None

    project = _row_to_project_summary(row)
    batch_payload = row.get("writing_batch")
    if not isinstance(batch_payload, dict):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stored writing batch invalid",
        )

    batch = WritingBatch.model_validate(batch_payload)
    updates: dict[str, Any] = {}
    if row.get("writing_summary"):
        updates["summary"] = row.get("writing_summary")
    if row.get("writing_readiness"):
        updates["readiness"] = row.get("writing_readiness")
    if row.get("writing_cycle_count"):
        updates["cycle_count"] = int(row.get("writing_cycle_count"))
    if row.get("writing_total_word_count") is not None:
        updates["total_word_count"] = row.get("writing_total_word_count")
    if row.get("writing_updated_at"):
        updates["updated_at"] = row.get("writing_updated_at")

    if updates:
        batch = batch.model_copy(update=updates)

    return WritingDetail(project=project, batch=batch, critique=row.get("writing_critique"))


def _fetch_guideline_run_meta(project_id: UUID) -> Optional[dict[str, Any]]:
    query = "SELECT version, readiness, summary FROM project_guideline_runs WHERE project_id = %s"
    with POOL.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, (project_id,))
        row = cur.fetchone()
    return row if row else None


def _fetch_emotional_entries_for_guidelines(project_id: UUID) -> list[dict[str, Any]]:
    query = """
        SELECT subchapter_id, story_hook, persona_note, analogy, emotional_goal, created_by
        FROM project_emotional_entries
        WHERE project_id = %s
        ORDER BY created_at ASC
    """
    with POOL.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, (project_id,))
        rows = cur.fetchall()

    entries: list[dict[str, Any]] = []
    for row in rows:
        entries.append(
            {
                "subchapter_id": str(row.get("subchapter_id")),
                "story_hook": row.get("story_hook"),
                "persona_note": row.get("persona_note"),
                "analogy": row.get("analogy"),
                "emotional_goal": row.get("emotional_goal"),
                "created_by": row.get("created_by"),
            }
        )
    return entries


def _build_guidelines_payload(project_id: UUID, preferences: Optional[str]) -> Optional[dict[str, Any]]:
    structure_payload = _fetch_structure_payload(project_id)
    if not structure_payload:
        return None

    facts = _fetch_mapped_facts(project_id)
    if not facts:
        return None

    emotional_entries = _fetch_emotional_entries_for_guidelines(project_id)
    if not emotional_entries:
        return None

    persona_snapshot = _fetch_emotional_persona(project_id)
    if not persona_snapshot:
        return None

    project = _fetch_project_core(project_id)
    if not project:
        return None

    selected_title = _fetch_selected_title(project_id) or project.get("title")
    structure = structure_payload.get("structure") or {}
    synopsis = (
        structure_payload.get("summary")
        or (structure.get("synopsis") if isinstance(structure, dict) else None)
        or project.get("idea_summary")
        or ""
    )

    facts_payload = [
        {
            "id": str(fact.id),
            "subchapter_id": str(fact.subchapter_id),
            "summary": fact.summary,
            "detail": fact.detail,
            "citation": fact.citation.model_dump(mode="json"),
        }
        for fact in facts
    ]

    run_meta = _fetch_guideline_run_meta(project_id) or {}
    current_version = int(run_meta.get("version") or 0)

    payload: dict[str, Any] = {
        "project_id": str(project_id),
        "title": selected_title or project.get("idea_summary") or "Untitled Manuscript",
        "synopsis": synopsis,
        "structure": structure,
        "facts": facts_payload,
        "emotional_layer": emotional_entries,
        "persona": persona_snapshot.get("persona"),
        "preferences": preferences or None,
        "target_version": current_version + 1,
    }

    if persona_snapshot.get("critique"):
        payload["persona_critique"] = persona_snapshot.get("critique")

    return payload


def _fetch_existing_writing_batch(project_id: UUID) -> Optional[dict[str, Any]]:
    query = "SELECT batch FROM project_writing_runs WHERE project_id = %s"
    with POOL.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, (project_id,))
        row = cur.fetchone()
    return row.get("batch") if row and row.get("batch") else None


def _build_writing_payload(project_id: UUID, notes: Optional[str]) -> Optional[dict[str, Any]]:
    guideline_meta = _fetch_guideline_run_meta(project_id)
    if not guideline_meta or (guideline_meta.get("readiness") or "draft") != "ready":
        return None

    structure_payload = _fetch_structure_payload(project_id)
    if not structure_payload:
        return None

    guidelines = _fetch_guideline_packets(project_id)
    if not guidelines:
        return None

    project = _fetch_project_core(project_id)
    if not project:
        return None

    persona_snapshot = _fetch_emotional_persona(project_id)
    emotional_entries = _fetch_emotional_entries_for_guidelines(project_id)
    facts = _fetch_mapped_facts(project_id)

    structure_obj = structure_payload.get("structure") or {}
    subchapter_meta: list[dict[str, Any]] = []
    if isinstance(structure_obj, dict):
        for chapter in structure_obj.get("chapters", []):
            if not isinstance(chapter, dict):
                continue
            chapter_title = chapter.get("title")
            chapter_order = chapter.get("order") or 0
            for sub in chapter.get("subchapters", []):
                if not isinstance(sub, dict):
                    continue
                sub_id = sub.get("id")
                if not sub_id:
                    continue
                sub_order = sub.get("order") or 0
                order_label = f"{chapter_order}.{sub_order}" if chapter_order else str(sub_order)
                subchapter_meta.append(
                    {
                        "id": sub_id,
                        "title": sub.get("title") or "Untitled Subchapter",
                        "chapter_title": chapter_title,
                        "order_label": order_label,
                        "chapter_order": chapter_order,
                        "sub_order": sub_order,
                    }
                )

    guidelines_payload = [packet.model_dump(mode="json") for packet in guidelines]
    facts_payload = [fact.model_dump(mode="json") for fact in facts]

    selected_title = _fetch_selected_title(project_id) or project.get("title")
    synopsis = (
        structure_payload.get("summary")
        or (structure_obj.get("synopsis") if isinstance(structure_obj, dict) else None)
        or project.get("idea_summary")
        or ""
    )

    payload: dict[str, Any] = {
        "project_id": str(project_id),
        "title": selected_title or project.get("idea_summary") or "Untitled Manuscript",
        "synopsis": synopsis,
        "structure": structure_obj,
        "guidelines": guidelines_payload,
        "facts": facts_payload,
        "emotional_layer": emotional_entries,
        "subchapters": subchapter_meta,
        "notes": notes.strip() if notes else None,
        "cycle_count": 3,
    }

    if persona_snapshot and persona_snapshot.get("persona"):
        payload["persona"] = persona_snapshot.get("persona")
        if persona_snapshot.get("critique"):
            payload["persona_critique"] = persona_snapshot.get("critique")

    previous_batch = _fetch_existing_writing_batch(project_id)
    if previous_batch:
        payload["previous_batch"] = previous_batch

    return payload


def _save_guideline_result(
    project_id: UUID,
    batch: CreativeGuidelineBatch,
    critique: Optional[str],
) -> None:
    batch_json = batch.model_dump(mode="json")
    guidelines = batch.guidelines or []

    with POOL.connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO project_guideline_runs (project_id, batch, critique, summary, readiness, version, updated_at, approved_at)
            VALUES (%s, %s::jsonb, %s, %s, %s, %s, NOW(), %s)
            ON CONFLICT (project_id) DO UPDATE
            SET batch = EXCLUDED.batch,
                critique = EXCLUDED.critique,
                summary = EXCLUDED.summary,
                readiness = EXCLUDED.readiness,
                version = EXCLUDED.version,
                updated_at = NOW(),
                approved_at = EXCLUDED.approved_at
            """,
            (
                project_id,
                json.dumps(batch_json, ensure_ascii=False),
                critique,
                batch.summary,
                batch.readiness,
                batch.version,
                batch.approved_at,
            ),
        )

        cur.execute("DELETE FROM project_guideline_packets WHERE project_id = %s", (project_id,))

        for guideline in guidelines:
            fact_payload = [
                fact.model_dump(mode="json") if isinstance(fact, GuidelineFactReference) else fact
                for fact in guideline.must_include_facts
            ]
            cur.execute(
                """
                INSERT INTO project_guideline_packets (
                    id,
                    project_id,
                    subchapter_id,
                    objectives,
                    must_include_facts,
                    emotional_beats,
                    narrative_voice,
                    structural_reminders,
                    success_metrics,
                    risks,
                    status,
                    created_by,
                    version,
                    created_at,
                    updated_at
                )
                VALUES (%s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s, %s, %s, %s, %s)
                """,
                (
                    UUID(str(guideline.id)),
                    project_id,
                    UUID(str(guideline.subchapter_id)),
                    json.dumps(guideline.objectives, ensure_ascii=False),
                    json.dumps(fact_payload, ensure_ascii=False),
                    json.dumps(guideline.emotional_beats, ensure_ascii=False),
                    guideline.narrative_voice,
                    json.dumps(guideline.structural_reminders, ensure_ascii=False),
                    json.dumps(guideline.success_metrics, ensure_ascii=False),
                    json.dumps(guideline.risks, ensure_ascii=False),
                    guideline.status,
                    guideline.created_by.value if isinstance(guideline.created_by, AgentRole) else str(guideline.created_by),
                    guideline.version,
                    guideline.created_at,
                    guideline.updated_at,
                ),
            )

        next_stage = BookStage.WRITING.value if batch.readiness == "ready" else BookStage.GUIDELINES.value
        cur.execute(
            """
            UPDATE projects
            SET stage = %s,
                last_updated = NOW()
            WHERE id = %s
            """,
            (next_stage, project_id),
        )
        conn.commit()


async def _run_guidelines_stage(project_id: UUID, preferences: Optional[str]) -> bool:
    stage_name = BookStage.GUIDELINES.value
    payload = await run_in_threadpool(_build_guidelines_payload, project_id, preferences)
    if not payload:
        with log_context(project_id=str(project_id), stage=stage_name):
            logger.info("Skipping guidelines stage; prerequisites not ready")
        return False

    start_time = perf_counter()
    outcome = "success"
    with log_context(project_id=str(project_id), stage=stage_name):
        logger.info("Submitting guidelines stage to orchestrator")
        try:
            await _guard_project_budget(project_id)
            async with httpx.AsyncClient(
                base_url=ORCHESTRATOR_URL,
                timeout=ORCHESTRATOR_TIMEOUT_SECONDS,
            ) as client:
                response = await client.post(
                    "/orchestrator/run",
                    json={
                        "project_id": str(project_id),
                        "stages": [
                            {
                                "stage": stage_name,
                                "prompt": json.dumps(payload),
                            }
                        ],
                    },
                )

            response.raise_for_status()
            data = response.json()
            stages = data.get("stages", [])
            if not stages:
                raise httpx.HTTPError("Orchestrator returned no stage output")
            stage_result = next(
                (stage for stage in stages if stage.get("stage") == stage_name),
                stages[0],
            )
            structured_output = stage_result.get("structured_output")
            if not isinstance(structured_output, dict):
                raise httpx.HTTPError("Structured output missing for guidelines stage")

            batch = CreativeGuidelineBatch.model_validate(structured_output)
            extras = stage_result.get("extras") or {}
            critique = extras.get("critique")

            await run_in_threadpool(
                _save_guideline_result,
                project_id,
                batch,
                critique,
            )
            await run_in_threadpool(
                _record_stage_metrics,
                BookStage.GUIDELINES,
                stage_result,
            )
            await run_in_threadpool(_apply_stage_cost, project_id, stage_result)
            logger.info(
                "Guidelines stage persisted",
                extra={
                    "model": stage_result.get("model"),
                    "prompt_tokens": int(stage_result.get("prompt_tokens") or 0),
                    "completion_tokens": int(stage_result.get("completion_tokens") or 0),
                    "latency_ms": float(stage_result.get("latency_ms") or 0.0),
                    "guideline_count": len(batch.guidelines or []),
                    "readiness": batch.readiness,
                    "version": batch.version,
                },
            )
            return True
        except Exception:
            outcome = "error"
            logger.exception("Guidelines stage execution failed")
            raise
        finally:
            observe_stage_duration(
                stage=stage_name,
                duration_seconds=perf_counter() - start_time,
                service_name=SERVICE_NAME,
                status=outcome,
            )


def _save_writing_result(
    project_id: UUID,
    batch: WritingBatch,
    critique: Optional[str],
) -> None:
    batch_json = batch.model_dump(mode="json")
    subchapters = batch.subchapters or []

    with POOL.connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO project_writing_runs (project_id, batch, summary, critique, readiness, cycle_count, total_word_count, updated_at)
            VALUES (%s, %s::jsonb, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (project_id) DO UPDATE
            SET batch = EXCLUDED.batch,
                summary = EXCLUDED.summary,
                critique = EXCLUDED.critique,
                readiness = EXCLUDED.readiness,
                cycle_count = EXCLUDED.cycle_count,
                total_word_count = EXCLUDED.total_word_count,
                updated_at = NOW()
            """,
            (
                project_id,
                json.dumps(batch_json, ensure_ascii=False),
                batch.summary,
                critique,
                batch.readiness,
                batch.cycle_count,
                batch.total_word_count,
            ),
        )

        cur.execute("DELETE FROM project_writing_iterations WHERE project_id = %s", (project_id,))

        for subchapter in subchapters:
            sub_id = UUID(str(subchapter.subchapter_id))
            for iteration in subchapter.iterations or []:
                role_value = (
                    iteration.role.value
                    if isinstance(iteration.role, AgentRole)
                    else str(iteration.role)
                )
                feedback_payload: list[dict[str, Any]] = []
                for item in iteration.feedback or []:
                    if isinstance(item, DraftFeedbackItem):
                        feedback_payload.append(item.model_dump(mode="json"))
                    elif hasattr(item, "model_dump"):
                        feedback_payload.append(item.model_dump(mode="json"))
                    else:
                        feedback_payload.append(dict(item))

                summary_value = iteration.summary if iteration.summary else None
                cur.execute(
                    """
                    INSERT INTO project_writing_iterations (
                        id,
                        project_id,
                        subchapter_id,
                        cycle,
                        role,
                        content,
                        summary,
                        word_count,
                        feedback,
                        created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                    """,
                    (
                        UUID(str(iteration.id)),
                        project_id,
                        sub_id,
                        iteration.cycle,
                        role_value,
                        iteration.content,
                        summary_value,
                        iteration.word_count,
                        json.dumps(feedback_payload, ensure_ascii=False),
                        iteration.created_at,
                    ),
                )

        next_stage = (
            BookStage.COMPLETE.value if batch.readiness == "ready" else BookStage.WRITING.value
        )
        cur.execute(
            """
            UPDATE projects
            SET stage = %s,
                last_updated = NOW()
            WHERE id = %s
            """,
            (next_stage, project_id),
        )
        conn.commit()


async def _run_writing_stage(project_id: UUID, notes: Optional[str]) -> bool:
    stage_name = BookStage.WRITING.value
    payload = await run_in_threadpool(_build_writing_payload, project_id, notes)
    if not payload:
        with log_context(project_id=str(project_id), stage=stage_name):
            logger.info("Skipping writing stage; guidelines not ready")
        return False

    start_time = perf_counter()
    outcome = "success"
    with log_context(project_id=str(project_id), stage=stage_name):
        logger.info("Submitting writing stage to orchestrator")
        try:
            await _guard_project_budget(project_id)
            async with httpx.AsyncClient(
                base_url=ORCHESTRATOR_URL,
                timeout=ORCHESTRATOR_TIMEOUT_SECONDS,
            ) as client:
                response = await client.post(
                    "/orchestrator/run",
                    json={
                        "project_id": str(project_id),
                        "stages": [
                            {
                                "stage": stage_name,
                                "prompt": json.dumps(payload),
                            }
                        ],
                    },
                )

            response.raise_for_status()
            data = response.json()
            stages = data.get("stages", [])
            if not stages:
                raise httpx.HTTPError("Orchestrator returned no stage output")

            stage_result = next(
                (stage for stage in stages if stage.get("stage") == stage_name),
                stages[0],
            )

            structured_output = stage_result.get("structured_output")
            if not isinstance(structured_output, dict):
                raise httpx.HTTPError("Structured output missing for writing stage")

            batch = WritingBatch.model_validate(structured_output)
            critique = stage_result.get("extras", {}).get("critique")

            await run_in_threadpool(
                _save_writing_result,
                project_id,
                batch,
                critique,
            )
            await run_in_threadpool(
                _record_stage_metrics,
                BookStage.WRITING,
                stage_result,
            )
            await run_in_threadpool(_apply_stage_cost, project_id, stage_result)
            logger.info(
                "Writing stage persisted",
                extra={
                    "model": stage_result.get("model"),
                    "prompt_tokens": int(stage_result.get("prompt_tokens") or 0),
                    "completion_tokens": int(stage_result.get("completion_tokens") or 0),
                    "latency_ms": float(stage_result.get("latency_ms") or 0.0),
                    "readiness": batch.readiness,
                    "cycle_count": batch.cycle_count,
                    "total_word_count": batch.total_word_count,
                },
            )
            return True
        except Exception:
            outcome = "error"
            logger.exception("Writing stage execution failed")
            raise
        finally:
            observe_stage_duration(
                stage=stage_name,
                duration_seconds=perf_counter() - start_time,
                service_name=SERVICE_NAME,
                status=outcome,
            )


def _fetch_research_uploads(project_id: UUID) -> list[ResearchUploadModel]:
    query = """
        SELECT id, prompt_index, filename, storage_path, notes, uploaded_at, word_count, paragraph_count
        FROM project_research_uploads
        WHERE project_id = %s
        ORDER BY uploaded_at ASC
    """
    with POOL.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, (project_id,))
        rows = cur.fetchall()
    uploads: list[ResearchUploadModel] = []
    for row in rows:
        uploads.append(
            ResearchUploadModel(
                id=row["id"],
                prompt_index=row["prompt_index"],
                filename=row["filename"],
                storage_path=row["storage_path"],
                notes=row.get("notes"),
                uploaded_at=row["uploaded_at"],
                word_count=row.get("word_count") or 0,
                paragraph_count=row.get("paragraph_count") or 0,
            )
        )
    return uploads


def _usd_to_cents(value: float) -> int:
    try:
        cents = int(round(float(value) * 100))
    except (TypeError, ValueError):  # pragma: no cover - defensive guard
        return 0
    return max(cents, 0)


def _fetch_budget_state(project_id: UUID) -> tuple[int | None, int]:
    query = """
        SELECT spend_limit_cents, total_cost_cents
        FROM projects
        WHERE id = %s
    """
    with POOL.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, (project_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return row.get("spend_limit_cents"), int(row.get("total_cost_cents") or 0)


def _increment_project_cost(project_id: UUID, delta_usd: float) -> None:
    cents = _usd_to_cents(delta_usd)
    if cents <= 0:
        return
    with POOL.connection() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE projects SET total_cost_cents = total_cost_cents + %s WHERE id = %s",
            (cents, project_id),
        )
        if cur.rowcount == 0:
            conn.rollback()
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        conn.commit()


def _apply_stage_cost(project_id: UUID, stage_result: dict[str, Any]) -> None:
    cost = stage_result.get("cost_usd")
    if cost is None:
        extras = stage_result.get("extras") or {}
        cost = extras.get("cost_usd")
    if cost is None:
        return
    try:
        delta = float(cost)
    except (TypeError, ValueError):  # pragma: no cover - defensive guard
        return
    _increment_project_cost(project_id, delta)


def _set_project_budget(project_id: UUID, spend_limit_usd: float | None) -> None:
    cents = None if spend_limit_usd is None else _usd_to_cents(spend_limit_usd)
    with POOL.connection() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE projects SET spend_limit_cents = %s, last_updated = NOW() WHERE id = %s",
            (cents, project_id),
        )
        if cur.rowcount == 0:
            conn.rollback()
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        conn.commit()


def _delete_project(project_id: UUID) -> bool:
    upload_paths: list[str] = []
    with POOL.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT storage_path FROM project_research_uploads WHERE project_id = %s",
            (project_id,),
        )
        upload_paths = [row["storage_path"] for row in cur.fetchall() if row.get("storage_path")]
        cur.execute("DELETE FROM projects WHERE id = %s", (project_id,))
        deleted = cur.rowcount > 0
        conn.commit()

    if not deleted:
        return False

    for path in upload_paths:
        try:
            os.remove(path)
        except FileNotFoundError:  # pragma: no cover - already gone
            continue
        except OSError as exc:  # pragma: no cover - best effort cleanup
            logger.warning(
                "Failed to remove research upload file",
                extra={"path": path, "error": str(exc)},
            )
    return True


async def _guard_project_budget(project_id: UUID) -> None:
    spend_limit_cents, total_cents = await run_in_threadpool(_fetch_budget_state, project_id)
    if spend_limit_cents is not None and total_cents >= spend_limit_cents:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Project budget exhausted. Increase or disable the spend limit to continue.",
        )


def _record_stage_metrics(stage: BookStage | str, stage_result: dict[str, Any]) -> None:
    stage_value = stage.value if isinstance(stage, BookStage) else str(stage)
    prompt_tokens = int(stage_result.get("prompt_tokens") or 0)
    completion_tokens = int(stage_result.get("completion_tokens") or 0)
    latency_ms = float(stage_result.get("latency_ms") or 0)
    cost_usd = stage_result.get("cost_usd")
    if cost_usd is None:
        cost_usd = stage_result.get("extras", {}).get("cost_usd")
    cost_usd = float(cost_usd) if cost_usd is not None else 0.0

    with POOL.connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO agent_stage_metrics (stage, total_runs, total_prompt_tokens, total_completion_tokens, total_latency_ms, total_cost_usd, updated_at)
            VALUES (%s, 1, %s, %s, %s, %s, NOW())
            ON CONFLICT (stage) DO UPDATE
            SET total_runs = agent_stage_metrics.total_runs + 1,
                total_prompt_tokens = agent_stage_metrics.total_prompt_tokens + EXCLUDED.total_prompt_tokens,
                total_completion_tokens = agent_stage_metrics.total_completion_tokens + EXCLUDED.total_completion_tokens,
                total_latency_ms = agent_stage_metrics.total_latency_ms + EXCLUDED.total_latency_ms,
                total_cost_usd = agent_stage_metrics.total_cost_usd + EXCLUDED.total_cost_usd,
                updated_at = NOW()
            """,
            (stage_value, prompt_tokens, completion_tokens, latency_ms, cost_usd),
        )
        conn.commit()


def _fetch_agent_stage_metrics() -> dict[str, Any]:
    query = """
        SELECT stage, total_runs, total_prompt_tokens, total_completion_tokens, total_latency_ms, total_cost_usd
        FROM agent_stage_metrics
    """
    with POOL.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query)
        rows = cur.fetchall()
    metrics: dict[str, Any] = {}
    for row in rows:
        runs = max(row["total_runs"], 1)
        metrics[row["stage"]] = {
            "average_prompt_tokens": row["total_prompt_tokens"] / runs,
            "average_completion_tokens": row["total_completion_tokens"] / runs,
            "average_latency_ms": row["total_latency_ms"] / runs,
            "average_cost_usd": row["total_cost_usd"] / runs,
            "runs": row["total_runs"],
        }
    return metrics


def _summarise_structure(structure: Any) -> str:
    if not isinstance(structure, dict):
        return ""
    lines: list[str] = []
    for chapter in structure.get("chapters", []):
        title = chapter.get("title", "")
        summary = chapter.get("summary", "")
        order = chapter.get("order", "")
        lines.append(f"Chapter {order}: {title} — {summary}")
        for sub in chapter.get("subchapters", []):
            sub_order = sub.get("order", "")
            sub_title = sub.get("title", "")
            sub_summary = sub.get("summary", "")
            lines.append(f"  - {order}.{sub_order} {sub_title}: {sub_summary}")
    return "\n".join(lines)


def _fetch_structure_detail(project_id: UUID) -> StructureDetail:
    query = """
        SELECT
            p.id,
            p.title,
            p.idea_summary,
            p.research_guidelines,
            p.stage::text AS stage,
            p.last_updated,
            c.id AS category_id,
            c.name AS category_name,
            c.color_hex AS category_color,
            s.structure,
            s.summary,
            s.critiques,
            s.updated_at
        FROM projects p
        LEFT JOIN categories c ON c.id = p.category_id
        JOIN project_structures s ON s.project_id = p.id
        WHERE p.id = %s
    """
    with POOL.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, (project_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Structure not found for project")

    project = _row_to_project_summary(row)
    structure = row["structure"]
    summary = row["summary"]
    critiques = list(row["critiques"] or [])
    iterations = _build_iterations(structure, summary, critiques, row["updated_at"])
    return StructureDetail(project=project, structure=structure, summary=summary, critiques=critiques, iterations=iterations)


def _update_project_stage(project_id: UUID, stage: BookStage) -> Optional[ProjectSummary]:
    with POOL.connection() as conn, conn.cursor() as cur:
        cur.execute("UPDATE projects SET stage = %s, last_updated = NOW() WHERE id = %s", (stage.value, project_id))
        if cur.rowcount == 0:
            conn.rollback()
            return None
        conn.commit()
    return _fetch_project_summary(project_id)


def _row_to_project_summary(row: dict[str, Any]) -> ProjectSummary:
    stage = BookStage(row["stage"])
    category = None
    if row.get("category_id") is not None:
        category = Category(
            id=row["category_id"],
            name=row["category_name"],
            color_hex=row["category_color"],
        )

    total_cents = row.get("total_cost_cents") or 0
    spend_limit_cents = row.get("spend_limit_cents")
    total_usd = round(total_cents / 100.0, 2)
    spend_limit_usd: float | None = None
    budget_remaining_usd: float | None = None
    budget_status = "unlimited"

    if spend_limit_cents is not None:
        spend_limit_usd = round(spend_limit_cents / 100.0, 2)
        remaining_cents = max(spend_limit_cents - total_cents, 0)
        budget_remaining_usd = round(remaining_cents / 100.0, 2)
        if total_cents >= spend_limit_cents:
            budget_status = "exceeded"
            budget_remaining_usd = 0.0
        elif spend_limit_cents > 0 and total_cents >= int(spend_limit_cents * 0.9):
            budget_status = "warning"
        else:
            budget_status = "ok"

    return ProjectSummary(
        id=row["id"],
        title=row.get("title"),
        stage=stage,
        stage_label=_format_stage_label(stage),
        progress=STAGE_PROGRESS.get(stage, 0),
        idea_summary=row.get("idea_summary"),
        research_guidelines=row.get("research_guidelines"),
        last_updated=row["last_updated"],
        category=category,
        guidelines_ready=bool(row.get("guidelines_ready") or False),
        guideline_version=row.get("guideline_version"),
        guideline_updated_at=row.get("guideline_updated_at"),
        writing_ready=bool(row.get("writing_ready") or False),
        writing_updated_at=row.get("writing_updated_at"),
        total_cost_usd=total_usd,
        spend_limit_usd=spend_limit_usd,
        budget_remaining_usd=budget_remaining_usd,
        budget_status=budget_status,
    )


def _format_stage_label(stage: BookStage) -> str:
    return STAGE_FRIENDLY_LABELS.get(stage, stage.value.replace("_", " ").title())


def _build_iterations(
    structure: dict[str, Any], summary: str, critiques: list[str], updated_at: datetime
) -> list[StructureTimelineEntry]:
    base_time = updated_at or datetime.utcnow()
    start_time = base_time - timedelta(minutes=len(critiques) + 1)
    synopsis = structure.get("synopsis") if isinstance(structure, dict) else None
    entries: list[StructureTimelineEntry] = [
        StructureTimelineEntry(
            id="proposal",
            role="proposal",
            title="Initial Outline Created",
            content=synopsis or "Initial outline generated by proposal agent.",
            timestamp=start_time,
        )
    ]
    for index, critique in enumerate(critiques, start=1):
        entries.append(
            StructureTimelineEntry(
                id=f"critique-{index}",
                role="critique",
                title=f"Critique {index}",
                content=critique,
                timestamp=start_time + timedelta(minutes=index),
            )
        )
    entries.append(
        StructureTimelineEntry(
            id="summary",
            role="summary",
            title="Final Summary",
            content=summary,
            timestamp=base_time,
        )
    )
    return entries
