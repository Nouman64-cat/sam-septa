"""
SAM.gov Scraper — bid evaluator (DOC-20260625 criteria).

Decision flow (requirement-type-first, location second):

  Step 1  Kill-Word Sieve        → instant REJECT if dealbreaker found
  Step 2  Requirement Type (LLM) → HARDWARE → PURSUE (any location)
  Step 3  Excluded Service? (LLM)→ Rule B match → REJECT (any location)
  Step 4  Allowed Service? (LLM) → Rule C match → proceed to Step 5
  Step 5  Place of Performance   → US Mainland → PURSUE, else REJECT
           (keyword check first, LLM fallback)

When a service matches neither Rule B nor Rule C:
  - US Mainland → MANUAL_REVIEW
  - Outside US Mainland → REJECT
"""

import logging
import time

logger = logging.getLogger(__name__)

# Non-mainland US territories — always outside US Mainland for services
_NON_MAINLAND = [
    "guam",
    "puerto rico",
    "us virgin islands",
    "u.s. virgin islands",
    "american samoa",
    "northern mariana islands",
]


# ---------------------------------------------------------------------------
# Step 1 — Kill-Word Sieve
# ---------------------------------------------------------------------------

def _step1_kill_words(full_text_lower: str, kill_words: list[str]) -> str | None:
    for word in kill_words:
        if word in full_text_lower:
            return word
    return None


# ---------------------------------------------------------------------------
# LLM helper
# ---------------------------------------------------------------------------

def _call_llm(
    prompt: str,
    expected_words: list[str],
    model: str = "llama3",
) -> tuple[str, str]:
    """
    Call Ollama and return (matched_keyword | "AMBIGUOUS", raw_response).
    Matches the first expected_word found (case-insensitive) in the response.
    """
    try:
        import ollama
    except ImportError:
        raise RuntimeError(
            "The 'ollama' Python package is not installed. Run: pip install ollama"
        )

    try:
        response = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.0, "num_predict": 10},
        )
        raw = response["message"]["content"].strip()
    except Exception as exc:
        raise RuntimeError(f"Ollama request failed: {exc}")

    raw_upper = raw.upper()
    for word in expected_words:
        if word.upper() in raw_upper:
            return word, raw
    return "AMBIGUOUS", raw


# ---------------------------------------------------------------------------
# Step 2 — Requirement Type Classification
# ---------------------------------------------------------------------------

def _step2_classify_requirement(
    full_text: str, model: str = "llama3"
) -> tuple[str, str]:
    """Returns ("HARDWARE" | "SERVICE" | "AMBIGUOUS", raw_response)."""
    prompt = (
        "You are evaluating a US government procurement bid.\n"
        "Is the PRIMARY requirement of this bid for:\n"
        "- HARDWARE: physical goods, equipment, materials, supplies, or products to be delivered\n"
        "- SERVICE: work to be performed, labor, maintenance, repair, installation, or professional services\n\n"
        "Answer with exactly one word: HARDWARE or SERVICE.\n\n"
        f"Bid text:\n{full_text[:3000]}"
    )
    return _call_llm(prompt, ["HARDWARE", "SERVICE"], model)


# ---------------------------------------------------------------------------
# Step 3 — Excluded Service Check (Rule B)
# ---------------------------------------------------------------------------

def _step3_excluded_service(
    full_text: str,
    excluded_services: list[str],
    model: str = "llama3",
) -> tuple[str, str]:
    """Returns ("YES" | "NO" | "AMBIGUOUS", raw_response)."""
    if not excluded_services:
        return "NO", ""

    services_list = "\n".join(f"- {s}" for s in excluded_services)
    prompt = (
        "You are evaluating a US government procurement bid.\n"
        "Does the PRIMARY service requirement of this bid match any of the following "
        "EXCLUDED service categories?\n\n"
        f"EXCLUDED categories:\n{services_list}\n\n"
        "Answer with exactly one word: YES (if it matches any category) or NO (if it does not).\n\n"
        f"Bid text:\n{full_text[:3000]}"
    )
    return _call_llm(prompt, ["YES", "NO"], model)


# ---------------------------------------------------------------------------
# Step 4 — Allowed Service Check (Rule C)
# ---------------------------------------------------------------------------

def _step4_allowed_service(
    full_text: str,
    allowed_services: list[str],
    model: str = "llama3",
) -> tuple[str, str]:
    """Returns ("YES" | "NO" | "AMBIGUOUS", raw_response)."""
    if not allowed_services:
        return "NO", ""

    services_list = "\n".join(f"- {s}" for s in allowed_services)
    prompt = (
        "You are evaluating a US government procurement bid.\n"
        "Does the PRIMARY service requirement of this bid match any of the following "
        "ALLOWED service categories?\n\n"
        f"ALLOWED categories:\n{services_list}\n\n"
        "Answer with exactly one word: YES (if it matches any category) or NO (if it does not).\n\n"
        f"Bid text:\n{full_text[:3000]}"
    )
    return _call_llm(prompt, ["YES", "NO"], model)


# ---------------------------------------------------------------------------
# Step 5 — Place of Performance Check
# ---------------------------------------------------------------------------

def _step5_location_check(
    full_text: str, model: str = "llama3"
) -> tuple[str, str]:
    """
    Returns ("US_MAINLAND" | "OUTSIDE_MAINLAND", raw_response).

    Fast path: keyword match against known non-mainland territories.
    LLM fallback: ask the model to classify the place of performance.
    """
    text_lower = full_text.lower()

    for territory in _NON_MAINLAND:
        if territory in text_lower:
            return "OUTSIDE_MAINLAND", f"keyword: {territory}"

    prompt = (
        "You are evaluating a US government procurement bid.\n"
        "Is the place of performance (where the work will be done) within the "
        "United States Mainland?\n\n"
        "US MAINLAND = all 50 US states + Washington D.C.\n"
        "NOT US MAINLAND = Guam, Puerto Rico, US Virgin Islands, American Samoa, "
        "Northern Mariana Islands, or any foreign country.\n\n"
        "Answer with exactly one word: MAINLAND or OUTSIDE.\n\n"
        f"Bid text:\n{full_text[:3000]}"
    )
    raw_class, raw_resp = _call_llm(prompt, ["MAINLAND", "OUTSIDE"], model)
    if raw_class == "MAINLAND":
        return "US_MAINLAND", raw_resp
    # OUTSIDE or AMBIGUOUS — conservative fallback is OUTSIDE
    return "OUTSIDE_MAINLAND", raw_resp


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def evaluate_bid(bid_id: str, full_text: str, config: dict) -> dict:
    """
    Run the DOC-20260625 evaluation pipeline on a bid.

    Parameters
    ----------
    bid_id    : Unique bid identifier (passed through to the result).
    full_text : Combined description + document text.
    config    : The ``sam`` section of config.yml (must contain ``evaluation``).

    Returns
    -------
    dict with keys:
      bid_id, decision, stopped_at_step, reason,
      kill_word_found, requirement_type,
      service_excluded, service_allowed, location,
      llm_raw_responses, elapsed_ms.

    decision values: PURSUE | REJECT | MANUAL_REVIEW | ERROR
    """
    t0 = time.perf_counter()

    eval_cfg         = config.get("evaluation", {})
    kill_words       = [w.lower() for w in eval_cfg.get("kill_words", [])]
    excluded_services = eval_cfg.get("excluded_services", [])
    allowed_services  = eval_cfg.get("allowed_services", [])
    ollama_model     = eval_cfg.get("ollama_model", "llama3")

    result = {
        "bid_id":            bid_id,
        "decision":          None,
        "stopped_at_step":   None,
        "reason":            "",
        "kill_word_found":   None,
        "requirement_type":  None,
        "service_excluded":  None,
        "service_allowed":   None,
        "location":          None,
        "llm_raw_responses": [],
        "elapsed_ms":        0.0,
    }

    full_text_lower = full_text.lower()

    # ── Step 1: Kill-Word Sieve ──────────────────────────────────────────────
    hit = _step1_kill_words(full_text_lower, kill_words)
    if hit:
        result.update(
            decision="REJECT",
            stopped_at_step=1,
            reason=f"Contains dealbreaker: {hit}",
            kill_word_found=hit,
        )
        result["elapsed_ms"] = (time.perf_counter() - t0) * 1000
        logger.info(f"[EVAL] {bid_id} -> REJECT @ Step 1 (kill-word: {hit})")
        return result

    # ── Step 2: Requirement Type Classification ──────────────────────────────
    try:
        req_type, raw2 = _step2_classify_requirement(full_text, ollama_model)
    except RuntimeError as exc:
        result.update(decision="ERROR", stopped_at_step=2, reason=str(exc))
        result["elapsed_ms"] = (time.perf_counter() - t0) * 1000
        logger.exception(f"[EVAL] {bid_id} -> ERROR @ Step 2")
        return result

    result["requirement_type"] = req_type
    result["llm_raw_responses"].append({"step": 2, "raw": raw2})

    if req_type == "HARDWARE":
        result.update(
            decision="PURSUE",
            stopped_at_step=2,
            reason="Hardware/material requirement — pursued regardless of location (Rule A)",
        )
        result["elapsed_ms"] = (time.perf_counter() - t0) * 1000
        logger.info(f"[EVAL] {bid_id} -> PURSUE @ Step 2 (HARDWARE)")
        return result

    if req_type == "AMBIGUOUS":
        result.update(
            decision="REJECT",
            stopped_at_step=2,
            reason="Could not classify requirement type — conservative REJECT",
        )
        result["elapsed_ms"] = (time.perf_counter() - t0) * 1000
        logger.info(f"[EVAL] {bid_id} -> REJECT @ Step 2 (AMBIGUOUS requirement type)")
        return result

    # req_type == "SERVICE" — continue to service list checks

    # ── Step 3: Excluded Service Check (Rule B) ──────────────────────────────
    try:
        excluded, raw3 = _step3_excluded_service(
            full_text, excluded_services, ollama_model
        )
    except RuntimeError as exc:
        result.update(decision="ERROR", stopped_at_step=3, reason=str(exc))
        result["elapsed_ms"] = (time.perf_counter() - t0) * 1000
        logger.exception(f"[EVAL] {bid_id} -> ERROR @ Step 3")
        return result

    result["service_excluded"] = excluded
    result["llm_raw_responses"].append({"step": 3, "raw": raw3})

    if excluded == "YES":
        result.update(
            decision="REJECT",
            stopped_at_step=3,
            reason="Excluded service category (Rule B) — rejected regardless of location",
        )
        result["elapsed_ms"] = (time.perf_counter() - t0) * 1000
        logger.info(f"[EVAL] {bid_id} -> REJECT @ Step 3 (excluded service Rule B)")
        return result

    # ── Step 4: Allowed Service Check (Rule C) ───────────────────────────────
    try:
        allowed, raw4 = _step4_allowed_service(
            full_text, allowed_services, ollama_model
        )
    except RuntimeError as exc:
        result.update(decision="ERROR", stopped_at_step=4, reason=str(exc))
        result["elapsed_ms"] = (time.perf_counter() - t0) * 1000
        logger.exception(f"[EVAL] {bid_id} -> ERROR @ Step 4")
        return result

    result["service_allowed"] = allowed
    result["llm_raw_responses"].append({"step": 4, "raw": raw4})

    # ── Step 5: Place of Performance Check ──────────────────────────────────
    try:
        location, raw5 = _step5_location_check(full_text, ollama_model)
    except RuntimeError as exc:
        result.update(decision="ERROR", stopped_at_step=5, reason=str(exc))
        result["elapsed_ms"] = (time.perf_counter() - t0) * 1000
        logger.exception(f"[EVAL] {bid_id} -> ERROR @ Step 5")
        return result

    result["location"] = location
    result["llm_raw_responses"].append({"step": 5, "raw": raw5})

    if allowed == "NO":
        # Service not on either list — matrix: US Mainland → MANUAL_REVIEW, else → REJECT
        if location == "US_MAINLAND":
            result.update(
                decision="MANUAL_REVIEW",
                stopped_at_step=5,
                reason="Service not in allowed/excluded list + US Mainland — manual review required",
            )
        else:
            result.update(
                decision="REJECT",
                stopped_at_step=5,
                reason="Service not in allowed/excluded list + outside US Mainland",
            )
    elif location == "US_MAINLAND":
        # Allowed service + US Mainland → PURSUE (Rule C)
        result.update(
            decision="PURSUE",
            stopped_at_step=5,
            reason="Allowed service (Rule C) + US Mainland place of performance",
        )
    else:
        # Allowed service + outside US Mainland → REJECT (Rule C)
        result.update(
            decision="REJECT",
            stopped_at_step=5,
            reason="Allowed service (Rule C) but performed outside US Mainland",
        )

    result["elapsed_ms"] = (time.perf_counter() - t0) * 1000
    logger.info(
        f"[EVAL] {bid_id} -> {result['decision']} @ Step 5 "
        f"(service_allowed={allowed}, location={location})"
    )
    return result
