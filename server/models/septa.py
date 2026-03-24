"""Models for SEPTA procurement quotes and scrape requests."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Text
from sqlmodel import SQLModel, Field
from pydantic import BaseModel


class SeptaScrapeRequest(BaseModel):
    date_filter: Optional[str] = None


class SeptaQuote(SQLModel, table=True):
    """
    Exact 4-column match to the dict returned by SeptaPortal.scrape_quotes().
    Linked to the scrape run that produced it via job_id.
    """
    __tablename__ = "septa_quotes"

    id:                  Optional[int] = Field(default=None, primary_key=True)
    job_id:              str           = Field(max_length=100, foreign_key="scrape_jobs.job_id")
    # ── Scraped fields ────────────────────────────────────────────────────────
    requisition_number:  str           = Field(default="", max_length=255)
    summary:             Optional[str] = Field(default="", sa_column=Column(Text))
    open_date:           str           = Field(default="", max_length=50)
    close_date:          str           = Field(default="", max_length=50)
    # ── Metadata ──────────────────────────────────────────────────────────────
    scraped_at:          datetime      = Field(default_factory=datetime.utcnow)
