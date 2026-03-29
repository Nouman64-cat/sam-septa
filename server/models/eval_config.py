"""EvalConfig — DB-backed kill words and restricted territories for the bid evaluator."""

from typing import Optional
from sqlmodel import SQLModel, Field


class EvalConfig(SQLModel, table=True):
    """
    Stores the evaluator's kill_words and restricted_territories in the DB
    so they can be managed at runtime without editing any config files.

    category: "kill_word" | "territory"
    value:    the actual string (stored lowercase for consistent matching)
    """
    __tablename__ = "eval_config"

    id:       Optional[int] = Field(default=None, primary_key=True)
    category: str           = Field(max_length=30, index=True)   # kill_word | territory
    value:    str           = Field(max_length=200, index=True)   # e.g. "idiq" or "guam"
