import csv
import os
from datetime import datetime, date
from sqlmodel import Session, select
from db import engine
from models import SamBid
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE

os.makedirs("store_data", exist_ok=True)

# Using today's date based on server time
today = date.today()

with Session(engine) as s:
    query = select(SamBid).where(SamBid.scraped_at >= today)
    bids = s.exec(query.order_by(SamBid.scraped_at.desc())).all()

headers = [
    "Notice Title", "Notice ID", "Decision", "Reason",
    "Department/Ind. Agency", "Description", "Subtier", "Updated Date",
    "Bid Repeat Count", "NAICS Code", "NAICS Title",
    "Date Offers Due", "Published Date", "Office",
]

with open("store_data/file1.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(headers)
    for b in bids:
        row = [
            b.title, b.notice_id, b.decision or "PENDING", b.reason or "",
            b.department, b.description,
            b.subtier, b.updated_date, b.bid_repeat_count,
            b.naics_code, b.naics_title,
            b.date_offers_due, b.published_date, b.office,
        ]
        cleaned_row = [
            ILLEGAL_CHARACTERS_RE.sub("", str(val)) if val is not None else ""
            for val in row
        ]
        writer.writerow(cleaned_row)

print(f"Exported {len(bids)} bids to store_data/file1.csv")
