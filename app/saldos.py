# app/saldos.py
from datetime import date

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth import require_user
from app.db import get_connection

router = APIRouter(prefix="/saldos", tags=["saldos"])
templates = Jinja2Templates(directory="templates")


def _parse_date(s: str) -> date:
    # Espera YYYY-MM-DD
    try:
        return date.fromisoformat((s or "").strip()[:10])
    except Exception:
        return date.today()


def _add_months(d: date, months: int) -> date:
    y = d.year + (d.month - 1 + months) // 12
    m = (d.month - 1 + months) % 12 + 1
    # clamp day
    mdays = [31, 29 if (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    day = min(d.day, mdays[m - 1])
    return date(y, m, day)


def _full_months_between(d1: date, d2: date) -> int:
    # meses completos entre d1 y d2
    if d2 <= d1:
        return 0
    months = (d2.year - d1.year) * 12 + (d2.month - d1.month)
    if d2.day < d1.day:
        months -= 1
    return max(months, 0)


class Loan:
    __slots__ = ("principal", "interest_due", "last_interest_date", "rate")

    def __init__(self, principal: float, start_date: date, rate: float):
        self.principal = float(principal)
        self.interest_due = 0.0
        self.last_interest_date = start_date
        self.rate = float(rate)

    def accrue_until(self, until: date):
        m = _full_months_between(self.last_interest_date, until)
        if m <= 0 or self.principal <= 0:
            return
        # interés simple por mes sobre capital pendiente
        self.interest_due = round(self.interest_due + (self.principal * self.rate * m), 2)
        self.last_interest_date = _add_months(self.last_interest_date, m)


def _compute_balance(transactions):
    """
    transactions: lista de dict/Row con:
      - fecha, tipo ('prestamo'|'abono'), valor, interes_mensual
    """
    loans = []  # FIFO
    for t in transactions:
        tipo = (t["tipo"] or "abono").strip().lower()
        fecha = _parse_date(t["fecha"] or "")
        valor = float(t["valor"] or 0)
        rate = float(t["interes_mensual"] or 0)

        if tipo == "prestamo":
            # crear nueva deuda por el valor prestado completo
            if rate <= 0:
                rate = 0.20
            loans.append(Loan(valor, fecha, rate))
            continue

        # abono: primero acumular interés hasta la fecha del abono
        for loan in loans:
            loan.accrue_until(fecha)

        pago = valor

        # pagar intereses primero (FIFO)
        for loan in loans:
            if pago <= 0:
                break
            if loan.interest_due > 0:
                x = min(pago, loan.interest_due)
                loan.interest_due = round(loan.interest_due - x, 2)
                pago = round(pago - x, 2)

        # luego capital (FIFO)
        for loan in loans:
            if pago <= 0:
                break
            if loan.principal > 0:
                x = min(pago, loan.principal)
                loan.principal = round(loan.principal - x, 2)
                pago = round(pago - x, 2)

    # saldo total
    capital = round(sum(l.principal for l in loans), 2)
    interes = round(sum(l.interest_due for l in loans), 2)
    total = round(capital + interes, 2)
    return capital, interes, total


@router.get("")
def saldos_page(request: Request):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, nombre FROM clientes ORDER BY nombre ASC")
        clientes = cur.fetchall()

        resultados = []
        for c in clientes:
            cid = c["id"]
            cur.execute(
                """
                SELECT fecha, valor, tipo, interes_mensual
                FROM pagos
                WHERE cliente_id = ?
                ORDER BY date(fecha) ASC, id ASC
                """,
                (cid,),
            )
            tx = cur.fetchall()
            capital, interes, total = _compute_balance(tx)

            resultados.append(
                {
                    "cliente_id": cid,
                    "nombre": c["nombre"],
                    "capital": capital,
                    "interes": interes,
                    "total": total,
                }
            )
    finally:
        conn.close()

    return templates.TemplateResponse(
        "saldos.html",
        {"request": request, "user": user, "saldos": resultados},
    )
