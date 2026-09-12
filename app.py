"""Streamlit UI for the Research Ops Agent.

Run locally with: streamlit run app.py
Deploy for free on Streamlit Community Cloud by pointing it at this file
and setting LLM_API_KEY / TAVILY_API_KEY as secrets in the dashboard.
"""

import streamlit as st

from agent.controller import ResearchOpsAgent

st.set_page_config(page_title="Research Ops Agent", page_icon="🔎", layout="centered")

st.title("Research Ops Agent")
st.caption("Goal → decide → act → evaluate → adapt. Built for Tech Zephyr 4.0.")

question = st.text_area(
    "Research question",
    placeholder="e.g. What are current approaches to reducing hallucination in RAG systems, and what's still unsolved?",
    height=80,
)

run_button = st.button("Run agent", type="primary", disabled=not question.strip())

if run_button:
    log_box = st.empty()
    log_lines: list[str] = []

    with st.spinner("Running the agent loop — this can take a minute..."):
        agent = ResearchOpsAgent()

        # Monkey-patch state.note so the log streams live to the UI
        original_note = agent.state.note

        def streaming_note(message: str) -> None:
            original_note(message)
            log_lines.append(message)
            log_box.code("\n".join(log_lines))

        agent.state.note = streaming_note

        result = agent.run(question.strip())

    st.subheader("Final brief")
    st.markdown(result["brief"])

    with st.expander(f"Claims collected ({len(result['claims'])})"):
        for c in result["claims"]:
            st.markdown(f"- **[{c['status']}]** {c['text']}  \n  _source: {c['source_url']}_")

    with st.expander(f"Sources ({len(result['sources'])})"):
        for s in result["sources"]:
            st.markdown(f"- [{s['title'] or s['url']}]({s['url']})")

    with st.expander("Run stats"):
        st.json(result["stats"])
