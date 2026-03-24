"""NAICS code scraper + search/list routes."""

import threading

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from sqlalchemy import func
from sqlmodel import Session, select

from db import engine
from models import ScrapeJob, NaicsCode
from scrappers.naics.naics_scraper import NaicsCodeScraper

router = APIRouter()


# ---------------------------------------------------------------------------
# Scrape
# ---------------------------------------------------------------------------

@router.post("/scrape/naics")
async def scrape_naics():
    """Start a NAICS code scrape. Returns job_id immediately; poll /status/{job_id}."""
    from main import _jobs, _new_job_id, _finish_job

    job_id     = _new_job_id("naics")
    stop_event = threading.Event()

    _jobs[job_id] = {
        "status":       "running",
        "record_count": 0,
        "error":        None,
        "stop_event":   stop_event,
    }

    with Session(engine) as s:
        s.add(ScrapeJob(
            job_id  = job_id,
            scraper = "naics",
            status  = "running",
        ))
        s.commit()

    def _on_code(item: dict):
        try:
            with Session(engine) as s:
                s.add(NaicsCode(code=item["code"], title=item["title"]))
                s.commit()
            _jobs[job_id]["record_count"] += 1
        except Exception:
            pass  # skip duplicates (unique constraint on code)

    def _run():
        try:
            scraper = NaicsCodeScraper()
            scraper._stop_event      = stop_event
            scraper._on_code_scraped = _on_code
            scraper.run()
            final = "stopped" if stop_event.is_set() else "done"
            _finish_job(job_id, final, _jobs[job_id]["record_count"])
        except Exception as exc:
            _finish_job(job_id, "error", _jobs[job_id]["record_count"], str(exc))

    threading.Thread(target=_run, daemon=True).start()
    return JSONResponse({"success": True, "job_id": job_id})


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

@router.get("/naics/search")
async def search_naics(
    q:     str = Query(default=""),
    page:  int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
):
    offset = (page - 1) * limit
    with Session(engine) as s:
        base = select(NaicsCode)
        if q:
            term = f"%{q.lower()}%"
            base = base.where(
                func.lower(NaicsCode.code).like(term) |
                func.lower(NaicsCode.title).like(term)
            )
        total   = s.exec(select(func.count()).select_from(base.subquery())).one()
        results = s.exec(base.order_by(NaicsCode.code).offset(offset).limit(limit)).all()

    return JSONResponse({
        "total":   total,
        "page":    page,
        "limit":   limit,
        "results": [{"code": r.code, "title": r.title} for r in results],
    })


# ---------------------------------------------------------------------------
# List all
# ---------------------------------------------------------------------------

@router.get("/naics")
async def list_naics(
    page:  int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
):
    offset = (page - 1) * limit
    with Session(engine) as s:
        total   = s.exec(select(func.count(NaicsCode.id))).one()
        results = s.exec(
            select(NaicsCode).order_by(NaicsCode.code).offset(offset).limit(limit)
        ).all()

    return JSONResponse({
        "total":   total,
        "page":    page,
        "limit":   limit,
        "results": [{"code": r.code, "title": r.title} for r in results],
    })
