import pandas as pd
import streamlit as st


def render_inventory():
    conn = st.session_state.get("conn")

    if conn is None:
        st.error("No active database connection found.")
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

    inventory_df = pd.read_sql(query, conn)

    st.title("Inventory")

    st.write(
        "A log of all devices in the system. Displays asset ID, IP address, "
        "online status, location ID, form factor, and assigned user when applicable."
    )

    st.dataframe(inventory_df, use_container_width=True)