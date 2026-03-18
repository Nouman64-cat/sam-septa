import os
import threading
import importlib.util
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from database import create_db_and_tables, engine
from models import (
    SamBid, SeptaQuote, UnisonRequest, DibbsBid,
    SamScrapeRequest, SeptaScrapeRequest, UnisonScrapeRequest,
)
from sam_scraper import SAMGovScraper

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
    spec_dibbs = importlib.util.spec_from_file_location(
        "dibbs_module", "dibbs-scrapper.py"
    )
    dibbs_module = importlib.util.module_from_spec(spec_dibbs)
    spec_dibbs.loader.exec_module(dibbs_module)
    DibbsScraper = dibbs_module.DibbsScraper
except Exception as e:
    print(f"Error importing Dibbs scraper: {e}")


# ── Job registry ──────────────────────────────────────────────────────────────
# Keyed by job_id.  Each value holds live runtime state for one scrape run.
# status values: "running" | "done" | "stopped" | "error"

_jobs: dict[str, dict] = {}


def _new_job_id(prefix: str) -> str:
    return f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


# ── App lifespan ──────────────────────────────────────────────────────────────

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


# ── Misc endpoints ────────────────────────────────────────────────────────────

@app.get("/")
async def home():
    return {"message": "SAM-SEPTA Scraper API"}


@app.get("/download/{filename:path}")
async def download_file(filename: str):
    try:
        return FileResponse(
            filename,
            filename=os.path.basename(filename),
            media_type="application/octet-stream",
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=404)


# ── Job status / stop ─────────────────────────────────────────────────────────

@app.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """Poll the live status of a running or finished scrape job."""
    if job_id not in _jobs:
        return JSONResponse({"error": "Unknown job ID"}, status_code=404)
    job = _jobs[job_id]
    return JSONResponse({
        "status":   job["status"],    # running | done | stopped | error
        "filename": job["filename"],  # absolute path once finished
        "error":    job["error"],
    })


@app.post("/stop/{job_id}")
async def stop_job(job_id: str):
    """Signal a running scrape job to stop gracefully and save partial data."""
    if job_id not in _jobs:
        return JSONResponse({"error": "Unknown job ID"}, status_code=404)
    job = _jobs[job_id]
    if job["status"] != "running":
        return JSONResponse({"success": False, "message": "Job is not currently running."})
    job["stop_event"].set()
    return JSONResponse({
        "success": True,
        "message": "Stop signal sent - finishing current page then saving.",
    })


# ── SAM.gov scraper ───────────────────────────────────────────────────────────

@app.post("/scrape_sam")
async def scrape_sam(body: SamScrapeRequest):
    """
    Start a SAM.gov scrape in a background thread.
    Returns immediately with a job_id; poll /status/{job_id} for progress.
    """
    job_id = _new_job_id("sam")
    stop_event = threading.Event()
    _jobs[job_id] = {
        "status":     "running",
        "filename":   None,
        "error":      None,
        "stop_event": stop_event,
    }

    def _run():
        try:
            scraper = SAMGovScraper(
                headless=False,
                date_filter=body.date_filter,
                date_to=body.date_to,
            )
            scraper._stop_event = stop_event
            csv_file = scraper.run(max_records=1000)

            if csv_file and os.path.exists(csv_file):
                with Session(engine) as session:
                    for item in scraper.data:
                        record = SamBid(
                            notice_id=item.get("Notice ID", ""),
                            title=item.get("Notice Title", ""),
                            date_offers_due=item.get("Date Offers Due", ""),
                            published_date=item.get("Published Date", ""),
                            updated_date=item.get("Updated Date", ""),
                            inactive_dates=item.get("Office", ""),
                        )
                        session.add(record)
                    session.commit()

                _jobs[job_id]["status"]   = "stopped" if stop_event.is_set() else "done"
                _jobs[job_id]["filename"] = str(csv_file)   # coerce Path → str
            else:
                _jobs[job_id]["status"] = "error"
                _jobs[job_id]["error"]  = "No data extracted or output file not created."

        except Exception as exc:
            _jobs[job_id]["status"] = "error"
            _jobs[job_id]["error"]  = str(exc)

    threading.Thread(target=_run, daemon=True).start()
    return JSONResponse({"success": True, "job_id": job_id})


# ── SEPTA scraper ─────────────────────────────────────────────────────────────

@app.post("/scrape_septa")
async def scrape_septa(body: SeptaScrapeRequest):
    """
    Start a SEPTA scrape in a background thread.
    Returns immediately with a job_id; poll /status/{job_id} for progress.
    """
    job_id = _new_job_id("septa")
    stop_event = threading.Event()
    _jobs[job_id] = {
        "status":     "running",
        "filename":   None,
        "error":      None,
        "stop_event": stop_event,
    }

    def _run():
        try:
            config = SeptaConfig()
            browser_manager = SeptaBrowser(config)

            if not browser_manager.setup_driver(headless=True):
                _jobs[job_id]["status"] = "error"
                _jobs[job_id]["error"]  = "Failed to setup browser for SEPTA scraper."
                return

            portal = SeptaPortal(browser_manager, config)

            if not portal.login():
                browser_manager.close_driver()
                _jobs[job_id]["status"] = "error"
                _jobs[job_id]["error"]  = "SEPTA login failed."
                return

            if not portal.navigate_to_open_quotes():
                browser_manager.close_driver()
                _jobs[job_id]["status"] = "error"
                _jobs[job_id]["error"]  = "SEPTA navigation to Open Quotes failed."
                return

            portal.apply_date_filter(body.date_filter)
            quotes = portal.scrape_all_pages(stop_event=stop_event)

            excel_path = config.get_excel_path()
            DataExporter.export_to_excel(quotes, excel_path)
            browser_manager.close_driver()

            if os.path.exists(excel_path):
                with Session(engine) as session:
                    for q in quotes:
                        record = SeptaQuote(
                            requisition_number=q.get("requisition_number", ""),
                            summary=q.get("summary", ""),
                            open_date=q.get("open_date", ""),
                            close_date=q.get("close_date", ""),
                        )
                        session.add(record)
                    session.commit()

                _jobs[job_id]["status"]   = "stopped" if stop_event.is_set() else "done"
                _jobs[job_id]["filename"] = str(excel_path)   # coerce Path → str
            else:
                _jobs[job_id]["status"] = "error"
                _jobs[job_id]["error"]  = "No quotes found or Excel creation failed."

        except Exception as exc:
            _jobs[job_id]["status"] = "error"
            _jobs[job_id]["error"]  = str(exc)

    threading.Thread(target=_run, daemon=True).start()
    return JSONResponse({"success": True, "job_id": job_id})


# ── Unison scraper ────────────────────────────────────────────────────────────

@app.post("/scrape_unison")
async def scrape_unison(body: UnisonScrapeRequest):
    try:
        scraper = UnisonMarketplaceScraper()
        scraper.run_scraper(filter_by=body.filter_by)

        if os.path.exists(scraper.csv_file):
            import csv
            with open(scraper.csv_file, "r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                with Session(engine) as session:
                    for row in reader:
                        record = UnisonRequest(
                            buyer_number=row.get("Buyer#", ""),
                            buyer_description=row.get("Buyer Description", ""),
                            buyer=row.get("Buyer", ""),
                            end_date=row.get("End Date", ""),
                        )
                        session.add(record)
                    session.commit()

            return JSONResponse({"success": True, "filename": scraper.csv_file})
        else:
            return JSONResponse({
                "success": False,
                "error": "Unison scraper finished but CSV file not found (maybe no data).",
            })

    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})


# ── DIBBS scraper ─────────────────────────────────────────────────────────────

@app.post("/scrape_dibbs")
async def scrape_dibbs():
    try:
        scraper = DibbsScraper(headless=False)
        csv_file = scraper.run()

        if csv_file and os.path.exists(csv_file):
            with Session(engine) as session:
                for item in scraper.data:
                    record = DibbsBid(
                        nsn_part_number=item.get("NSN/Part Number", ""),
                        nomenclature=item.get("Nomenclature", ""),
                        solicitation=item.get("Solicitation", ""),
                        rfq_quote_status=item.get("RFQ/Quote Status", ""),
                        purchase_request=item.get("Purchase Request", ""),
                        issued=item.get("Issued", ""),
                        return_by=item.get("Return By", ""),
                    )
                    session.add(record)
                session.commit()

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
