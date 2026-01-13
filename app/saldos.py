# app/saldos.py
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime, date

from app import db
from app.auth import require_user

router = APIRouter()
templates = Jinja2Templates(directory="templates")

FREQ_DAYS = {
    "diario": 1,
    "semanal": 7,
    "quincenal": 15,
    "mensual": 30,
}

def _parse_dt(s: str):
    if not s:
        return None
    s = str(s).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            pass
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None

def _freq_days(freq: str) -> int:
    f = (freq or "").strip().lower()
    return FREQ_DAYS.get(f, 30)

def _norm_freq(freq: str) -> str:
    f = (freq or "").strip().lower()
    return f if f in FREQ_DAYS else "mensual"

@router.get("/saldos")
def saldos_home(request: Request):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    clientes = db.fetch_all("""
        SELECT id, nombre, documento, telefono, direccion, codigo_postal, observaciones,
               COALESCE(NULLIF(tipo_cobro,''), 'mensual') AS tipo_cobro
        FROM clientes
        ORDER BY nombre ASC
    """)

    rows = []
    today = date.today()

    for c in clientes:
        cid = c["id"]

        # movimientos del cliente
        movs = db.fetch_all("""
            SELECT tipo, fecha, monto, seguro, monto_entregado, interes_mensual,
                   COALESCE(NULLIF(frecuencia,''), 'mensual') AS frecuencia
            FROM pagos
            WHERE cliente_id = %s
            ORDER BY id ASC
        """ if db.db_kind()=="postgres" else """
            SELECT tipo, fecha, monto, seguro, monto_entregado, interes_mensual,
                   COALESCE(NULLIF(frecuencia,''), 'mensual') AS frecuencia
            FROM pagos
            WHERE cliente_id = ?
            ORDER BY id ASC
        """, [cid])

        total_prestado = 0.0
        total_abonos = 0.0

        last_prestamo_dt = None
        last_prestamo_freq = None
        last_interes = 20.0

        # para mora: fecha del último abono después del último préstamo
        last_abono_dt = None

        for m in movs:
            t = (m.get("tipo") or "").lower()
            dt = _parse_dt(m.get("fecha"))
            if t == "prestamo":
                total_prestado += float(m.get("monto_entregado") or 0) + float(m.get("seguro") or 0)
                last_prestamo_dt = dt
                last_prestamo_freq = _norm_freq(m.get("frecuencia"))
                last_interes = float(m.get("interes_mensual") or 20)
                last_abono_dt = None  # resetea: mora se cuenta desde el préstamo
            else:
                total_abonos += float(m.get("monto") or 0)
                # solo cuenta abonos posteriores al último préstamo
                if last_prestamo_dt and dt and dt >= last_prestamo_dt:
                    last_abono_dt = dt

        saldo_base = total_prestado - total_abonos
        if saldo_base < 0:
            saldo_base = 0.0

        # Frecuencia usada para mora:
        freq = last_prestamo_freq or _norm_freq(c.get("tipo_cobro")) or "mensual"
        freq_days = _freq_days(freq)

        # Próxima fecha de pago esperada:
        base_dt = last_abono_dt or last_prestamo_dt
        mora_dias = 0
        en_mora = False

        if saldo_base > 0 and base_dt:
            next_due = base_dt.date()
            # siguiente vencimiento = base + freq_days
            next_due = date.fromordinal(next_due.toordinal() + freq_days)
            if today > next_due:
                mora_dias = (today - next_due).days
                en_mora = True

        # interés simple mensual (no compuesto)
        interes_calc = 0.0
        if saldo_base > 0 and last_prestamo_dt:
            dias = (datetime.now().date() - last_prestamo_dt.date()).days
            meses = max(0.0, dias / 30.0)
            interes_calc = saldo_base * (last_interes / 100.0) * meses

        total_deuda = saldo_base + interes_calc

        rows.append({
            "cliente_id": cid,
            "nombre": c.get("nombre"),
            "documento": c.get("documento"),
            "telefono": c.get("telefono"),
            "saldo_base": round(saldo_base, 2),
            "interes_estimado": round(interes_calc, 2),
            "total_deuda": round(total_deuda, 2),
            "frecuencia": freq,
            "en_mora": en_mora,
            "mora_dias": mora_dias,
        })

    # orden: primero en mora, luego mayor deuda
    rows.sort(key=lambda x: (0 if x["en_mora"] else 1, -x["total_deuda"]))

    return templates.TemplateResponse("saldos.html", {"request": request, "user": user, "rows": rows})

@router.get("/alertas/mora")
def alertas_mora(request: Request):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    # Reutiliza la misma lógica: lista de saldos y filtra morosos
    # (simple y robusto)
    resp = saldos_home(request)
    data = resp.context
    morosos = [r for r in data["rows"] if r["en_mora"] and r["total_deuda"] > 0]
    return templates.TemplateResponse("alertas_mora.html", {"request": request, "user": user, "rows": morosos})
