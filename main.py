import os
import importlib.util
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from database import create_db_and_tables, get_session
from models import SamBid, SeptaQuote, UnisonRequest, DibbsBid
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/scrape_sam")
async def scrape(request: Request, session: Session = Depends(get_session)):
    data = await request.json()
    search_query = data.get("search_query", "")
    date_filter = data.get("date_filter", None)

    try:
        scraper = SAMGovScraper(
            headless=False, search_query=search_query, date_filter=date_filter
        )
        csv_file = scraper.run(max_records=1000)

        if csv_file and os.path.exists(csv_file):
            # Save scraped data to database
            for item in scraper.data:
                record = SamBid(
                    notice_id=item.get("Notice ID", ""),
                    title=item.get("Title", ""),
                    date_offers_due=item.get("Date Offers Due", ""),
                    published_date=item.get("Published Date", ""),
                    updated_date=item.get("Updated Date", ""),
                    inactive_dates=item.get("Inactive Dates", ""),
                )
                session.add(record)
            session.commit()

            return JSONResponse({"success": True, "filename": csv_file})
        else:
            return JSONResponse(
                {"success": False, "error": "No data extracted or file not created."}
            )

    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})


@app.post("/scrape_septa")
async def scrape_septa(request: Request, session: Session = Depends(get_session)):
    try:
        data = await request.json()
        date_filter = data.get("date_filter")

        config = SeptaConfig()
        browser_manager = SeptaBrowser(config)

        if not browser_manager.setup_driver(headless=True):
            return JSONResponse(
                {
                    "success": False,
                    "error": "Failed to setup browser for Septa Scraper",
                }
            )

        portal = SeptaPortal(browser_manager, config)

        if not portal.login():
            browser_manager.close_driver()
            return JSONResponse({"success": False, "error": "Septa Login Failed"})

        if not portal.navigate_to_open_quotes():
            browser_manager.close_driver()
            return JSONResponse(
                {"success": False, "error": "Septa Navigation Failed"}
            )

        portal.apply_date_filter(date_filter)
        quotes = portal.scrape_all_pages()

        csv_filename = config.get_csv_filename()
        csv_path = config.get_csv_path()
        DataExporter.export_to_csv(quotes, csv_path)

        browser_manager.close_driver()

        if os.path.exists(csv_path):
            # Save to database
            for q in quotes:
                record = SeptaQuote(
                    requisition_number=q.get("requisition_number", ""),
                    summary=q.get("summary", ""),
                    open_date=q.get("open_date", ""),
                    close_date=q.get("close_date", ""),
                )
                session.add(record)
            session.commit()

            return JSONResponse({"success": True, "filename": csv_filename})
        else:
            return JSONResponse(
                {
                    "success": False,
                    "error": "No quotes imported or CSV creation failed.",
                }
            )

    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})


@app.post("/scrape_unison")
async def scrape_unison(request: Request, session: Session = Depends(get_session)):
    try:
        data = await request.json()
        filter_by = data.get("filter_by")

        scraper = UnisonMarketplaceScraper()
        scraper.run_scraper(filter_by=filter_by)

        if os.path.exists(scraper.csv_file):
            # Read CSV and save to database
            import csv

            with open(scraper.csv_file, "r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
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
            return JSONResponse(
                {
                    "success": False,
                    "error": "Unison scraper finished but CSV file not found (maybe no data).",
                }
            )

    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})


@app.post("/scrape_dibbs")
async def scrape_dibbs(request: Request, session: Session = Depends(get_session)):
    try:
        scraper = DibbsScraper(headless=False)
        csv_file = scraper.run()

        if csv_file and os.path.exists(csv_file):
            # Save to database
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
            return JSONResponse(
                {
                    "success": False,
                    "error": "Dibbs scraper finished but CSV file not found.",
                }
            )

    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})


@app.get("/download/{filename:path}")
async def download_file(filename: str):
    try:
        return FileResponse(filename, filename=filename, media_type="application/octet-stream")
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=404)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)
