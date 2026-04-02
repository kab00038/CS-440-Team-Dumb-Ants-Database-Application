import pymysql
import dotenv
import os
import streamlit as st

def run_query(connection, sql, params=None):
    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute(sql, params or ())
        return cursor.fetchall()

st.title("IT Asset Management System")

def connect_to_database():
    dotenv.load_dotenv()
    try:
        connection = pymysql.connect(
            host = os.getenv("DB_HOST"),
            user = os.getenv("DB_USER"),
            password = os.getenv("DB_PASS"),
            port = int(os.getenv("DB_PORT")),
            database="defaultdb",
            ssl = {'ca': 'ca.pem'}
    )
        st.success("Successfully connected to the database.")
    except Exception as e:
        st.error("Error connecting to the database:")
        st.write(e)
        return None

    return connection

