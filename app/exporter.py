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
                sheet = (t[:31] if t else "tabla")  # Excel máximo 31 chars

                # lee tabla completa
                try:
                    df = pd.read_sql_query(f'SELECT * FROM "{t}"', conn)
                except Exception:
                    df = pd.read_sql_query(f"SELECT * FROM {t}", conn)

                if df.empty:
                    pd.DataFrame({"info": [f"Tabla '{t}' está vacía"]}).to_excel(
                        writer, index=False, sheet_name=sheet
                    )
                else:
                    df.to_excel(writer, index=False, sheet_name=sheet)

        output.seek(0)
        return output.read()
    finally:
        conn.close()
