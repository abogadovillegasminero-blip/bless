# app/saldos.py
from datetime import datetime, date

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth import require_user
from app.db import get_connection

router = APIRouter(prefix="/saldos", tags=["saldos"])
templates = Jinja2Templates(directory="templates")

INTERES_MENSUAL = 0.20


def _months_elapsed(fecha_iso: str) -> int:
    """
    Calcula meses completos transcurridos desde fecha_iso (YYYY-MM-DD) hasta hoy.
    Regla simple: diferencia por año/mes y si el día de hoy es menor al día del préstamo,
    resta 1 (no se completó el mes).
    """
    try:
        f = datetime.strptime((fecha_iso or "").strip(), "%Y-%m-%d").date()
    except Exception:
        return 0

    today = date.today()
    months = (today.year - f.year) * 12 + (today.month - f.month)
    if today.day < f.day:
        months -= 1
    return max(0, months)


@router.get("")
def saldos_page(request: Request):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    conn = get_connection()
    try:
        cur = conn.cursor()

        # Totales base por cliente (prestado / abonos / seguro / entregado)
        cur.execute("""
            SELECT
              c.id AS cliente_id,
              c.nombre AS nombre,
              COALESCE(c.documento, '') AS documento,

              SUM(CASE WHEN COALESCE(p.tipo,'abono')='prestamo' THEN COALESCE(p.valor,0) ELSE 0 END) AS total_prestado,
              SUM(CASE WHEN COALESCE(p.tipo,'abono')='prestamo' THEN COALESCE(p.seguro,0) ELSE 0 END) AS total_seguro,
              SUM(CASE WHEN COALESCE(p.tipo,'abono')='prestamo' THEN COALESCE(p.monto_entregado,0) ELSE 0 END) AS total_entregado,

              SUM(CASE WHEN COALESCE(p.tipo,'abono')='abono' THEN COALESCE(p.valor,0) ELSE 0 END) AS total_abonos
            FROM clientes c
            LEFT JOIN pagos p ON p.cliente_id = c.id
            GROUP BY c.id
            ORDER BY c.nombre ASC
        """)
        clientes = cur.fetchall()

        saldos = []
        for c in clientes:
            cliente_id = c["cliente_id"]

            # Traemos TODOS los préstamos del cliente para calcular interés por meses
            cur.execute("""
                SELECT fecha, valor
                FROM pagos
                WHERE cliente_id = ?
                  AND COALESCE(tipo,'abono')='prestamo'
                ORDER BY id ASC
            """, (cliente_id,))
            prestamos = cur.fetchall()

            interes_acumulado = 0.0
            deuda_con_interes = 0.0

            for pr in prestamos:
                fecha = pr["fecha"] or ""
                valor = float(pr["valor"] or 0)
                meses = _months_elapsed(fecha)

                # interés simple mensual: valor * 0.20 * meses
                interes = valor * INTERES_MENSUAL * meses
                interes_acumulado += interes
                deuda_con_interes += (valor + interes)

            total_abonos = float(c["total_abonos"] or 0)
            total_prestado = float(c["total_prestado"] or 0)
            total_seguro = float(c["total_seguro"] or 0)
            total_entregado = float(c["total_entregado"] or 0)

            saldo = deuda_con_interes - total_abonos

            a_favor = 0.0
            if saldo < 0:
                a_favor = abs(saldo)
                saldo = 0.0

            saldos.append({
                "cliente_id": cliente_id,
                "nombre": c["nombre"],
                "documento": c["documento"],
                "total_prestado": round(total_prestado, 2),
                "interes_acumulado": round(interes_acumulado, 2),
                "deuda_con_interes": round(deuda_con_interes, 2),
                "total_abonos": round(total_abonos, 2),
                "saldo": round(saldo, 2),
                "a_favor": round(a_favor, 2),
                "total_seguro": round(total_seguro, 2),
                "total_entregado": round(total_entregado, 2),
            })

    finally:
        conn.close()

    return templates.TemplateResponse(
        "saldos.html",
        {"request": request, "user": user, "saldos": saldos},
    )
