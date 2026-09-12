"""Verify tool: uses an LLM to check whether two claims support, contradict,
or are unrelated to each other. This is the 'contradiction checker' the
evaluation gate relies on to decide whether to adapt."""

import json
import os

import anthropic

_client = anthropic.Anthropic(api_key=os.environ.get("LLM_API_KEY"))
_MODEL = os.environ.get("LLM_MODEL", "claude-sonnet-4-6")

_SYSTEM = """You compare two research claims and classify their relationship.
Respond with ONLY a JSON object, no other text, in this exact shape:
{"relation": "supports" | "contradicts" | "unrelated", "confidence": 0.0-1.0, "reason": "one sentence"}
"""


def verify_claim(claim_a: dict, claim_b: dict) -> dict:
    """Return {relation, confidence, reason} describing how claim_a and
    claim_b relate to each other."""
    prompt = (
        f"Claim A: {claim_a['text']}\n"
        f"Claim B: {claim_b['text']}\n\n"
        "How do these two claims relate?"
    )

    response = _client.messages.create(
        model=_MODEL,
        max_tokens=200,
        system=_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = "".join(block.text for block in response.content if block.type == "text").strip()
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        # Fail safe: treat unparseable output as unrelated rather than crashing the run
        parsed = {"relation": "unrelated", "confidence": 0.0, "reason": "could not parse model output"}

    return parsed
