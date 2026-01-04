@router.post("/pagos/eliminar")
def eliminar_pago(
    request: Request,
    row_id: int = Form(...),
):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    pagos_df = _load_pagos()

    # Seguridad: validar rango
    if row_id < 0 or row_id >= len(pagos_df):
        return RedirectResponse("/pagos", status_code=303)

    # Eliminar la fila exacta
    pagos_df = pagos_df.drop(index=row_id).reset_index(drop=True)
    pagos_df.to_excel(PAGOS, index=False)

    return RedirectResponse("/pagos", status_code=303)
