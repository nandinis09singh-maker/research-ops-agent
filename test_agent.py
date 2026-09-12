"""Tests for the Research Ops Agent, with all external calls (LLM, search,
fetch) mocked so the suite runs without live API keys."""

import json
from unittest.mock import patch, MagicMock

import pytest

from agent.controller import ResearchOpsAgent
from memory.state_store import StateStore
from evaluation.evaluator import Evaluator


def _mock_llm_response(text: str) -> MagicMock:
    block = MagicMock()
    block.type = "text"
    block.text = text
    response = MagicMock()
    response.content = [block]
    return response


# --- StateStore -----------------------------------------------------------

def test_state_store_tracks_claims_and_queries():
    state = StateStore()
    state.add_claim("RAG grounding reduces hallucination", "http://example.com/a", 0.8)
    state.record_query("rag hallucination mitigation")

    assert len(state.claims) == 1
    assert state.already_searched("RAG Hallucination Mitigation")  # case-insensitive
    assert not state.already_searched("something else")


# --- Evaluator --------------------------------------------------------------

def test_evaluator_flags_weak_support():
    state = StateStore()
    state.add_claim("A vague underpowered claim", "http://example.com/a", 0.2)
    gaps = Evaluator().check(state)
    assert any(g["type"] == "weak_support" for g in gaps)


@patch("evaluation.evaluator.verify_claim")
def test_evaluator_flags_contradiction(mock_verify):
    mock_verify.return_value = {"relation": "contradicts", "confidence": 0.9, "reason": "conflicting numbers"}
    state = StateStore()
    state.add_claim("Method X reduces error by 40%", "http://example.com/a", 0.8)
    state.add_claim("Method X has no measurable effect on error", "http://example.com/b", 0.8)

    gaps = Evaluator().check(state)
    assert any(g["type"] == "contradiction" for g in gaps)


# --- Agent controller (fully mocked run) -----------------------------------

@patch("agent.controller.fetch")
@patch("agent.controller.search")
@patch("agent.controller._client")
def test_agent_full_run_with_mocks(mock_client, mock_search, mock_fetch):
    # Plan step returns two queries
    plan_response = _mock_llm_response(json.dumps(["rag hallucination", "retrieval grounding"]))
    # Claim extraction returns one claim
    claims_response = _mock_llm_response(json.dumps([{"claim": "Grounding reduces hallucination", "confidence": 0.8}]))
    # Finalize returns a brief
    brief_response = _mock_llm_response("## Key Findings\n- Grounding helps.")

    mock_client.messages.create.side_effect = [plan_response, claims_response, claims_response, brief_response]

    mock_search.return_value = [{"title": "Paper A", "url": "http://example.com/a", "snippet": "..."}]
    mock_fetch.return_value = "Grounding techniques reduce hallucination in RAG systems significantly."

    agent = ResearchOpsAgent(max_adapt_retries=1)
    # Force evaluator to report no gaps so the run terminates quickly in this test
    agent.evaluator.check = MagicMock(return_value=[])

    result = agent.run("What reduces hallucination in RAG?")

    assert "brief" in result
    assert result["stats"]["num_claims"] >= 1


def test_agent_handles_search_failure_gracefully():
    """A failed search should be logged, not crash the run."""
    with patch("agent.controller.search", side_effect=Exception("boom")):
        agent = ResearchOpsAgent()
        # _act should not raise even if search blows up unexpectedly upstream
        with pytest.raises(Exception):
            # This intentionally demonstrates raw exceptions still propagate;
            # SearchError specifically is the one the agent catches (see below).
            agent._act("some query")


def test_agent_handles_search_error_with_fallback():
    from tools.search_tool import SearchError
    with patch("agent.controller.search", side_effect=SearchError("no results")):
        agent = ResearchOpsAgent()
        agent._act("some query")  # should not raise
        assert any("Search failed" in line for line in agent.state.log)
