"""Agent controller: runs the plan -> act -> observe -> evaluate -> adapt loop.

This is the core of the "agentic" behavior: it decides its own search
strategy, extracts claims from sources, evaluates them for contradictions
and weak support, and — if problems are found — launches targeted
follow-up actions instead of finalizing blindly. Failed tool calls trigger
fallback logic rather than crashing the run.
"""

import argparse
import json
import os

import anthropic
from dotenv import load_dotenv

from memory.state_store import StateStore
from evaluation.evaluator import Evaluator
from tools.search_tool import search, SearchError
from tools.fetch_tool import fetch, FetchError

load_dotenv()

_MODEL = os.environ.get("LLM_MODEL", "claude-sonnet-4-6")
_client = anthropic.Anthropic(api_key=os.environ.get("LLM_API_KEY"))


class ResearchOpsAgent:
    def __init__(self, max_adapt_retries: int = 2, sources_per_query: int = 3):
        self.state = StateStore()
        self.evaluator = Evaluator()
        self.max_adapt_retries = max_adapt_retries
        self.sources_per_query = sources_per_query

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self, question: str) -> dict:
        self.state.note(f"Goal received: {question}")

        plan = self._plan(question)
        self.state.note(f"Planned {len(plan)} initial searches: {plan}")

        for query in plan:
            self._act(query)

        for attempt in range(1, self.max_adapt_retries + 1):
            gaps = self.evaluator.check(self.state)
            if not gaps:
                self.state.note("Evaluation gate: no unresolved gaps, finalizing.")
                break
            self.state.note(f"Evaluation gate found {len(gaps)} gap(s) on attempt {attempt}, adapting.")
            self._adapt(gaps)
        else:
            self.state.note("Max adapt retries reached; finalizing with remaining gaps noted.")

        return self._finalize(question)

    # ------------------------------------------------------------------
    # Plan: decide the initial search strategy
    # ------------------------------------------------------------------

    def _plan(self, question: str) -> list[str]:
        prompt = (
            f"Research question: {question}\n\n"
            "Produce 3-4 distinct web search queries that together would surface "
            "the key evidence needed to answer this question thoroughly. "
            "Respond with ONLY a JSON array of strings, no other text."
        )
        response = _client.messages.create(
            model=_MODEL,
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = self._extract_text(response)
        try:
            queries = json.loads(raw)
            assert isinstance(queries, list)
            return [str(q) for q in queries][:4]
        except (json.JSONDecodeError, AssertionError):
            # Fallback: use the raw question as a single query rather than failing the run
            return [question]

    # ------------------------------------------------------------------
    # Act: execute one search query end-to-end (search -> fetch -> extract claims)
    # ------------------------------------------------------------------

    def _act(self, query: str) -> None:
        if self.state.already_searched(query):
            return
        self.state.record_query(query)

        try:
            results = search(query, max_results=self.sources_per_query)
        except SearchError as exc:
            self.state.note(f"Search failed for {query!r}: {exc}. Skipping this query.")
            return

        for result in results:
            self.state.add_source(result["url"], result["title"], result["snippet"])
            try:
                text = fetch(result["url"])
            except FetchError as exc:
                # Failure + fallback: log it and fall back to the search snippet
                # instead of stalling the run.
                self.state.note(f"Fetch failed for {result['url']}: {exc}. Falling back to snippet.")
                text = result["snippet"]
                if not text:
                    continue

            claims = self._extract_claims(text, source_url=result["url"])
            for claim_text, confidence in claims:
                self.state.add_claim(claim_text, result["url"], confidence)

    def _extract_claims(self, text: str, source_url: str) -> list[tuple[str, float]]:
        """Use the LLM to pull out discrete factual claims from source text."""
        prompt = (
            "Extract up to 3 discrete, specific factual claims from this text "
            "that are directly relevant to a research summary. "
            'Respond with ONLY a JSON array like [{"claim": "...", "confidence": 0.7}], '
            "confidence reflecting how clearly the text supports the claim (0-1).\n\n"
            f"Text:\n{text[:3000]}"
        )
        response = _client.messages.create(
            model=_MODEL,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = self._extract_text(response)
        try:
            items = json.loads(raw)
            return [(item["claim"], float(item.get("confidence", 0.6))) for item in items]
        except (json.JSONDecodeError, KeyError, TypeError):
            return []

    # ------------------------------------------------------------------
    # Adapt: given evaluation gaps, launch targeted follow-up searches
    # ------------------------------------------------------------------

    def _adapt(self, gaps: list[dict]) -> None:
        for gap in gaps:
            claim_texts = " / ".join(c["text"] for c in gap["claims"])
            prompt = (
                f"A research agent found this issue: {gap['type']} — {gap['detail']}\n"
                f"Related claim(s): {claim_texts}\n\n"
                "Propose ONE specific follow-up web search query that would help "
                "resolve this issue. Respond with ONLY the query text, nothing else."
            )
            response = _client.messages.create(
                model=_MODEL,
                max_tokens=60,
                messages=[{"role": "user", "content": prompt}],
            )
            follow_up_query = self._extract_text(response).strip().strip('"')
            self.state.note(f"Adapting: launching follow-up search — {follow_up_query!r}")
            self._act(follow_up_query)

    # ------------------------------------------------------------------
    # Finalize: synthesize the brief from accumulated state
    # ------------------------------------------------------------------

    def _finalize(self, question: str) -> dict:
        claims_summary = "\n".join(
            f"- [{c['status']}] {c['text']} (source: {c['source_url']})" for c in self.state.claims
        )
        prompt = (
            f"Research question: {question}\n\n"
            f"Accumulated claims:\n{claims_summary or '(none found)'}\n\n"
            "Write a structured research brief with these sections: "
            "Key Findings, Open Contradictions, Evidence Gaps, Suggested Next Direction. "
            "Be concise and cite which claims support each point."
        )
        response = _client.messages.create(
            model=_MODEL,
            max_tokens=1200,
            messages=[{"role": "user", "content": prompt}],
        )
        brief_text = self._extract_text(response)

        return {
            "question": question,
            "brief": brief_text,
            "claims": self.state.claims,
            "sources": list(self.state.sources.values()),
            "run_log": self.state.log,
            "stats": self.state.summary(),
        }

    @staticmethod
    def _extract_text(response) -> str:
        raw = "".join(block.text for block in response.content if block.type == "text").strip()
        return raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--question", required=True, help="Research question")
    args = parser.parse_args()

    agent = ResearchOpsAgent()
    result = agent.run(args.question)

    print("\n=== RUN LOG ===")
    for line in result["run_log"]:
        print("-", line)

    print("\n=== BRIEF ===")
    print(result["brief"])

    print("\n=== STATS ===")
    print(result["stats"])


if __name__ == "__main__":
    main()
