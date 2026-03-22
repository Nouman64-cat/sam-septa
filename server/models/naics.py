"""Models for NAICS codes."""

from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class NaicsCode(SQLModel, table=True):
    __tablename__ = "naics_codes"

    id:         Optional[int] = Field(default=None, primary_key=True)
    code:       str           = Field(unique=True, max_length=10)
    title:      str           = Field(default="", max_length=500)
    scraped_at: datetime      = Field(default_factory=datetime.utcnow)
