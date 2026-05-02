"""Active Devices page module for displaying online managed assets."""

import pandas as pd
import streamlit as st
from db import run_query


def render_active_devices() -> None:
    """Display a list of all active devices from the database.
    
    Queries the database for devices with online_status = 1 across
    servers, workstations, and network devices.
    """
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
        st.dataframe(df, width='stretch', hide_index=True, height=520)
    else:
        st.caption("Assets will appear here once logged in.")
