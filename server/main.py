import io
import os
import threading
import importlib.util
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import func
from sqlmodel import Session, select

from database import create_db_and_tables, engine
from models import (
    ScrapeJob,
    SamBid, SeptaQuote, NaicsCode,
    UnisonRequest, DibbsBid,
    SamScrapeRequest, SeptaScrapeRequest, UnisonScrapeRequest,
)
from sam_scraper import SAMGovScraper
from naics_scraper import NaicsCodeScraper

# Import Septa Scraper
try:
    from septa_scrapper import (
        Config as SeptaConfig,
        BrowserManager as SeptaBrowser,
        SeptaPortal,
        DataExporter,
    )
except ImportError:
    print("Error importing Septa scraper modules. Make sure septa_scrapper.py works.")

# Import Unison Scraper (handling hyphen in filename)
try:
    spec = importlib.util.spec_from_file_location("unison_module", "unison-scraper.py")
    unison_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(unison_module)
    UnisonMarketplaceScraper = unison_module.UnisonMarketplaceScraper
except Exception as e:
    print(f"Error importing Unison scraper: {e}")

# Import Dibbs Scraper (handling hyphen in filename)
try:
    spec_dibbs = importlib.util.spec_from_file_location("dibbs_module", "dibbs-scrapper.py")
    dibbs_module = importlib.util.module_from_spec(spec_dibbs)
    spec_dibbs.loader.exec_module(dibbs_module)
    DibbsScraper = dibbs_module.DibbsScraper
except Exception as e:
    print(f"Error importing Dibbs scraper: {e}")


# ── In-memory job registry ────────────────────────────────────────────────────
# Mirrors the DB ScrapeJob row for fast status polling without DB hits.

_jobs: dict[str, dict] = {}


def _new_job_id(prefix: str) -> str:
    return f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def _finish_job(job_id: str, status: str, record_count: int, error: str | None = None):
    """Update both the in-memory registry and the DB ScrapeJob row."""
    now = datetime.utcnow()
    _jobs[job_id]["status"]       = status
    _jobs[job_id]["record_count"] = record_count
    _jobs[job_id]["error"]        = error
    with Session(engine) as s:
        job = s.exec(select(ScrapeJob).where(ScrapeJob.job_id == job_id)).first()
        if job:
            job.status        = status
            job.finished_at   = now
            job.record_count  = record_count
            job.error_message = error
            s.add(job)
            s.commit()


# ── Excel helpers ─────────────────────────────────────────────────────────────

_HEADER_FILL  = PatternFill("solid", fgColor="1E3A5F")
_HEADER_FONT  = Font(bold=True, color="FFFFFF", size=11)
_HEADER_ALIGN = Alignment(horizontal="center", vertical="center", wrap_text=True)


def _styled_workbook(sheet_name: str, headers: list[str], rows: list[list]) -> io.BytesIO:
    """Build a styled openpyxl workbook and return it as an in-memory BytesIO stream."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet_name

    # Header row
    ws.append(headers)
    for cell in ws[1]:
        cell.fill      = _HEADER_FILL
        cell.font      = _HEADER_FONT
        cell.alignment = _HEADER_ALIGN
    ws.row_dimensions[1].height = 30

    # Data rows
    for row in rows:
        ws.append(row)

    # Auto-fit column widths (capped at 60)
    for col in ws.columns:
        max_len = max((len(str(c.value or "")) for c in col), default=10)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 60)

    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return stream


# ── App setup ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Misc ──────────────────────────────────────────────────────────────────────

@app.get("/")
async def home():
    return {"message": "SAM-SEPTA Scraper API"}


# ── Job status / stop ─────────────────────────────────────────────────────────

@app.get("/status/{job_id}")
async def get_job_status(job_id: str):
    if job_id not in _jobs:
        return JSONResponse({"error": "Unknown job ID"}, status_code=404)
    job = _jobs[job_id]
    return JSONResponse({
        "status":       job["status"],        # running | done | stopped | error
        "record_count": job["record_count"],  # live count updated per bid
        "error":        job["error"],
    })


@app.post("/stop/{job_id}")
async def stop_job(job_id: str):
    if job_id not in _jobs:
        return JSONResponse({"error": "Unknown job ID"}, status_code=404)
    job = _jobs[job_id]
    if job["status"] != "running":
        return JSONResponse({"success": False, "message": "Job is not currently running."})
    job["stop_event"].set()
    return JSONResponse({
        "success": True,
        "message": "Stop signal sent - finishing current bid then saving.",
    })


# ── SAM.gov scraper ───────────────────────────────────────────────────────────

@app.post("/scrape_sam")
async def scrape_sam(body: SamScrapeRequest):
    """Start a SAM.gov scrape. Returns job_id immediately; poll /status/{job_id}."""
    job_id     = _new_job_id("sam")
    stop_event = threading.Event()

    _jobs[job_id] = {
        "status":       "running",
        "record_count": 0,
        "error":        None,
        "stop_event":   stop_event,
    }

    # Persist job row to DB immediately
    with Session(engine) as s:
        s.add(ScrapeJob(
            job_id    = job_id,
            scraper   = "sam",
            status    = "running",
            date_from = body.date_filter,
            date_to   = body.date_to,
        ))
        s.commit()

    def _on_bid(bid: dict):
        """Called per extracted bid — inserts to DB and updates live counter."""
        with Session(engine) as s:
            s.add(SamBid(
                job_id           = job_id,
                notice_id        = bid.get("Notice ID", ""),
                title            = bid.get("Notice Title", ""),
                department       = bid.get("Department/Ind. Agency", ""),
                subtier          = bid.get("Subtier", ""),
                office           = bid.get("Office", ""),
                description      = bid.get("Description", ""),
                updated_date     = bid.get("Updated Date", ""),
                bid_repeat_count = int(bid.get("bid_repeat_count", 0)),
                naics_code       = bid.get("NAICS Code", ""),
                naics_title      = bid.get("NAICS Title", ""),
                date_offers_due  = bid.get("Date Offers Due", ""),
                published_date   = bid.get("Published Date", ""),
            ))
            s.commit()
        _jobs[job_id]["record_count"] += 1

    def _run():
        try:
            scraper = SAMGovScraper(
                headless    = False,
                date_filter = body.date_filter,
                date_to     = body.date_to,
                naics_codes = body.naics_codes,
            )
            scraper._stop_event       = stop_event
            scraper.skip_csv          = True      # no CSV files
            scraper._on_bid_extracted = _on_bid   # live DB insert per bid

            scraper.run(max_records=1000)

            final = "stopped" if stop_event.is_set() else "done"
            _finish_job(job_id, final, _jobs[job_id]["record_count"])

        except Exception as exc:
            _finish_job(job_id, "error", _jobs[job_id]["record_count"], str(exc))

    threading.Thread(target=_run, daemon=True).start()
    return JSONResponse({"success": True, "job_id": job_id})


# ── SEPTA scraper ─────────────────────────────────────────────────────────────

@app.post("/scrape_septa")
async def scrape_septa(body: SeptaScrapeRequest):
    """Start a SEPTA scrape. Returns job_id immediately; poll /status/{job_id}."""
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
            config         = SeptaConfig()
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


# ── Export endpoints ──────────────────────────────────────────────────────────

@app.get("/export/sam")
async def export_sam(job_id: Optional[str] = Query(default=None)):
    """
    Export SAM bids to a styled Excel file.
    - ?job_id=sam_... → only that run's bids
    - no param         → all bids in DB
    """
    with Session(engine) as s:
        query = select(SamBid)
        if job_id:
            query = query.where(SamBid.job_id == job_id)
        bids = s.exec(query.order_by(SamBid.scraped_at.desc())).all()

    headers = [
        "Notice Title", "Notice ID", "Department/Ind. Agency",
        "Description", "Subtier", "Updated Date",
        "Bid Repeat Count", "NAICS Code", "NAICS Title",
        "Date Offers Due", "Published Date", "Office",
    ]
    rows = [
        [
            b.title, b.notice_id, b.department, b.description,
            b.subtier, b.updated_date, b.bid_repeat_count,
            b.naics_code, b.naics_title,
            b.date_offers_due, b.published_date, b.office,
        ]
        for b in bids
    ]

    _now = datetime.now()
    _hr  = _now.strftime("%I").lstrip("0") or "12"
    ts   = _now.strftime(f"%Y-%m-%d, {_hr}:%M %p")
    filename = f"sam_{ts}.xlsx"
    stream   = _styled_workbook("SAM Bids", headers, rows)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/export/septa")
async def export_septa(job_id: Optional[str] = Query(default=None)):
    """
    Export SEPTA quotes to a styled Excel file.
    - ?job_id=septa_... → only that run's quotes
    - no param           → all quotes in DB
    """
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


# ── NAICS scraper ─────────────────────────────────────────────────────────────

@app.post("/scrape/naics")
async def scrape_naics():
    """Start a NAICS code scrape. Returns job_id immediately; poll /status/{job_id}."""
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


@app.get("/naics/search")
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


@app.get("/naics")
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


# ── Scrape jobs list ──────────────────────────────────────────────────────────

@app.get("/jobs")
async def list_jobs(scraper: Optional[str] = Query(default=None)):
    """List all scrape jobs, newest first. Filter by scraper='sam' or 'septa'."""
    with Session(engine) as s:
        query = select(ScrapeJob).order_by(ScrapeJob.started_at.desc())
        if scraper:
            query = query.where(ScrapeJob.scraper == scraper)
        jobs = s.exec(query).all()

    return JSONResponse([
        {
            "job_id":       j.job_id,
            "scraper":      j.scraper,
            "status":       j.status,
            "date_from":    j.date_from,
            "date_to":      j.date_to,
            "started_at":   j.started_at.isoformat() if j.started_at  else None,
            "finished_at":  j.finished_at.isoformat() if j.finished_at else None,
            "record_count": j.record_count,
            "error_message": j.error_message,
        }
        for j in jobs
    ])


# ── Unison scraper (unchanged) ────────────────────────────────────────────────

@app.post("/scrape_unison")
async def scrape_unison(body: UnisonScrapeRequest):
    try:
        scraper = UnisonMarketplaceScraper()
        scraper.run_scraper(filter_by=body.filter_by)

        if os.path.exists(scraper.csv_file):
            import csv
            with open(scraper.csv_file, "r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                with Session(engine) as s:
                    for row in reader:
                        s.add(UnisonRequest(
                            buyer_number      = row.get("Buyer#", ""),
                            buyer_description = row.get("Buyer Description", ""),
                            buyer             = row.get("Buyer", ""),
                            end_date          = row.get("End Date", ""),
                        ))
                    s.commit()
            return JSONResponse({"success": True, "filename": scraper.csv_file})
        else:
            return JSONResponse({
                "success": False,
                "error": "Unison scraper finished but CSV file not found.",
            })
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})


# ── DIBBS scraper (unchanged) ─────────────────────────────────────────────────

@app.post("/scrape_dibbs")
async def scrape_dibbs():
    try:
        scraper  = DibbsScraper(headless=False)
        csv_file = scraper.run()

        if csv_file and os.path.exists(csv_file):
            with Session(engine) as s:
                for item in scraper.data:
                    s.add(DibbsBid(
                        nsn_part_number  = item.get("NSN/Part Number", ""),
                        nomenclature     = item.get("Nomenclature", ""),
                        solicitation     = item.get("Solicitation", ""),
                        rfq_quote_status = item.get("RFQ/Quote Status", ""),
                        purchase_request = item.get("Purchase Request", ""),
                        issued           = item.get("Issued", ""),
                        return_by        = item.get("Return By", ""),
                    ))
                s.commit()
            return JSONResponse({"success": True, "filename": csv_file})
        else:
            return JSONResponse({
                "success": False,
                "error": "DIBBS scraper finished but CSV file not found.",
            })
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
