"""Unison Marketplace scraper route."""

import csv
import os

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlmodel import Session

from db import engine
from models import UnisonRequest, UnisonScrapeRequest
from scrappers.unison.unison_scraper import UnisonMarketplaceScraper

router = APIRouter()


@router.post("/scrape_unison")
async def scrape_unison(body: UnisonScrapeRequest):
    try:
        scraper = UnisonMarketplaceScraper()
        scraper.run_scraper(filter_by=body.filter_by)

        if os.path.exists(scraper.csv_file):
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
