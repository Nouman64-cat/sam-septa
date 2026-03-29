"""
SAM.gov Scraper — 4-layer smart bid evaluator.

Evaluates a bid's full text (description + extracted document text) through
a fast, tiered pipeline:

  Layer 1  Kill-Word Sieve       → instant REJECT if dealbreaker found
  Layer 2  Geographic Tripwire   → instant PASS if no restricted territory
  Layer 3  Context Extraction    → slice ~250 tokens around territory match
  Layer 4  GPU Inference (Ollama)→ SERVICES=REJECT / HARDWARE=PASS

Only ~1 % of bids ever reach Layer 4. The full 120 K-char payload is never
sent to the LLM — only the ~250-token context window is.
"""

import logging
import time

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Layer 1 — Kill-Word Sieve
# ---------------------------------------------------------------------------

def _layer1_kill_words(full_text_lower: str, kill_words: list[str]) -> str | None:
    """
    Return the first kill-word found in *full_text_lower*, or None.
    """
    for word in kill_words:
        if word in full_text_lower:
            return word
    return None


# ---------------------------------------------------------------------------
# Layer 2 — Geographic Tripwire
# ---------------------------------------------------------------------------

def _layer2_territory_check(
    full_text_lower: str,
    territories: list[str],
) -> tuple[str | None, int]:
    """
    Return (territory, match_index) for the first restricted territory found,
    or (None, -1) if none match.
    """
    for territory in territories:
        idx = full_text_lower.find(territory)
        if idx != -1:
            return territory, idx
    return None, -1


# ---------------------------------------------------------------------------
# Layer 3 — Context Extraction
# ---------------------------------------------------------------------------

def _layer3_extract_context(
    full_text: str,
    match_index: int,
    max_chars: int = 1000,
    paragraph_window: int = 1,
) -> str:
    """
    Slice out the paragraph containing *match_index* plus ±paragraph_window
    surrounding paragraphs.  Cap at *max_chars* characters.
    """
    paragraphs = full_text.split("\n\n")
    if not paragraphs:
        return full_text[:max_chars]

    # Map match_index to a paragraph index via cumulative offsets
    offset = 0
    target_idx = 0
    for i, para in enumerate(paragraphs):
        # +2 accounts for the "\n\n" delimiter between paragraphs
        end = offset + len(para) + (2 if i < len(paragraphs) - 1 else 0)
        if match_index < end:
            target_idx = i
            break
        offset = end

    lo = max(0, target_idx - paragraph_window)
    hi = min(len(paragraphs), target_idx + paragraph_window + 1)

    context = "\n\n".join(paragraphs[lo:hi])

    if len(context) > max_chars:
        # Centre the window around the match point within the context
        local_idx = match_index - sum(
            len(paragraphs[j]) + 2 for j in range(lo)
        )
        local_idx = max(0, min(local_idx, len(context)))
        half = max_chars // 2
        start = max(0, local_idx - half)
        end = start + max_chars
        if end > len(context):
            end = len(context)
            start = max(0, end - max_chars)
        context = context[start:end]

    return context


# ---------------------------------------------------------------------------
# Layer 4 — GPU Inference via Ollama
# ---------------------------------------------------------------------------

def _layer4_llm_classify(
    context_snippet: str,
    model: str = "llama3",
    timeout: int = 30,
) -> tuple[str, str]:
    """
    Send the context snippet to Ollama and get a SERVICES / HARDWARE answer.

    Returns (classification, raw_response).
    classification is "SERVICES", "HARDWARE", or "AMBIGUOUS".
    """
    try:
        import ollama
    except ImportError:
        raise RuntimeError(
            "The 'ollama' Python package is not installed. "
            "Run: pip install ollama"
        )

    prompt = (
        "Does the following text describe providing services or hardware?\n"
        "Answer with exactly one word: SERVICES or HARDWARE.\n\n"
        f"Text:\n{context_snippet}"
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
    if "SERVICES" in raw_upper:
        return "SERVICES", raw
    if "HARDWARE" in raw_upper:
        return "HARDWARE", raw
    return "AMBIGUOUS", raw


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def evaluate_bid(bid_id: str, full_text: str, config: dict) -> dict:
    """
    Run the 4-layer evaluation pipeline on a bid.

    Parameters
    ----------
    bid_id    : Unique bid identifier (passed through to the result).
    full_text : Combined description + document text.
    config    : The ``sam`` section of config.yml (must contain ``evaluation``).

    Returns
    -------
    dict with keys: bid_id, decision, stopped_at_layer, reason,
    kill_word_found, territory_found, context_snippet,
    llm_classification, llm_raw_response, elapsed_ms.
    """
    t0 = time.perf_counter()

    eval_cfg = config.get("evaluation", {})
    kill_words = [w.lower() for w in eval_cfg.get("kill_words", [])]
    territories = [t.lower() for t in eval_cfg.get("restricted_territories", [])]
    max_chars = eval_cfg.get("context_max_chars", 1000)
    para_window = eval_cfg.get("paragraph_window", 1)
    ollama_model = eval_cfg.get("ollama_model", "llama3")
    ollama_timeout = eval_cfg.get("ollama_timeout", 30)

    result = {
        "bid_id": bid_id,
        "decision": None,
        "stopped_at_layer": None,
        "reason": "",
        "kill_word_found": None,
        "territory_found": None,
        "context_snippet": None,
        "llm_classification": None,
        "llm_raw_response": None,
        "elapsed_ms": 0.0,
    }

    full_text_lower = full_text.lower()

    # ── Layer 1: Kill-Word Sieve ─────────────────────────────────────────
    hit = _layer1_kill_words(full_text_lower, kill_words)
    if hit:
        result.update(
            decision="REJECT",
            stopped_at_layer=1,
            reason=f"Contains dealbreaker: {hit}",
            kill_word_found=hit,
        )
        result["elapsed_ms"] = (time.perf_counter() - t0) * 1000
        logger.info(f"[EVAL] {bid_id} -> REJECT @ Layer 1 (kill-word: {hit})")
        return result

    # ── Layer 2: Geographic Tripwire ─────────────────────────────────────
    territory, match_idx = _layer2_territory_check(full_text_lower, territories)
    if territory is None:
        result.update(
            decision="PASS",
            stopped_at_layer=2,
            reason="Mainland USA default",
        )
        result["elapsed_ms"] = (time.perf_counter() - t0) * 1000
        logger.info(f"[EVAL] {bid_id} -> PASS @ Layer 2 (no restricted territory)")
        return result

    result["territory_found"] = territory

    # ── Layer 3: Context Extraction ──────────────────────────────────────
    context = _layer3_extract_context(full_text, match_idx, max_chars, para_window)
    result["context_snippet"] = context
    logger.info(
        f"[EVAL] {bid_id} -> territory '{territory}' found, "
        f"extracted {len(context)} char context -> proceeding to Layer 4"
    )

    # ── Layer 4: GPU Inference ───────────────────────────────────────────
    try:
        classification, raw_resp = _layer4_llm_classify(
            context, model=ollama_model, timeout=ollama_timeout
        )
    except RuntimeError as exc:
        result.update(
            decision="ERROR",
            stopped_at_layer=4,
            reason=str(exc),
        )
        result["elapsed_ms"] = (time.perf_counter() - t0) * 1000
        logger.error(f"[EVAL] {bid_id} -> ERROR @ Layer 4: {exc}")
        return result

    result["llm_classification"] = classification
    result["llm_raw_response"] = raw_resp

    if classification == "SERVICES":
        result.update(
            decision="REJECT",
            stopped_at_layer=4,
            reason=f"Restricted Territory ({territory.title()}) + Services",
        )
    elif classification == "HARDWARE":
        result.update(
            decision="PASS",
            stopped_at_layer=4,
            reason=f"Restricted Territory ({territory.title()}) + Hardware Exception",
        )
    else:
        # Ambiguous → conservative REJECT
        result.update(
            decision="REJECT",
            stopped_at_layer=4,
            reason=f"Restricted Territory ({territory.title()}) + Ambiguous LLM response",
        )

    result["elapsed_ms"] = (time.perf_counter() - t0) * 1000
    logger.info(
        f"[EVAL] {bid_id} -> {result['decision']} @ Layer 4 "
        f"(territory={territory}, llm={classification})"
    )
    return result
