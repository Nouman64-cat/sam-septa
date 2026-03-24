"""Models for DIBBS bids."""

from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class DibbsBid(SQLModel, table=True):
    __tablename__ = "dibbs_bids"

    id:                Optional[int] = Field(default=None, primary_key=True)
    nsn_part_number:   str           = Field(default="", max_length=255)
    nomenclature:      str           = Field(default="")
    solicitation:      str           = Field(default="", max_length=255)
    rfq_quote_status:  str           = Field(default="", max_length=255)
    purchase_request:  str           = Field(default="", max_length=255)
    issued:            str           = Field(default="", max_length=255)
    return_by:         str           = Field(default="", max_length=255)
    created_at:        datetime      = Field(default_factory=datetime.utcnow)
