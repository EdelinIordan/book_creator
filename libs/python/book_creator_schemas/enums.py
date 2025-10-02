"""Enum definitions shared across workflows."""

from __future__ import annotations

from enum import Enum


class BookStage(str, Enum):
    IDEA = "IDEA"
    STRUCTURE = "STRUCTURE"
    TITLE = "TITLE"
    RESEARCH = "RESEARCH"
    FACT_MAPPING = "FACT_MAPPING"
    EMOTIONAL = "EMOTIONAL"
    GUIDELINES = "GUIDELINES"
    WRITING = "WRITING"
    COMPLETE = "COMPLETE"


class AgentRole(str, Enum):
    IDEA_GENERATOR = "idea_generator"

    STRUCTURE_ARCHITECT = "structure_architect"
    STRUCTURE_CRITIC_I = "structure_critic_i"
    STRUCTURE_EDITOR_I = "structure_editor_i"
    STRUCTURE_CRITIC_II = "structure_critic_ii"
    STRUCTURE_EDITOR_II = "structure_editor_ii"
    STRUCTURE_CRITIC_III = "structure_critic_iii"
    STRUCTURE_EDITOR_III = "structure_editor_iii"

    TITLER = "titler"

    PROMPT_ARCHITECT = "prompt_architect"
    PROMPT_CRITIC = "prompt_critic"
    PROMPT_FINALIZER = "prompt_finalizer"

    RESEARCH_INGESTOR = "research_ingestor"
    FACT_SELECTOR = "fact_selector"
    FACT_CRITIC = "fact_critic"
    FACT_IMPLEMENTER = "fact_implementer"

    EMOTION_AUTHOR = "emotion_author"
    EMOTION_CRITIC = "emotion_critic"
    EMOTION_IMPLEMENTER = "emotion_implementer"

    CREATIVE_DIRECTOR_ASSISTANT = "creative_director_assistant"
    CREATIVE_DIRECTOR_CRITIC = "creative_director_critic"
    CREATIVE_DIRECTOR_FINAL = "creative_director_final"

    WRITER_INITIAL = "writer_initial"
    WRITING_CRITIC_I = "writing_critic_i"
    WRITING_IMPLEMENTATION_I = "writing_implementation_i"
    WRITING_CRITIC_II = "writing_critic_ii"
    WRITING_IMPLEMENTATION_II = "writing_implementation_ii"
    WRITING_CRITIC_III = "writing_critic_iii"
    WRITING_IMPLEMENTATION_III = "writing_implementation_iii"

    # Backwards-compatible aliases
    STRUCTURE_AUTHOR = STRUCTURE_ARCHITECT
    STRUCTURE_CRITIC = STRUCTURE_CRITIC_I
    RESEARCH_PLANNER = PROMPT_ARCHITECT
    RESEARCH_CRITIC = PROMPT_CRITIC
    FACT_ANALYST = FACT_SELECTOR
    CREATIVE_DIRECTOR = CREATIVE_DIRECTOR_ASSISTANT
    CREATIVE_CRITIC = CREATIVE_DIRECTOR_CRITIC
    WRITER = WRITER_INITIAL
    WRITING_CRITIC = WRITING_CRITIC_I
    IMPLEMENTATION = WRITING_IMPLEMENTATION_I


class CritiqueSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ResearchSourceType(str, Enum):
    ACADEMIC_JOURNAL = "academic_journal"
    BOOK = "book"
    GOVERNMENT_REPORT = "government_report"
    NEWS_ARTICLE = "news_article"
    EXPERT_INTERVIEW = "expert_interview"
    DATASET = "dataset"
    OTHER = "other"
