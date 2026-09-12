# System architecture

## Overview

The agent runs an observe → decide → act → evaluate → adapt loop. A research question enters the controller, which plans and dispatches tool calls, accumulates state, and passes results through an evaluation gate before either looping back to adapt or producing the final brief.

*(Insert the architecture diagram image here — export from your diagramming tool as `architecture.png` and reference it: `![architecture](architecture.png)`)*

## Components

| Component | Role |
|---|---|
| **Agent controller** (`agent/controller.py`) | Runs the plan → act → observe → replan loop. Decides which tool to call next based on current state. |
| **Search tool** (`tools/search_tool.py`) | Finds candidate papers/sources for a query. |
| **Fetch tool** (`tools/fetch_tool.py`) | Retrieves full text or abstract for a given source. |
| **Verify tool** (`tools/verify_tool.py`) | Compares two claims for contradiction/support. |
| **State & memory** (`memory/state_store.py`) | Tracks claims, sources, and confidence scores across the run — avoids redundant searches. |
| **Evaluation gate** (`evaluation/evaluator.py`) | Checks each claim's evidentiary support before it's allowed into the final brief. |
| **Human steering** | User can redirect scope mid-run (e.g. narrow domain, exclude a source type). |
| **Failure handling** | On a failed tool call (unavailable source, empty search), the controller retries or falls back to an alternate source rather than stalling. |

## Adaptation logic

When the evaluation gate flags a claim as contested (contradicted by another source) or under-supported (single weak source), the controller does not proceed to finalize. Instead it:
1. Formulates a targeted follow-up search specific to the gap
2. Re-runs the relevant tool calls
3. Re-evaluates before retrying finalization

This is capped by `MAX_ADAPT_RETRIES` (see `.env.example`) to guarantee termination.

## Failure handling

If a tool call fails (timeout, 404, empty result):
1. The controller retries once
2. On repeat failure, it selects an alternate source/tool if one exists
3. If no alternate exists, the gap is explicitly logged in the final brief rather than silently dropped
