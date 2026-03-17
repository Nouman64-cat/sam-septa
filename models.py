from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field
from pydantic import BaseModel


# ── Request body schemas (used by FastAPI endpoints / Swagger UI) ──────────────

class SamScrapeRequest(BaseModel):
    date_filter: Optional[str] = None


class SeptaScrapeRequest(BaseModel):
    date_filter: Optional[str] = None


class UnisonScrapeRequest(BaseModel):
    filter_by: Optional[str] = None


# ── SQLModel database table models ─────────────────────────────────────────────

class SamBid(SQLModel, table=True):
    __tablename__ = "sam_bids"

    id: Optional[int] = Field(default=None, primary_key=True)
    notice_id: str = Field(default="", max_length=255)
    title: str = Field(default="")
    date_offers_due: str = Field(default="", max_length=255)
    published_date: str = Field(default="", max_length=255)
    updated_date: str = Field(default="", max_length=255)
    inactive_dates: str = Field(default="", max_length=255)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SeptaQuote(SQLModel, table=True):
    __tablename__ = "septa_quotes"

    id: Optional[int] = Field(default=None, primary_key=True)
    requisition_number: str = Field(default="", max_length=255)
    summary: str = Field(default="")
    open_date: str = Field(default="", max_length=255)
    close_date: str = Field(default="", max_length=255)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class UnisonRequest(SQLModel, table=True):
    __tablename__ = "unison_requests"

    id: Optional[int] = Field(default=None, primary_key=True)
    buyer_number: str = Field(default="", max_length=255)
    buyer_description: str = Field(default="")
    buyer: str = Field(default="", max_length=500)
    end_date: str = Field(default="", max_length=255)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DibbsBid(SQLModel, table=True):
    __tablename__ = "dibbs_bids"

    id: Optional[int] = Field(default=None, primary_key=True)
    nsn_part_number: str = Field(default="", max_length=255)
    nomenclature: str = Field(default="")
    solicitation: str = Field(default="", max_length=255)
    rfq_quote_status: str = Field(default="", max_length=255)
    purchase_request: str = Field(default="", max_length=255)
    issued: str = Field(default="", max_length=255)
    return_by: str = Field(default="", max_length=255)
    created_at: datetime = Field(default_factory=datetime.utcnow)
