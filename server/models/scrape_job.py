"""Models for scrape job tracking."""

from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class ScrapeJob(SQLModel, table=True):
    """One row per scraping run — links bids/quotes back to the job that created them."""
    __tablename__ = "scrape_jobs"

    id:            Optional[int]      = Field(default=None, primary_key=True)
    job_id:        str                = Field(unique=True, max_length=100)
    scraper:       str                = Field(max_length=10)   # 'sam' | 'septa' | 'naics'
    status:        str                = Field(default="running", max_length=10)
    # Filters used for this run (nullable — blank means "no filter")
    date_from:     Optional[str]      = Field(default=None, max_length=20)
    date_to:       Optional[str]      = Field(default=None, max_length=20)
    started_at:    datetime           = Field(default_factory=datetime.utcnow)
    finished_at:   Optional[datetime] = Field(default=None)
    record_count:  int                = Field(default=0)
    error_message: Optional[str]      = Field(default=None)
