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
import auth
from db import run_query
from ui_shell import render_shell
from argon2 import PasswordHasher, exceptions
from auth import hash_password, verify_password

def create_user(conn, username: str, password: str, is_admin: bool=False):
    pw_hash = auth.hash_password(password)
    sql = "INSERT INTO users (username, password_hash, is_admin) VALUES (%s, %s, %s)"
    try:
        # run_query will return the lastrowid for non-SELECT statements when commit=True
        new_id = run_query(conn, sql, (username, pw_hash, is_admin), commit=True)
        return new_id
    except Exception as e:
        st.error("Error creating user")
        st.write(e)
        return None

def get_user_by_username(conn, username: str):
    rows = run_query(
        conn,
        "SELECT id, username, password_hash, is_admin FROM users WHERE username = %s",
        (username,),
    )
    return rows[0] if rows else None
    
def authenticate_user(conn, username: str, password: str):
    row = get_user_by_username(conn, username)
    if not row:
        return None
    if auth.verify_password(row["password_hash"], password):
        return {"id": row["id"], "username": row["username"], "is_admin": bool(row["is_admin"])}
    return None



def connect_to_database():
    # Read .env values and open a secure MySQL connection for later page queries.
    dotenv.load_dotenv()
    try:
        connection = pymysql.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            port=int(os.getenv("DB_PORT", 3306)),
            database=os.getenv("DB_NAME", "assetdatabase"),
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
if "user" not in st.session_state:
    st.session_state["user"] = None

if st.session_state["user"] is None:
    # Render a centered floating login modal instead of the sidebar form.
    st.markdown('<div class="login-overlay">', unsafe_allow_html=True)
    with st.form("login_form"):
        st.markdown("<h2 style='margin:0 0 0.5rem 0;color:#d7ffe5;'>Log in</h2>", unsafe_allow_html=True)
        u = st.text_input("Username", key="login_username")
        p = st.text_input("Password", type="password", key="login_password")
        submit = st.form_submit_button("Log in")
    st.markdown('</div>', unsafe_allow_html=True)

    if submit:
        conn = connect_to_database()
        if conn:
            user = authenticate_user(conn, u, p)
            if user:
                st.session_state["user"] = user
                st.session_state["conn"] = conn
                st.success(f"Welcome {user['username']}")
                st.rerun()
            else:
                st.error("Invalid credentials")
        else:
            st.error("DB connection failed")
else:
    render_shell()

