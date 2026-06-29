import os
import threading
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlmodel import Session, select

from db import create_db_and_tables, engine
from models import ScrapeJob
from utils.excel import styled_workbook as _styled_workbook


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

    if status == "done":
        scraper_type = job_id.split("_")[0]
        threading.Thread(
            target=_run_notification,
            args=(job_id, scraper_type, record_count),
            daemon=True,
        ).start()


def _run_notification(job_id: str, scraper_type: str, record_count: int) -> None:
    from services.notifier import notify_job_completion
    notify_job_completion(job_id, scraper_type, record_count)



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
        "http://localhost:4000",
        "http://127.0.0.1:4000",
        "http://localhost:4001",
        "http://127.0.0.1:4001"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Include route modules ────────────────────────────────────────────────────

from routes.sam import router as sam_router
from routes.septa import router as septa_router
from routes.unison import router as unison_router
from routes.dibbs import router as dibbs_router
from routes.naics import router as naics_router
from routes.eval_config import router as eval_config_router

app.include_router(sam_router)
app.include_router(septa_router)
app.include_router(unison_router)
app.include_router(dibbs_router)
app.include_router(naics_router)
app.include_router(eval_config_router)


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
