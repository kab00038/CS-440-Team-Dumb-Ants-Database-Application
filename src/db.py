import pymysql
import pymysql.cursors


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
