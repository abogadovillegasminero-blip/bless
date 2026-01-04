@router.post("/pagos/eliminar")
def eliminar_pago(request: Request, idx: int = Form(...)):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    pagos_df = _load_pagos()

    # idx es el número de fila en la tabla (0,1,2...)
    if 0 <= int(idx) < len(pagos_df):
        pagos_df = pagos_df.drop(pagos_df.index[int(idx)]).reset_index(drop=True)
        pagos_df.to_excel(PAGOS, index=False)

    return RedirectResponse("/pagos", status_code=303)
