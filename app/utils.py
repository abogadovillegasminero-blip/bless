# app/utils.py
from __future__ import annotations

from datetime import datetime, date, time, timedelta
from zoneinfo import ZoneInfo
from typing import Optional

TZ_CO = ZoneInfo("America/Bogota")


def now_co() -> datetime:
    """Fecha/hora actual de Colombia (timezone aware)."""
    return datetime.now(TZ_CO)


def co_date_today() -> date:
    return now_co().date()


def parse_co_datetime(date_str: str, time_str: str) -> datetime:
    """
    Recibe 'YYYY-MM-DD' y 'HH:MM' (inputs HTML) y devuelve datetime Colombia (aware).
    """
    y, m, d = map(int, date_str.split("-"))
    hh, mm = map(int, time_str.split(":"))
    dt = datetime(y, m, d, hh, mm, tzinfo=TZ_CO)
    return dt


def fmt_co(dt: Optional[datetime]) -> str:
    """Formato legible Colombia."""
    if not dt:
        return ""
    if dt.tzinfo is None:
        # si viene naive, asumimos Colombia
        dt = dt.replace(tzinfo=TZ_CO)
    return dt.astimezone(TZ_CO).strftime("%Y-%m-%d %H:%M")


def money_miles(value) -> int:
    """
    Convierte pesos a 'miles' sin decimales:
      1000 -> 1
      150000 -> 150
    - Quita centésimas (si llega float).
    """
    if value is None:
        return 0
    try:
        v = int(float(value))
    except Exception:
        return 0
    # en miles
    return v // 1000


def next_due_date(tipo_cobro: str, last_date: date) -> date:
    """
    Calcula próximo vencimiento según tipo_cobro.
    (Ajusta si manejas otra lógica)
    """
    tipo = (tipo_cobro or "mensual").strip().lower()
    if tipo == "diario":
        return last_date + timedelta(days=1)
    if tipo == "semanal":
        return last_date + timedelta(days=7)
    if tipo == "quincenal":
        return last_date + timedelta(days=15)
    # mensual (simple)
    return last_date + timedelta(days=30)


def mora_dias(vencimiento: date, hoy: Optional[date] = None) -> int:
    hoy = hoy or co_date_today()
    if hoy <= vencimiento:
        return 0
    return (hoy - vencimiento).days
