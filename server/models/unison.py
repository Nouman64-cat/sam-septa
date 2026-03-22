"""Models for Unison Marketplace requests."""

from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field
from pydantic import BaseModel


class UnisonScrapeRequest(BaseModel):
    filter_by: Optional[str] = None


class UnisonRequest(SQLModel, table=True):
    __tablename__ = "unison_requests"

    id:                Optional[int] = Field(default=None, primary_key=True)
    buyer_number:      str           = Field(default="", max_length=255)
    buyer_description: str           = Field(default="")
    buyer:             str           = Field(default="", max_length=500)
    end_date:          str           = Field(default="", max_length=255)
    created_at:        datetime      = Field(default_factory=datetime.utcnow)
