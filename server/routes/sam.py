"""SAM.gov scraper routes — scrape + export + evaluate."""

import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, StreamingResponse
from sqlmodel import Session, select

from db import engine
from models import ScrapeJob, SamBid, SamScrapeRequest, SamEvaluateRequest
from models.eval_config import EvalConfig
from scrappers.sam.sam_scraper import SAMGovScraper
from scrappers.sam.evaluator import evaluate_bid


# ── Load SAM config once at module level ──────────────────────────────────────
_SAM_CFG_PATH = Path(__file__).resolve().parent.parent / "scrappers" / "sam" / "config.yml"
with open(_SAM_CFG_PATH, "r", encoding="utf-8") as _f:
    _SAM_CONFIG = yaml.safe_load(_f).get("sam", {})

router = APIRouter()


# ---------------------------------------------------------------------------
# Scrape
# ---------------------------------------------------------------------------

@router.post("/scrape_sam")
async def scrape_sam(body: SamScrapeRequest):
    """Start a SAM.gov scrape. Returns job_id immediately; poll /status/{job_id}."""
    from main import _jobs, _new_job_id, _finish_job

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
        """Called per extracted bid — evaluates, then inserts to DB and updates live counter."""
        # Run the NAICS-first evaluator using the Full Text already in memory.
        # Kill words are fetched live from DB so UI changes take effect
        # immediately without a server restart. Requirement-type (hardware vs
        # service), Rule B/C and location are decided from the NAICS code and
        # the notice title per SAM_Bid_Evaluation_Spec_v1.
        full_text  = bid.get("Full Text", "")
        notice_id  = bid.get("Notice ID") or bid.get("Notice Title", "unknown")
        title      = bid.get("Notice Title", "")
        naics_code = bid.get("NAICS Code", "")

        try:
            with Session(engine) as _es:
                cfg_rows = _es.exec(select(EvalConfig)).all()
            kill_words = [r.value for r in cfg_rows if r.category == "kill_word"]

            _eval_cfg = dict(_SAM_CONFIG)
            _eval_cfg["evaluation"] = dict(_eval_cfg.get("evaluation", {}))
            _eval_cfg["evaluation"]["kill_words"] = kill_words

            eval_result = evaluate_bid(
                notice_id, full_text, _eval_cfg,
                naics_code=naics_code, title=title,
            )
            decision = eval_result.get("decision", "PENDING")
            reason   = eval_result.get("reason", "")
        except Exception as _eval_err:
            decision = "PENDING"
            reason   = f"Evaluation error: {_eval_err}"

        with Session(engine) as s:
            s.add(SamBid(
                job_id           = job_id,
                notice_id        = notice_id,
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
                decision         = decision,
                reason           = reason,
            ))
            s.commit()
        _jobs[job_id]["record_count"] += 1

    def _run():
        try:
            scraper = SAMGovScraper(
                headless     = body.headless,
                date_filter  = body.date_filter,
                date_to      = body.date_to,
                naics_codes  = body.naics_codes,
                award_notice = body.award_notice,
            )
            scraper._stop_event       = stop_event
            scraper.skip_csv          = True      # no CSV files
            scraper._on_bid_extracted = _on_bid   # live DB insert per bid
            _jobs[job_id]["scraper"]  = scraper   # store for live preview

            scraper.run(max_records=1000)

            final = "stopped" if stop_event.is_set() else "done"
            _finish_job(job_id, final, _jobs[job_id]["record_count"])

        except Exception as exc:
            _finish_job(job_id, "error", _jobs[job_id]["record_count"], str(exc))

    threading.Thread(target=_run, daemon=True).start()
    return JSONResponse({"success": True, "job_id": job_id})


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

@router.get("/export/sam")
async def export_sam(job_id: Optional[str] = Query(default=None)):
    """
    Export SAM bids to a styled Excel file.
    - ?job_id=sam_... → only that run's bids
    - no param         → all bids in DB
    """
    from main import _styled_workbook

    with Session(engine) as s:
        query = select(SamBid)
        if job_id:
            query = query.where(SamBid.job_id == job_id)
        bids = s.exec(query.order_by(SamBid.scraped_at.desc())).all()

    headers = [
        "Notice Title", "Notice ID", "Decision", "Reason",
        "Department/Ind. Agency", "Description", "Subtier", "Updated Date",
        "Bid Repeat Count", "NAICS Code", "NAICS Title",
        "Date Offers Due", "Published Date", "Office",
    ]
    rows = [
        [
            b.title, b.notice_id, b.decision or "PENDING", b.reason or "",
            b.department, b.description,
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


# ---------------------------------------------------------------------------
# Evaluate
# ---------------------------------------------------------------------------

@router.post("/evaluate-sam")
async def evaluate_sam(body: SamEvaluateRequest):
    """
    NAICS-first bid evaluator (SAM_Bid_Evaluation_Spec_v1).

    Accepts bid_id + full_text (+ optional naics_code, title), returns
    PURSUE / REJECT / MANUAL_REVIEW with a standard-phrase reason.
    Steps: Kill-Word → Requirement Type (hardware/service) → Rule B → Rule C → Location.
    """
    with Session(engine) as _es:
        cfg_rows = _es.exec(select(EvalConfig)).all()
    kill_words = [r.value for r in cfg_rows if r.category == "kill_word"]

    _eval_cfg = dict(_SAM_CONFIG)
    _eval_cfg["evaluation"] = dict(_eval_cfg.get("evaluation", {}))
    _eval_cfg["evaluation"]["kill_words"] = kill_words

    result = evaluate_bid(
        body.bid_id, body.full_text, _eval_cfg,
        naics_code=body.naics_code or "", title=body.title or "",
    )

    status_code = 503 if result["decision"] == "ERROR" else 200
    return JSONResponse(content=result, status_code=status_code)


@router.get("/sam/screenshot/{job_id}")
async def get_sam_screenshot(job_id: str):
    """Fetch a live base64 screenshot from the running scraper."""
    from main import _jobs
    job = _jobs.get(job_id)
    if not job or "scraper" not in job:
        return JSONResponse({"error": "Job not found or scraper not active"}, status_code=404)
    
    scraper: SAMGovScraper = job["scraper"]
    b64 = scraper.get_screenshot_base64()
    if not b64:
        return JSONResponse({"error": "Could not capture screenshot"}, status_code=500)
    
    return JSONResponse({"screenshot": b64})
