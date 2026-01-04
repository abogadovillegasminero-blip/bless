from io import BytesIO
import pandas as pd

from .db import get_connection, is_postgres


def _list_tables(conn):
    cur = conn.cursor()
    if is_postgres():
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        return [r[0] for r in cur.fetchall()]
    else:
        cur.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type='table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)
        return [r[0] for r in cur.fetchall()]


def export_all_tables_to_excel_bytes() -> bytes:
    conn = get_connection()
    try:
        tables = _list_tables(conn)
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            for t in tables:
                try:
                    df = pd.read_sql_query(f'SELECT * FROM "{t}"', conn)
                except Exception:
                    # por si el driver no acepta comillas dobles
                    df = pd.read_sql_query(f"SELECT * FROM {t}", conn)

                sheet = (t[:31] if t else "tabla")  # Excel limita 31 chars
                if df.empty:
                    # hoja vacía pero creada
                    pd.DataFrame({"info": [f"Tabla '{t}' está vacía"]}).to_excel(writer, index=False, sheet_name=sheet)
                else:
                    df.to_excel(writer, index=False, sheet_name=sheet)

        output.seek(0)
        return output.read()
    finally:
        conn.close()
