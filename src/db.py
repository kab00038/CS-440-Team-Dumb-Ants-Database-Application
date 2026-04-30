import os
import dotenv
import pymysql
import pymysql.cursors
import streamlit as st


def run_query(connection, sql, params=None, commit: bool = False):
    """Run a SQL statement.

    - For SELECT queries: returns a list of dict rows (may be empty).
    - For INSERT/UPDATE/DELETE: if `commit=True` commits the transaction and
      returns the cursor.lastrowid (or rowcount if lastrowid is not available).
    """
    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute(sql, params or ())
        if commit:
            connection.commit()
        if cursor.description:
            return cursor.fetchall()
        try:
            return cursor.lastrowid
        except Exception:
            return cursor.rowcount


def connect_to_database():
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
        try:
            st.error("Error connecting to the database:")
            st.write(e)
        except Exception:
            pass
        return None
