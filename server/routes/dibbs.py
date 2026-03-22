"""DIBBS scraper route."""

import os
import importlib.util

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlmodel import Session

from database import engine
from models import DibbsBid

# Import Dibbs Scraper (handling hyphen in filename)
try:
    spec_dibbs = importlib.util.spec_from_file_location("dibbs_module", "dibbs-scrapper.py")
    dibbs_module = importlib.util.module_from_spec(spec_dibbs)
    spec_dibbs.loader.exec_module(dibbs_module)
    DibbsScraper = dibbs_module.DibbsScraper
except Exception as e:
    print(f"Error importing Dibbs scraper: {e}")

router = APIRouter()


@router.post("/scrape_dibbs")
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
