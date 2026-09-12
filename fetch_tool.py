"""Fetch tool: retrieves and extracts readable text from a URL.

Designed to fail loudly with a specific exception (not silently return
empty text) so the controller can trigger its fallback logic — this is
the piece your demo video's "failure/adaptation" moment will hook into.
"""

import requests
import trafilatura


class FetchError(Exception):
    """Raised when a page can't be retrieved or has no extractable text."""


def fetch(url: str, timeout: int = 10, max_chars: int = 6000) -> str:
    """Return extracted, readable text content from the given URL.

    Raises FetchError on timeout, non-200 status, paywalls, or pages with
    no extractable text (common on JS-heavy or blocked pages).
    """
    try:
        resp = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0 (ResearchOpsAgent/1.0)"},
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise FetchError(f"could not fetch {url}: {exc}") from exc

    text = trafilatura.extract(resp.text)
    if not text or len(text.strip()) < 100:
        raise FetchError(f"no usable text extracted from {url} (likely paywalled or JS-rendered)")

    return text[:max_chars]

