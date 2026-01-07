def ensure_admin(username: str, password: str):
    """
    Crea el admin si no existe.
    Si ya existe y es admin, actualiza la clave con la variable ADMIN_PASS.
    """
    if not username or not password:
        return

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, role FROM usuarios WHERE username = ?", (username,))
    row = cur.fetchone()

    if not row:
        cur.execute(
            "INSERT INTO usuarios (username, password, role) VALUES (?, ?, 'admin')",
            (username, password)
        )
        conn.commit()
    else:
        user_id, role = row[0], row[1]
        # Solo sincroniza si es admin (no toca usuarios normales)
        if role == "admin":
            cur.execute("UPDATE usuarios SET password = ? WHERE id = ?", (password, user_id))
            conn.commit()

    conn.close()
