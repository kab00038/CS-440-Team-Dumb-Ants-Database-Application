# Control + C in terminal to close the Streamlit app and return to the command line.
# Streamlit entrypoint for the IT Asset Management app shell.
#
# This file is used to:
# - provide lightweight database helpers,
# - load connection settings from environment variables, and
# - launch the styled UI shell.

import os
import dotenv
import pymysql
import streamlit as st
from ui_shell import render_shell


def run_query(connection, sql, params=None):
    # Run a SQL query and return rows as dictionaries for easy UI rendering.
    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute(sql, params or ())
        return cursor.fetchall()


def connect_to_database():
    # Read .env values and open a secure MySQL connection for later page queries.
    dotenv.load_dotenv()
    try:
        connection = pymysql.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            port=int(os.getenv("DB_PORT", 3306)),
            database=os.getenv("DB_NAME", "defaultdb"),
            ssl={"ca": "ca.pem"},
        )
        return connection
    except Exception as e:
        st.error("Error connecting to the database:")
        st.write(e)
        return None


    # Global Streamlit page settings must be configured before rendering content.
st.set_page_config(page_title="IT Asset Management", layout="wide")

    # Render the temporary multi-page shell (home/inventory/analytics/operations).
render_shell()

