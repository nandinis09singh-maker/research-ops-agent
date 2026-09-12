"""State store: tracks claims, sources, and search history across a run."""

import uuid


class StateStore:
    def __init__(self):
        self.claims: list[dict] = []
        self.sources: dict[str, dict] = {}   # url -> {title, url, snippet}
        self._searched_queries: set[str] = set()
        self.log: list[str] = []             # human-readable trace for the demo/debug

    # --- sources -----------------------------------------------------

    def add_source(self, url: str, title: str = "", snippet: str = "") -> None:
        if url not in self.sources:
            self.sources[url] = {"url": url, "title": title, "snippet": snippet}

    # --- claims --------------------------------------------------------

    def add_claim(self, text: str, source_url: str, confidence: float = 0.6) -> dict:
        """Record a new claim tied to a source. Returns the stored claim."""
        claim = {
            "id": str(uuid.uuid4())[:8],
            "text": text,
            "source_url": source_url,
            "confidence": confidence,
            "status": "unverified",   # unverified | supported | contested
        }
        self.claims.append(claim)
        return claim

    def claims_for(self, topic_hint: str | None = None) -> list[dict]:
        """Return all claims, optionally filtered by a naive substring match."""
        if not topic_hint:
            return list(self.claims)
        hint = topic_hint.lower()
        return [c for c in self.claims if hint in c["text"].lower()]

    def mark_status(self, claim_id: str, status: str) -> None:
        for c in self.claims:
            if c["id"] == claim_id:
                c["status"] = status
                return

    # --- search bookkeeping ---------------------------------------------

    def record_query(self, query: str) -> None:
        self._searched_queries.add(query.strip().lower())

    def already_searched(self, query: str) -> bool:
        return query.strip().lower() in self._searched_queries

    # --- tracing ---------------------------------------------------------

    def note(self, message: str) -> None:
        """Append a human-readable step to the run log (useful for the demo)."""
        self.log.append(message)

    def summary(self) -> dict:
        return {
            "num_claims": len(self.claims),
            "num_sources": len(self.sources),
            "num_searches": len(self._searched_queries),
        }
