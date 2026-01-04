@router.get("/pagos", response_class=HTMLResponse)
def pagos_form(request: Request):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    clientes_df = _load_clientes()
    clientes = clientes_df.to_dict(orient="records")

    pagos_df = _load_pagos()

    # Ordenar por fecha (si falla, no rompe)
    try:
        pagos_df["_fecha_dt"] = pd.to_datetime(pagos_df["fecha"], errors="coerce")
        pagos_df = pagos_df.sort_values(by="_fecha_dt", ascending=False)
        pagos_df = pagos_df.drop(columns=["_fecha_dt"])
    except Exception:
        pass

    pagos = pagos_df.to_dict(orient="records")

    return templates.TemplateResponse(
        "pagos.html",
        {"request": request, "clientes": clientes, "pagos": pagos, "user": user}
    )
