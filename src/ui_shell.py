from pathlib import Path

import pandas as pd
import streamlit as st
from db import run_query
from inventory import render_inventory
from analytics import render_analytics
from crud import render_operations

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

    conn = st.session_state.get("conn")
    if conn:
        sql = """
            SELECT ma.asset_id, ma.hostname, ma.location_id, ma.ip_address, 'Server' AS device_type
            FROM managed_assets ma JOIN server s ON ma.asset_id = s.asset_id
            WHERE ma.online_status = 1
            UNION ALL
            SELECT ma.asset_id, ma.hostname, ma.location_id, ma.ip_address, 'Workstation' AS device_type
            FROM managed_assets ma JOIN workstation w ON ma.asset_id = w.asset_id
            WHERE ma.online_status = 1
            UNION ALL
            SELECT ma.asset_id, ma.hostname, ma.location_id, ma.ip_address, nd.device_type
            FROM managed_assets ma JOIN network_device nd ON ma.asset_id = nd.asset_id
            WHERE ma.online_status = 1
        """
        rows = run_query(conn, sql)
        df = pd.DataFrame(rows, columns=["asset_id", "hostname", "location_id", "ip_address", "device_type"])
        df.columns = ["Asset ID", "Hostname", "Location ID", "IP Address", "Device Type"]
        st.dataframe(df, width='stretch', hide_index=True)
    else:
        st.caption("Assets will appear here once logged in.")

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
