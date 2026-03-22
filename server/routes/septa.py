"""SEPTA scraper routes — scrape + export."""

import threading
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, StreamingResponse
from sqlmodel import Session, select

from database import engine
from models import ScrapeJob, SeptaQuote, SeptaScrapeRequest

from septa.septa_scraper import (
    Config as SeptaConfig,
    BrowserManager as SeptaBrowser,
    SeptaPortal,
    DataExporter,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Scrape
# ---------------------------------------------------------------------------

@router.post("/scrape_septa")
async def scrape_septa(body: SeptaScrapeRequest):
    """Start a SEPTA scrape. Returns job_id immediately; poll /status/{job_id}."""
    from main import _jobs, _new_job_id, _finish_job

    job_id     = _new_job_id("septa")
    stop_event = threading.Event()

    _jobs[job_id] = {
        "status":       "running",
        "record_count": 0,
        "error":        None,
        "stop_event":   stop_event,
    }

    with Session(engine) as s:
        s.add(ScrapeJob(
            job_id    = job_id,
            scraper   = "septa",
            status    = "running",
            date_from = body.date_filter,
        ))
        s.commit()

    def _run():
        try:
            config          = SeptaConfig()
            browser_manager = SeptaBrowser(config)

            if not browser_manager.setup_driver(headless=True):
                _finish_job(job_id, "error", 0, "Failed to setup browser for SEPTA scraper.")
                return

            portal = SeptaPortal(browser_manager, config)

            if not portal.login():
                browser_manager.close_driver()
                _finish_job(job_id, "error", 0, "SEPTA login failed.")
                return

            if not portal.navigate_to_open_quotes():
                browser_manager.close_driver()
                _finish_job(job_id, "error", 0, "SEPTA navigation to Open Quotes failed.")
                return

            def _on_quote(q: dict):
                """Called per quote — inserts to DB and updates live counter."""
                with Session(engine) as s:
                    s.add(SeptaQuote(
                        job_id             = job_id,
                        requisition_number = q.get("requisition_number", ""),
                        summary            = q.get("summary", ""),
                        open_date          = q.get("open_date", ""),
                        close_date         = q.get("close_date", ""),
                    ))
                    s.commit()
                _jobs[job_id]["record_count"] += 1

            portal.apply_date_filter(body.date_filter)
            portal.scrape_all_pages(stop_event=stop_event, on_quote=_on_quote)
            browser_manager.close_driver()

            final = "stopped" if stop_event.is_set() else "done"
            _finish_job(job_id, final, _jobs[job_id]["record_count"])

        except Exception as exc:
            _finish_job(job_id, "error", _jobs[job_id]["record_count"], str(exc))

    threading.Thread(target=_run, daemon=True).start()
    return JSONResponse({"success": True, "job_id": job_id})


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

@router.get("/export/septa")
async def export_septa(job_id: Optional[str] = Query(default=None)):
    """
    Export SEPTA quotes to a styled Excel file.
    - ?job_id=septa_... → only that run's quotes
    - no param           → all quotes in DB
    """
    from main import _styled_workbook

    with Session(engine) as s:
        query = select(SeptaQuote)
        if job_id:
            query = query.where(SeptaQuote.job_id == job_id)
        quotes = s.exec(query.order_by(SeptaQuote.scraped_at.desc())).all()

    headers = [
        "Requisition Number", "Summary", "Open Date", "Close Date",
    ]
    rows = [
        [
            q.requisition_number, q.summary, q.open_date, q.close_date,
        ]
        for q in quotes
    ]

    _now = datetime.now()
    _hr  = _now.strftime("%I").lstrip("0") or "12"
    ts   = _now.strftime(f"%Y-%m-%d, {_hr}:%M %p")
    filename = f"septa_{ts}.xlsx"
    stream   = _styled_workbook("SEPTA Quotes", headers, rows)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
