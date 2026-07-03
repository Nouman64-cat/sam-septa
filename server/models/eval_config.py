"""EvalConfig — DB-backed kill words (and reference service lists) for the bid evaluator."""

from typing import Optional
from sqlmodel import SQLModel, Field


class EvalConfig(SQLModel, table=True):
    """
    Stores runtime-editable evaluator config in the DB so it can be managed
    without editing config files.

    category: "kill_word"        — instant-reject keywords (used by evaluator)
            | "excluded_service" — Rule B reference list (shown in UI)
            | "allowed_service"  — Rule C reference list (shown in UI)
    value:    the actual string (stored lowercase for consistent matching)

    Note: Rule B/C matching in the evaluator is NAICS- and keyword-driven per
    SAM_Bid_Evaluation_Spec_v1; the service rows here are the editable
    reference catalogue surfaced in the Evaluator Settings panel.
    """
    __tablename__ = "eval_config"

    id:       Optional[int] = Field(default=None, primary_key=True)
    category: str           = Field(max_length=30, index=True)   # kill_word | territory
    value:    str           = Field(max_length=200, index=True)   # e.g. "idiq" or "guam"
