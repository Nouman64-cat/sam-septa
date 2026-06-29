import sys
import traceback
from sqlmodel import Session, select
from db import engine
from models import SamBid
from utils.excel import styled_workbook

try:
    with Session(engine) as s:
        bids = s.exec(select(SamBid)).all()
        print("Found", len(bids), "bids")
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
        stream = styled_workbook("SAM Bids", headers, rows)
        print("Workbook generated.")
except Exception as e:
    traceback.print_exc()
