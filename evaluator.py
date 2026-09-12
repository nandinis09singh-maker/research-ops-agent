"""Evaluation gate: checks accumulated claims for contradictions and weak
support before they're allowed into the final brief. This is what decides
whether the controller needs to adapt (search again) or can finalize."""

from itertools import combinations

from tools.verify_tool import verify_claim

MIN_CONFIDENCE = 0.5


class Evaluator:
    def check(self, state) -> list[dict]:
        """Return a list of gaps found in the current state.

        Each gap: {"type": "contradiction" | "weak_support",
                    "claims": [...], "detail": str}
        """
        gaps: list[dict] = []
        claims = state.claims

        # 1. Weak-support check: any claim below the confidence floor
        for c in claims:
            if c["confidence"] < MIN_CONFIDENCE and c["status"] == "unverified":
                gaps.append({
                    "type": "weak_support",
                    "claims": [c],
                    "detail": f"Claim has low confidence ({c['confidence']:.2f}): {c['text'][:80]}",
                })

        # 2. Pairwise contradiction check (only for claims not yet resolved,
        #    capped to avoid O(n^2) blowup on large claim sets)
        unresolved = [c for c in claims if c["status"] == "unverified"][:12]
        for a, b in combinations(unresolved, 2):
            if a["source_url"] == b["source_url"]:
                continue  # same source, skip
            result = verify_claim(a, b)
            if result["relation"] == "contradicts" and result["confidence"] >= MIN_CONFIDENCE:
                state.mark_status(a["id"], "contested")
                state.mark_status(b["id"], "contested")
                gaps.append({
                    "type": "contradiction",
                    "claims": [a, b],
                    "detail": result["reason"],
                })
            elif result["relation"] == "supports" and result["confidence"] >= MIN_CONFIDENCE:
                state.mark_status(a["id"], "supported")
                state.mark_status(b["id"], "supported")

        return gaps
