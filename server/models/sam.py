"""Models for SAM.gov bids and scrape requests."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Text
from sqlmodel import SQLModel, Field
from pydantic import BaseModel


class SamScrapeRequest(BaseModel):
    date_filter: Optional[str] = None         # from-date  YYYY-MM-DD  (start of range)
    date_to:     Optional[str] = None         # to-date    YYYY-MM-DD  (end   of range)
    naics_codes: Optional[list[str]] = None   # list of 6-digit NAICS codes to filter


class SamBid(SQLModel, table=True):
    """
    Exact 9-column match to the dict returned by SAMGovScraper.extract_details().
    Linked to the scrape run that produced it via job_id.
    """
    __tablename__ = "sam_bids"

    id:              Optional[int] = Field(default=None, primary_key=True)
    job_id:          str           = Field(max_length=100, foreign_key="scrape_jobs.job_id")
    # ── Scraped fields (keys match scraper dict exactly) ──────────────────────
    notice_id:       str           = Field(default="", max_length=255)
    title:           str           = Field(default="", max_length=500)  # Notice Title
    department:      str           = Field(default="", max_length=500)  # Department/Ind. Agency
    subtier:         str           = Field(default="", max_length=500)
    office:          str           = Field(default="", max_length=500)
    description:      Optional[str] = Field(default="", sa_column=Column(Text))
    updated_date:     str           = Field(default="", max_length=50)
    bid_repeat_count: int           = Field(default=0)
    naics_code:       str           = Field(default="", max_length=20)
    naics_title:      str           = Field(default="", max_length=500)
    date_offers_due:  str           = Field(default="", max_length=50)
    published_date:   str           = Field(default="", max_length=50)
    # ── Metadata ──────────────────────────────────────────────────────────────
    scraped_at:       datetime      = Field(default_factory=datetime.utcnow)
