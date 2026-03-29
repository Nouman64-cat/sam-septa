"""Eval Config routes — manage kill_words and allowed_states via the DB."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from db import engine
from models.eval_config import EvalConfig

router = APIRouter(prefix="/eval-config", tags=["eval-config"])

CATEGORY_KILL_WORD    = "kill_word"
CATEGORY_ALLOWED_STATE = "allowed_state"


class EvalConfigValueRequest(BaseModel):
    value: str


# ---------------------------------------------------------------------------
# GET — return both lists in one call
# ---------------------------------------------------------------------------

@router.get("")
async def get_eval_config():
    """Return all kill words and allowed states from DB."""
    with Session(engine) as s:
        rows = s.exec(select(EvalConfig)).all()

    kill_words    = sorted(r.value for r in rows if r.category == CATEGORY_KILL_WORD)
    allowed_states = sorted(r.value for r in rows if r.category == CATEGORY_ALLOWED_STATE)

    return JSONResponse({
        "kill_words":    kill_words,
        "allowed_states": allowed_states,
    })


# ---------------------------------------------------------------------------
# Kill-word endpoints
# ---------------------------------------------------------------------------

@router.post("/kill-words")
async def add_kill_word(body: EvalConfigValueRequest):
    """Add a kill word. Duplicate values are silently ignored."""
    value = body.value.strip().lower()
    if not value:
        raise HTTPException(status_code=422, detail="value must not be empty")

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
# Allowed-state endpoints
# ---------------------------------------------------------------------------

@router.post("/allowed-states")
async def add_allowed_state(body: EvalConfigValueRequest):
    """Add a state/region to the allowed list. Duplicate values are silently ignored."""
    value = body.value.strip().lower()
    if not value:
        raise HTTPException(status_code=422, detail="value must not be empty")

    with Session(engine) as s:
        existing = s.exec(
            select(EvalConfig).where(
                EvalConfig.category == CATEGORY_ALLOWED_STATE,
                EvalConfig.value == value,
            )
        ).first()
        if not existing:
            s.add(EvalConfig(category=CATEGORY_ALLOWED_STATE, value=value))
            s.commit()

    return JSONResponse({"success": True, "value": value})


@router.delete("/allowed-states/{value}")
async def delete_allowed_state(value: str):
    """Remove a state/region from the allowed list."""
    value = value.strip().lower()
    with Session(engine) as s:
        row = s.exec(
            select(EvalConfig).where(
                EvalConfig.category == CATEGORY_ALLOWED_STATE,
                EvalConfig.value == value,
            )
        ).first()
        if not row:
            raise HTTPException(status_code=404, detail=f"Allowed state '{value}' not found")
        s.delete(row)
        s.commit()

    return JSONResponse({"success": True, "value": value})
