from datetime import date
from typing import Callable

import pandas as pd
import plotly.express as px
import streamlit as st

from db import connect_to_database, run_query


def render_analytics(go_home_callback: Callable[[], None], logout_callback: Callable[[], None]) -> None:
    # Analytics page: interactive charts sourced from maintenance_log table.
    top_left, _ = st.columns([1, 7])
    with top_left:
        if st.button("Home", width="stretch"):
            go_home_callback()
        if st.session_state.get("user") is not None:
            if st.button("Logout", key="logout_btn_analytics"):
                logout_callback()

    st.markdown("## Analytics")

    metric = st.selectbox("Metric", [
        "Average downtime",
        "Average parts cost",
        "Total parts cost",
        "Maintenance count by type",
    ])

    today = date.today()
    default_start = date(2024, 1, 1)
    default_end = today
    start_date, end_date = st.date_input("Date range", value=(default_start, default_end))

    asset_filter = st.text_input("Asset ID (optional)")

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

    connection = connect_to_database()
    if not connection:
        st.error("Unable to connect to the database")
        return

    try:
        rows = run_query(connection, sql, params)
    except Exception as e:
        st.error("Query failed")
        st.write(e)
        return

    df = pd.DataFrame(rows)
    if df.empty:
        st.info("No data for the selected range/filters.")
        return

    if "month" in df.columns:
        df["month"] = pd.to_datetime(df["month"])

    if metric != "Maintenance count by type":
        df = df.sort_values("month")
        fig = px.line(df, x="month", y="value", markers=True, labels={"value": metric, "month": "Month"})
        st.plotly_chart(fig, width="stretch")
    else:
        df = df.sort_values(["month", "category"])
        fig = px.bar(df, x="month", y="value", color="category", barmode="group", labels={"value": "Count", "month": "Month"})
        st.plotly_chart(fig, width="stretch")

    with st.expander("Result data"):
        st.dataframe(df)
        csv = df.to_csv(index=False)
        st.download_button("Download CSV", csv, file_name="analytics_export.csv", mime="text/csv")
