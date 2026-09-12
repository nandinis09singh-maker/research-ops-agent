"""Search tool: finds candidate sources for a query using Tavily's search API.

Requires TAVILY_API_KEY in the environment. Get a free key at https://tavily.com
(Swap this out for Serper, Bing, or Semantic Scholar if you prefer — the
return shape is all that matters to the rest of the agent.)
"""

import os

import requests

TAVILY_URL = "https://api.tavily.com/search"


class SearchError(Exception):
    """Raised when the search API call fails or returns nothing usable."""


def search(query: str, max_results: int = 5) -> list[dict]:
    """Return a list of {title, url, snippet} for the given query.

    Raises SearchError on failure so the controller can decide how to
    recover (retry, fall back, or log the gap) instead of crashing.
    """
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        raise SearchError("TAVILY_API_KEY is not set")

    try:
        resp = requests.post(
            TAVILY_URL,
            json={
                "api_key": api_key,
                "query": query,
                "max_results": max_results,
                "search_depth": "basic",
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        raise SearchError(f"search request failed: {exc}") from exc

    results = data.get("results", [])
    if not results:
        raise SearchError(f"no results for query: {query!r}")

    return [
        {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "snippet": r.get("content", "")[:500],
        }
        for r in results
    ]
