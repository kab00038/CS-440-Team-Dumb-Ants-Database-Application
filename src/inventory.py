import pandas as pd
import streamlit as st

from db import connect_to_database, run_query

def render_inventory(go_home_callback=None, logout_callback=None):
    top_left, _, top_right = st.columns([1, 6, 1])

    with top_left:
        if st.button("Home", width="stretch"):
            if go_home_callback is not None:
                go_home_callback()

        if st.session_state.get("user") is not None:
            if st.button("Logout", key="logout_btn"):
                if logout_callback is not None:
                    logout_callback()

    with top_right:
        if st.button("Refresh", width="stretch"):
            st.rerun()

    st.markdown("## Inventory")
    st.caption(
        "A log of all devices in the system. Displays asset ID, IP address, online status, "
        "location ID, form factor, and assigned user when applicable."
    )

    conn = connect_to_database()

    if conn is None:
        st.error("Unable to connect to the database")
        return

    query = """
        SELECT
            ma.asset_id,
            ma.ip_address,
            ma.online_status,
            ma.location_id,
            w.form_factor,
            w.assigned_user
        FROM managed_assets ma
        LEFT JOIN workstation w
            ON ma.asset_id = w.asset_id
        ORDER BY ma.asset_id;
    """

    try:
        rows = run_query(conn, query)
        inventory_df = pd.DataFrame(
            rows,
            columns=[
                "asset_id",
                "ip_address",
                "online_status",
                "location_id",
                "form_factor",
                "assigned_user",
            ],
        )

        st.dataframe(inventory_df, width="stretch", height=520)
    finally:
        try:
            conn.close()
        except Exception:
            pass
