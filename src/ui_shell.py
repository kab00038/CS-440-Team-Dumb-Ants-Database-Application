from pathlib import Path

import pandas as pd
import streamlit as st

# UI shell module for the Streamlit proof-of-concept interface.
#
# This file handles lightweight page routing using session state, applies the
# shared stylesheet, and renders placeholder content for each top-level page.


def _load_stylesheet() -> str:
    # Keep styles in a separate CSS file and inject them at runtime.
    css_path = Path(__file__).with_name("styles.css")
    return css_path.read_text(encoding="utf-8")


def _go_to(page_name: str) -> None:
    # Save the selected page and rerun so the new view is drawn immediately.
    st.session_state["current_page"] = page_name
    st.rerun()


def _render_home() -> None:
    # Landing page with project context and navigation buttons.
    st.markdown(
        """
        <div class="hero">
            <h1>🖥️ IT Asset Management</h1>
            <p>
                UI shell for IT asset management application. This is an interface built with Streamlit,  designed layout and styling for inventory management, analytics, and operations workflows.
            </p>
            <span class="chip">User Interface Only</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        if st.button("Inventory", width='stretch'):
            _go_to("inventory")
    with c2:
        if st.button("Analytics", width='stretch'):
            _go_to("analytics")
    with c3:
        if st.button("Operations", width='stretch'):
            _go_to("operations")

    st.markdown("### Active Devices")
    st.caption("Assets will go here once live data querying is enabled.")

    empty_table = pd.DataFrame(
        columns=["Asset ID", "Hostname", "Device Type", "Form Factor"]
        #Device type is network vs server vs workstation. Form factor is laptop vs desktop vs rackmount, etc.
    )
    st.dataframe(empty_table, width='stretch', hide_index=True)

    st.divider()
    st.caption(
        "Status: Styled UI is active. Database connection helpers are loaded; no queries run on page load."
    )


def _render_subpage(title: str, subtitle: str) -> None:
    # Shared layout for placeholder subpages until feature-specific UI is added.
    top_left, _ = st.columns([1, 7])
    with top_left:
        if st.button("Home", width='stretch'):
            _go_to("home")

    st.markdown(f"## {title}")
    st.markdown(f"<div class=\"panel\"><p>{subtitle}</p></div>", unsafe_allow_html=True)
    st.info("No database queries are enabled on this page yet.")


def render_shell() -> None:
    # Main router for the shell: apply CSS, initialize page state, render view.
    st.markdown(f"<style>{_load_stylesheet()}</style>", unsafe_allow_html=True)

    # Default to home on first load.
    if "current_page" not in st.session_state:
        st.session_state["current_page"] = "home"

    page = st.session_state["current_page"]

    if page == "inventory":
        _render_subpage("Inventory", "Inventory page placeholder. Device lists and filters will be added here.")
    elif page == "analytics":
        _render_subpage("Analytics", "Analytics page placeholder. Charts and comparisons will be added here.")
    elif page == "operations":
        _render_subpage("Operations", "Operations page placeholder. Create/update/delete workflows will be added here.")
    else:
        _render_home()
