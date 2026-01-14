    # Campos extra (si ya existe la tabla, estos ALTER pueden fallar; por eso try/except)
    for alter in [
        "ALTER TABLE clientes ADD COLUMN cuota_valor INTEGER DEFAULT 0",
        "ALTER TABLE clientes ADD COLUMN saldo_actual INTEGER DEFAULT 0",
        "ALTER TABLE clientes ADD COLUMN ultimo_cobro TEXT",
    ]:
        try:
            execute(alter)
        except Exception:
            pass

    # Tablas de rutas
    execute("""
    CREATE TABLE IF NOT EXISTS rutas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cobrador_username TEXT NOT NULL,
        fecha TEXT NOT NULL, -- YYYY-MM-DD (Colombia)
        creado TEXT DEFAULT (datetime('now'))
    )
    """)

    execute("""
    CREATE TABLE IF NOT EXISTS ruta_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ruta_id INTEGER NOT NULL,
        cliente_id INTEGER NOT NULL,
        orden INTEGER NOT NULL DEFAULT 1,
        valor_cobrar INTEGER NOT NULL DEFAULT 0,
        saldo_cliente INTEGER NOT NULL DEFAULT 0,
        estado TEXT NOT NULL DEFAULT 'pendiente',
        FOREIGN KEY(ruta_id) REFERENCES rutas(id) ON DELETE CASCADE,
        FOREIGN KEY(cliente_id) REFERENCES clientes(id) ON DELETE CASCADE
    )
    """)
