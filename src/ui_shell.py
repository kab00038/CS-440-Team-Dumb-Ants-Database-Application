from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from datetime import date
from db import connect_to_database, run_query

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
        if st.session_state.get("user") is not None:
            if st.button("Logout", key="logout_btn"):
                _logout()

    st.markdown(f"## {title}")
    st.markdown(f"<div class=\"panel\"><p>{subtitle}</p></div>", unsafe_allow_html=True)
    st.info("No database queries are enabled on this page yet.")


def _render_analytics() -> None:
    # Analytics page: interactive charts sourced from maintenance_log table.
    top_left, _ = st.columns([1, 7])
    with top_left:
        if st.button("Home", width='stretch'):
            _go_to("home")
        if st.session_state.get("user") is not None:
            if st.button("Logout", key="logout_btn_analytics"):
                _logout()

    st.markdown("## Analytics")

    # Controls
    metric = st.selectbox("Metric", [
        "Average downtime",
        "Average parts cost",
        "Total parts cost",
        "Maintenance count by type",
    ])

    today = date.today()
    default_start = date(today.year, 1, 1)
    default_end = today
    start_date, end_date = st.date_input("Date range", value=(default_start, default_end))

    asset_filter = st.text_input("Asset ID (optional)")

    # Build SQL and params
    params = (start_date.isoformat(), end_date.isoformat())

    if metric == "Average downtime":
        sql = (
            "SELECT DATE_FORMAT(maintenance_date, '%%Y-%%m-01') AS month,"
            " AVG(downtime_minutes) AS value"
            " FROM maintenance_log"
            " WHERE maintenance_date BETWEEN %s AND %s"
        )
    elif metric == "Average parts cost":
        sql = (
            "SELECT DATE_FORMAT(maintenance_date, '%%Y-%%m-01') AS month,"
            " AVG(parts_cost) AS value"
            " FROM maintenance_log"
            " WHERE maintenance_date BETWEEN %s AND %s"
        )
    elif metric == "Total parts cost":
        sql = (
            "SELECT DATE_FORMAT(maintenance_date, '%%Y-%%m-01') AS month,"
            " SUM(parts_cost) AS value"
            " FROM maintenance_log"
            " WHERE maintenance_date BETWEEN %s AND %s"
        )
    else:  # Maintenance count by type
        sql = (
            "SELECT DATE_FORMAT(maintenance_date, '%%Y-%%m-01') AS month,"
            " maintenance_type AS category,"
            " COUNT(*) AS value"
            " FROM maintenance_log"
            " WHERE maintenance_date BETWEEN %s AND %s"
        )

    if asset_filter:
        sql += " AND asset_id = %s"
        params = (start_date.isoformat(), end_date.isoformat(), asset_filter)

    if metric != "Maintenance count by type":
        sql += " GROUP BY month ORDER BY month;"
    else:
        sql += " GROUP BY month, maintenance_type ORDER BY month, maintenance_type;"

    conn = connect_to_database()
    if not conn:
        st.error("Unable to connect to the database")
        return

    try:
        rows = run_query(conn, sql, params)
    except Exception as e:
        st.error("Query failed")
        st.write(e)
        return

    df = pd.DataFrame(rows)
    if df.empty:
        st.info("No data for the selected range/filters.")
        return

    # Prepare month column
    if 'month' in df.columns:
        df['month'] = pd.to_datetime(df['month'])

    # Plot
    if metric != "Maintenance count by type":
        df = df.sort_values('month')
        fig = px.line(df, x='month', y='value', markers=True, labels={'value': metric, 'month': 'Month'})
        st.plotly_chart(fig, use_container_width=True)
    else:
        df = df.sort_values(['month', 'category'])
        fig = px.bar(df, x='month', y='value', color='category', barmode='group', labels={'value': 'Count', 'month': 'Month'})
        st.plotly_chart(fig, use_container_width=True)

    # Data table + download
    with st.expander("Result data"):
        st.dataframe(df)
        csv = df.to_csv(index=False)
        st.download_button("Download CSV", csv, file_name="analytics_export.csv", mime="text/csv")


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
        _render_analytics()
    elif page == "operations":
        _render_subpage("Operations", "Operations page placeholder. Create/update/delete workflows will be added here.")
    else:
        _render_home()
