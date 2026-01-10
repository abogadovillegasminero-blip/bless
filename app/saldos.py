# app/saldos.py
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from app import db

router = APIRouter()
templates = Jinja2Templates(directory="templates")

DEFAULT_INTERES_MENSUAL = 20.0  # 20% mensual


@router.get("/saldos")
def ver_saldos(request: Request):
    """
    Mantiene el interés mensual fijo (por préstamo), pero:
    - si frecuencia está vacía -> asumir 'mensual'
    - NO rompe si valores vienen NULL
    """
    clientes = db.fetch_all("""
        SELECT id, nombre, documento, telefono, direccion, observaciones, COALESCE(NULLIF(tipo_cobro,''), 'mensual') AS tipo_cobro
        FROM clientes
        ORDER BY nombre ASC
    """)

    saldos = []

    for c in clientes:
        cliente_id = c["id"] if isinstance(c, dict) else c[0]

        # Totales
        tot_prestamos = db.fetch_one("""
            SELECT COALESCE(SUM(monto_entregado), 0) AS total
            FROM pagos
            WHERE cliente_id = {ph} AND tipo = 'prestamo'
        """.format(ph="?" if db.db_kind() == "sqlite" else "%s"), [cliente_id])

        tot_abonos = db.fetch_one("""
            SELECT COALESCE(SUM(monto), 0) AS total
            FROM pagos
            WHERE cliente_id = {ph} AND tipo = 'abono'
        """.format(ph="?" if db.db_kind() == "sqlite" else "%s"), [cliente_id])

        total_prestado = (tot_prestamos["total"] if isinstance(tot_prestamos, dict) else tot_prestamos[0]) or 0
        total_abonado = (tot_abonos["total"] if isinstance(tot_abonos, dict) else tot_abonos[0]) or 0
        saldo = float(total_prestado) - float(total_abonado)

        # Interés mensual total (solo sobre préstamos)
        # Si interes_mensual viene NULL -> DEFAULT_INTERES_MENSUAL
        # Si frecuencia viene NULL/vacía -> 'mensual' (solo informativo)
        prestamos = db.fetch_all("""
            SELECT
              COALESCE(NULLIF(frecuencia,''), 'mensual') AS frecuencia,
              COALESCE(interes_mensual, {default_im}) AS interes_mensual,
              COALESCE(monto_entregado, 0) AS monto_entregado
            FROM pagos
            WHERE cliente_id = {ph} AND tipo = 'prestamo'
        """.format(
            ph="?" if db.db_kind() == "sqlite" else "%s",
            default_im=DEFAULT_INTERES_MENSUAL
        ), [cliente_id])

        interes_mensual_total = 0.0
        # Mantener interés mensual fijo (no convertir por frecuencia)
        for p in prestamos:
            if isinstance(p, dict):
                monto_entregado = float(p.get("monto_entregado") or 0)
                interes_pct = float(p.get("interes_mensual") or DEFAULT_INTERES_MENSUAL)
            else:
                # fallback
                monto_entregado = float(p[2] or 0)
                interes_pct = float(p[1] or DEFAULT_INTERES_MENSUAL)

            interes_mensual_total += (monto_entregado * (interes_pct / 100.0))

        # Empaquetar resultado
        saldos.append({
            "cliente": c,
            "total_prestado": float(total_prestado),
            "total_abonado": float(total_abonado),
            "saldo": float(saldo),
            "interes_mensual_total": float(interes_mensual_total),
        })

    # No se entrega template aquí porque no lo pediste.
    # Si tu template actual usa claves viejas, NO se rompe por agregar nuevas.
    return templates.TemplateResponse(
        "saldos.html",
        {
            "request": request,
            "saldos": saldos,
            "default_interes_mensual": DEFAULT_INTERES_MENSUAL,
        }
    )
