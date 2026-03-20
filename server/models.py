from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Text
from sqlmodel import SQLModel, Field
from pydantic import BaseModel


# ── Request body schemas ───────────────────────────────────────────────────────

class SamScrapeRequest(BaseModel):
    date_filter: Optional[str] = None         # from-date  YYYY-MM-DD  (start of range)
    date_to:     Optional[str] = None         # to-date    YYYY-MM-DD  (end   of range)
    naics_codes: Optional[list[str]] = None   # list of 6-digit NAICS codes to filter


class SeptaScrapeRequest(BaseModel):
    date_filter: Optional[str] = None


class UnisonScrapeRequest(BaseModel):
    filter_by: Optional[str] = None


# ── Scrape job / run tracking ──────────────────────────────────────────────────

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


# ── SAM.gov bids ───────────────────────────────────────────────────────────────

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


# ── SEPTA procurement quotes ───────────────────────────────────────────────────

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


# ── NAICS codes ────────────────────────────────────────────────────────────────

class NaicsCode(SQLModel, table=True):
    __tablename__ = "naics_codes"

    id:         Optional[int] = Field(default=None, primary_key=True)
    code:       str           = Field(unique=True, max_length=10)
    title:      str           = Field(default="", max_length=500)
    scraped_at: datetime      = Field(default_factory=datetime.utcnow)


# ── Legacy tables (Unison / DIBBS — unchanged) ─────────────────────────────────

class UnisonRequest(SQLModel, table=True):
    __tablename__ = "unison_requests"

    id:                Optional[int] = Field(default=None, primary_key=True)
    buyer_number:      str           = Field(default="", max_length=255)
    buyer_description: str           = Field(default="")
    buyer:             str           = Field(default="", max_length=500)
    end_date:          str           = Field(default="", max_length=255)
    created_at:        datetime      = Field(default_factory=datetime.utcnow)


class DibbsBid(SQLModel, table=True):
    __tablename__ = "dibbs_bids"

    id:                Optional[int] = Field(default=None, primary_key=True)
    nsn_part_number:   str           = Field(default="", max_length=255)
    nomenclature:      str           = Field(default="")
    solicitation:      str           = Field(default="", max_length=255)
    rfq_quote_status:  str           = Field(default="", max_length=255)
    purchase_request:  str           = Field(default="", max_length=255)
    issued:            str           = Field(default="", max_length=255)
    return_by:         str           = Field(default="", max_length=255)
    created_at:        datetime      = Field(default_factory=datetime.utcnow)
