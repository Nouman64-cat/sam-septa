"""Eval Config routes — manage kill_words, excluded_services, and allowed_services via the DB."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from db import engine
from models.eval_config import EvalConfig

router = APIRouter(prefix="/eval-config", tags=["eval-config"])

CATEGORY_KILL_WORD        = "kill_word"
CATEGORY_EXCLUDED_SERVICE = "excluded_service"
CATEGORY_ALLOWED_SERVICE  = "allowed_service"

_ERR_EMPTY = "value must not be empty"


class EvalConfigValueRequest(BaseModel):
    value: str


# ---------------------------------------------------------------------------
# GET — return all three lists in one call
# ---------------------------------------------------------------------------

@router.get("")
async def get_eval_config():
    """Return all kill words, excluded services, and allowed services from DB."""
    with Session(engine) as s:
        rows = s.exec(select(EvalConfig)).all()

    kill_words        = sorted(r.value for r in rows if r.category == CATEGORY_KILL_WORD)
    excluded_services = sorted(r.value for r in rows if r.category == CATEGORY_EXCLUDED_SERVICE)
    allowed_services  = sorted(r.value for r in rows if r.category == CATEGORY_ALLOWED_SERVICE)

    return JSONResponse({
        "kill_words":        kill_words,
        "excluded_services": excluded_services,
        "allowed_services":  allowed_services,
    })


# ---------------------------------------------------------------------------
# Kill-word endpoints
# ---------------------------------------------------------------------------

@router.post("/kill-words")
async def add_kill_word(body: EvalConfigValueRequest):
    """Add a kill word. Duplicate values are silently ignored."""
    value = body.value.strip().lower()
    if not value:
        raise HTTPException(status_code=422, detail=_ERR_EMPTY)

    with Session(engine) as s:
        existing = s.exec(
            select(EvalConfig).where(
                EvalConfig.category == CATEGORY_KILL_WORD,
                EvalConfig.value == value,
            )
        ).first()
        if not existing:
            s.add(EvalConfig(category=CATEGORY_KILL_WORD, value=value))
            s.commit()

    return JSONResponse({"success": True, "value": value})


@router.delete("/kill-words/{value}")
async def delete_kill_word(value: str):
    """Remove a kill word."""
    value = value.strip().lower()
    with Session(engine) as s:
        row = s.exec(
            select(EvalConfig).where(
                EvalConfig.category == CATEGORY_KILL_WORD,
                EvalConfig.value == value,
            )
        ).first()
        if not row:
            raise HTTPException(status_code=404, detail=f"Kill word '{value}' not found")
        s.delete(row)
        s.commit()

    return JSONResponse({"success": True, "value": value})


# ---------------------------------------------------------------------------
# Excluded service endpoints (Rule B)
# ---------------------------------------------------------------------------

@router.post("/excluded-services")
async def add_excluded_service(body: EvalConfigValueRequest):
    """Add an excluded service category (Rule B). Duplicate values are silently ignored."""
    value = body.value.strip().lower()
    if not value:
        raise HTTPException(status_code=422, detail=_ERR_EMPTY)

    with Session(engine) as s:
        existing = s.exec(
            select(EvalConfig).where(
                EvalConfig.category == CATEGORY_EXCLUDED_SERVICE,
                EvalConfig.value == value,
            )
        ).first()
        if not existing:
            s.add(EvalConfig(category=CATEGORY_EXCLUDED_SERVICE, value=value))
            s.commit()

    return JSONResponse({"success": True, "value": value})


@router.delete("/excluded-services/{value}")
async def delete_excluded_service(value: str):
    """Remove an excluded service category."""
    value = value.strip().lower()
    with Session(engine) as s:
        row = s.exec(
            select(EvalConfig).where(
                EvalConfig.category == CATEGORY_EXCLUDED_SERVICE,
                EvalConfig.value == value,
            )
        ).first()
        if not row:
            raise HTTPException(status_code=404, detail=f"Excluded service '{value}' not found")
        s.delete(row)
        s.commit()

    return JSONResponse({"success": True, "value": value})


# ---------------------------------------------------------------------------
# Allowed service endpoints (Rule C)
# ---------------------------------------------------------------------------

@router.post("/allowed-services")
async def add_allowed_service(body: EvalConfigValueRequest):
    """Add an allowed service category (Rule C). Duplicate values are silently ignored."""
    value = body.value.strip().lower()
    if not value:
        raise HTTPException(status_code=422, detail=_ERR_EMPTY)

    with Session(engine) as s:
        existing = s.exec(
            select(EvalConfig).where(
                EvalConfig.category == CATEGORY_ALLOWED_SERVICE,
                EvalConfig.value == value,
            )
        ).first()
        if not existing:
            s.add(EvalConfig(category=CATEGORY_ALLOWED_SERVICE, value=value))
            s.commit()

    return JSONResponse({"success": True, "value": value})


@router.delete("/allowed-services/{value}")
async def delete_allowed_service(value: str):
    """Remove an allowed service category."""
    value = value.strip().lower()
    with Session(engine) as s:
        row = s.exec(
            select(EvalConfig).where(
                EvalConfig.category == CATEGORY_ALLOWED_SERVICE,
                EvalConfig.value == value,
            )
        ).first()
        if not row:
            raise HTTPException(status_code=404, detail=f"Allowed service '{value}' not found")
        s.delete(row)
        s.commit()

    return JSONResponse({"success": True, "value": value})
