# app/saldos.py
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime, date

from app import db
from app.auth import require_user

router = APIRouter()
templates = Jinja2Templates(directory="templates")

FREQ_DAYS = {"diario": 1, "semanal": 7, "quincenal": 15, "mensual": 30}

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

def _norm_freq(freq: str) -> str:
    f = (freq or "").strip().lower()
    return f if f in FREQ_DAYS else "mensual"

@router.get("/saldos")
def saldos_home(request: Request):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    clientes = db.fetch_all("""
        SELECT id, nombre, documento, telefono,
               COALESCE(NULLIF(tipo_cobro,''), 'mensual') AS tipo_cobro
        FROM clientes
        ORDER BY nombre ASC
    """)

    today = date.today()
    rows = []

    for c in clientes:
        cid = c["id"]
        movs = db.fetch_all(
            """
            SELECT tipo, fecha, monto, seguro, monto_entregado, interes_mensual,
                   COALESCE(NULLIF(frecuencia,''), 'mensual') AS frecuencia
            FROM pagos
            WHERE cliente_id = %s
            ORDER BY id ASC
            """ if db.db_kind()=="postgres" else
            """
            SELECT tipo, fecha, monto, seguro, monto_entregado, interes_mensual,
                   COALESCE(NULLIF(frecuencia,''), 'mensual') AS frecuencia
            FROM pagos
            WHERE cliente_id = ?
            ORDER BY id ASC
            """,
            [cid]
        )

        total_prestado = 0.0
        total_abonos = 0.0
        last_prestamo_dt = None
        last_abono_dt = None
        last_freq = None
        last_interes = 20.0

        for m in movs:
            t = (m.get("tipo") or "").lower()
            dt = _parse_dt(m.get("fecha"))
            if t == "prestamo":
                total_prestado += float(m.get("monto_entregado") or 0) + float(m.get("seguro") or 0)
                last_prestamo_dt = dt
                last_abono_dt = None
                last_freq = _norm_freq(m.get("frecuencia"))
                last_interes = float(m.get("interes_mensual") or 20)
            else:
                total_abonos += float(m.get("monto") or 0)
                if last_prestamo_dt and dt and dt >= last_prestamo_dt:
                    last_abono_dt = dt

        saldo = total_prestado - total_abonos
        if saldo < 0:
            saldo = 0.0

        freq = last_freq or _norm_freq(c.get("tipo_cobro")) or "mensual"
        freq_days = FREQ_DAYS.get(freq, 30)

        base_dt = last_abono_dt or last_prestamo_dt
        en_mora = False
        mora_dias = 0

        if saldo > 0 and base_dt:
            due = date.fromordinal(base_dt.date().toordinal() + freq_days)
            if today > due:
                en_mora = True
                mora_dias = (today - due).days

        interes_estimado = 0.0
        if saldo > 0 and last_prestamo_dt:
            dias = (today - last_prestamo_dt.date()).days
            meses = max(0.0, dias / 30.0)
            interes_estimado = saldo * (last_interes / 100.0) * meses

        total = saldo + interes_estimado

        rows.append({
            "nombre": c.get("nombre"),
            "documento": c.get("documento"),
            "telefono": c.get("telefono"),
            "frecuencia": freq,
            "saldo": round(saldo, 2),
            "interes": round(interes_estimado, 2),
            "total": round(total, 2),
            "en_mora": en_mora,
            "mora_dias": mora_dias
        })

    rows.sort(key=lambda r: (0 if r["en_mora"] else 1, -r["total"]))
    return templates.TemplateResponse("saldos.html", {"request": request, "user": user, "rows": rows})

@router.get("/alertas/mora")
def alertas_mora(request: Request):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    # Recalcular igual que saldos y filtrar morosos
    resp = saldos_home(request)
    data = resp.context
    morosos = [r for r in data["rows"] if r["en_mora"] and r["total"] > 0]
    return templates.TemplateResponse("alertas_mora.html", {"request": request, "user": user, "rows": morosos})
