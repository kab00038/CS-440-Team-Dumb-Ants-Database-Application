import pandas as pd
import streamlit as st

def render_inventory(go_home_callback=None, logout_callback=None):
    top_left, _ = st.columns([1, 7])

    with top_left:
        if st.button("Home", width="stretch"):
            if go_home_callback is not None:
                go_home_callback()

        if st.session_state.get("user") is not None:
            if st.button("Logout", key="logout_btn"):
                if logout_callback is not None:
                    logout_callback()

    st.markdown("## Inventory")
    st.markdown(
        """
        <div class="panel">
            <p>
                A log of all devices in the system. Displays asset ID, IP address,
                online status, location ID, form factor, and assigned user when applicable.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

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

    st.dataframe(inventory_df, use_container_width=True)