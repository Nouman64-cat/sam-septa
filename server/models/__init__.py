"""
Models package — re-exports all models for backward-compatible imports.

Usage unchanged:
    from models import SamBid, ScrapeJob, ...
    import models  # registers all SQLModel tables
"""

from models.scrape_job import ScrapeJob
from models.sam import SamBid, SamScrapeRequest, SamEvaluateRequest, SamEvaluateResponse
from models.septa import SeptaQuote, SeptaScrapeRequest
from models.naics import NaicsCode
from models.unison import UnisonRequest, UnisonScrapeRequest
from models.dibbs import DibbsBid

__all__ = [
    "ScrapeJob",
    "SamBid", "SamScrapeRequest", "SamEvaluateRequest", "SamEvaluateResponse",
    "SeptaQuote", "SeptaScrapeRequest",
    "NaicsCode",
    "UnisonRequest", "UnisonScrapeRequest",
    "DibbsBid",
]
