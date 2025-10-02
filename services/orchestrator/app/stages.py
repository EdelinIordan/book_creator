"""Default prompts and stage helpers for the Prefect flow."""

from __future__ import annotations

from book_creator_schemas import BookStage

DEFAULT_STAGE_PROMPTS = {
    BookStage.IDEA: "Summarise the core idea in one paragraph.",
    BookStage.STRUCTURE: "Propose chapter outline based on the supplied context.",
    BookStage.TITLE: "Generate five compelling title options.",
    BookStage.RESEARCH: "List three research directions relevant to the outline.",
    BookStage.FACT_MAPPING: "Map key facts to the existing subchapters.",
    BookStage.EMOTIONAL: "Suggest emotional narratives to support the facts.",
    BookStage.GUIDELINES: "Draft creative guidelines for the next writing pass.",
    BookStage.WRITING: "Execute the seven-pass writing loop to produce publication-ready drafts.",
    BookStage.COMPLETE: "Provide closing remarks confirming completion.",
}


def build_default_stage_sequence() -> list[tuple[BookStage, str]]:
    return [(stage, prompt) for stage, prompt in DEFAULT_STAGE_PROMPTS.items()]
