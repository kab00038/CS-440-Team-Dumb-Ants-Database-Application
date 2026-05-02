from pathlib import Path

import streamlit as st

from db import run_query
from inventory import render_inventory
from analytics import render_analytics
from crud import render_operations
from active import render_active_devices

# UI shell module for the Streamlit proof-of-concept interface.
#
# This file handles lightweight page routing using session state, applies the
# shared stylesheet, and renders placeholder content for each top-level page.

def _logout() -> None:
    st.session_state["user"] = None
    st.session_state["current_page"] = "home"
    st.rerun()

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
    header_col, _ = st.columns([1, 7])
    with header_col:
        if st.session_state.get("user") is not None:
            if st.button("Logout", key="logout_home_btn"):
                _logout()
    st.markdown(
        """
        <div class="hero">
            <h1>🖥️ IT Asset Management</h1>
            <p>
                Database-backed IT asset management application built with Streamlit, providing live inventory, analytics, and operations workflows.
            </p>
            <span class="chip">Full Functionality Implemented</span>
            <span class="chip">Live Data Connected</span>
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

    render_active_devices()

    st.divider()
    st.caption(
        "Status: Active. Displaying online assets from database. Analytics, Operations, and Inventory pages available."
    )


def _render_subpage(title: str, subtitle: str) -> None:
    # Shared layout for placeholder subpages until feature-specific UI is added.
    top_left, _ = st.columns([1, 7])
    with top_left:
        if st.button("Home", width='stretch'):
            _go_to("home")
        if st.session_state.get("user") is not None:
            if st.button("Logout", key="logout_btn"):
                _logout()

    st.markdown(f"## {title}")
    st.markdown(f"<div class=\"panel\"><p>{subtitle}</p></div>", unsafe_allow_html=True)
    st.info("No database queries are enabled on this page yet.")

def _render_inventory() -> None:
    render_inventory(
        go_home_callback=lambda: _go_to("home"),
        logout_callback=_logout,
    )


def _render_analytics() -> None:
    render_analytics(
        go_home_callback=lambda: _go_to("home"),
        logout_callback=_logout,
    )


def _render_operations() -> None:
    render_operations(
        go_home_callback=lambda: _go_to("home"),
        logout_callback=_logout,
    )


def render_shell() -> None:
    # Main router for the shell: apply CSS, initialize page state, render view.
    st.markdown(f"<style>{_load_stylesheet()}</style>", unsafe_allow_html=True)

    # Default to home on first load.
    if "current_page" not in st.session_state:
        st.session_state["current_page"] = "home"

    page = st.session_state["current_page"]

    if page == "inventory":
        _render_inventory()
    elif page == "analytics":
        _render_analytics()
    elif page == "operations":
        _render_operations()
    else:
        _render_home()
