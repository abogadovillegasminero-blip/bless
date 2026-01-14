  # app/contabilidad.py
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app import db
from app.utils import co_date_today, to_pesos

# Tu auth ya existe (según tus logs)
from app.auth import require_user

router = APIRouter()
templates = Jinja2Templates(directory="templates")

CATEGORIAS = ["general", "transporte", "alimentacion", "servicios", "oficina", "imprevistos"]


def _require_admin(request: Request):
    user = require_user(request)
    # user debe ser dict con role (según tu tabla usuarios)
    if not user or (user.get("role") != "admin"):
        raise HTTPException(status_code=403, detail="Solo administrador.")
    return user


def _month_range(yyyymm: str) -> tuple[str, str]:
    y, m = map(int, yyyymm.split("-"))
    start = f"{y:04d}-{m:02d}-01"
    if m == 12:
        end = f"{y+1:04d}-01-01"
    else:
        end = f"{y:04d}-{m+1:02d}-01"
    return start, end


@router.get("/contabilidad")
def contabilidad(request: Request, mes: str | None = None):
    _require_admin(request)

    hoy = co_date_today()
    if not mes:
        mes = f"{hoy.year:04d}-{hoy.month:02d}"
    start, end = _month_range(mes)

    base_hoy = db.fetch_one("SELECT fecha, base_valor FROM base_dia WHERE fecha = ?", [str(hoy)])

    gastos_hoy = db.fetch_all("""
        SELECT id, fecha, concepto, categoria, valor, cobrador_username
        FROM gastos
        WHERE fecha = ?
        ORDER BY id DESC
    """, [str(hoy)])

    prestado_total_row = db.fetch_one("""
        SELECT COALESCE(SUM(valor),0) AS total
        FROM prestamos
        WHERE fecha >= ? AND fecha < ?
    """, [start, end])
    prestado_total = (prestado_total_row or {}).get("total", 0)

    seguros_por_cobrador = db.fetch_all("""
        SELECT cobrador_username, COALESCE(SUM(valor),0) AS total
        FROM seguros_recaudos
        WHERE fecha >= ? AND fecha < ?
        GROUP BY cobrador_username
        ORDER BY total DESC
    """, [start, end])

    gastos_mes_total_row = db.fetch_one("""
        SELECT COALESCE(SUM(valor),0) AS total
        FROM gastos
        WHERE fecha >= ? AND fecha < ?
    """, [start, end])
    gastos_mes_total = (gastos_mes_total_row or {}).get("total", 0)

    gastos_por_categoria = db.fetch_all("""
        SELECT categoria, COALESCE(SUM(valor),0) AS total
        FROM gastos
        WHERE fecha >= ? AND fecha < ?
        GROUP BY categoria
        ORDER BY total DESC
    """, [start, end])

    prestamos_lista = db.fetch_all("""
        SELECT p.id, p.fecha, p.valor, p.observaciones, p.cobrador_username,
               COALESCE(c.nombre,'') AS cliente
        FROM prestamos p
        LEFT JOIN clientes c ON c.id = p.cliente_id
        WHERE p.fecha >= ? AND p.fecha < ?
        ORDER BY p.id DESC
    """, [start, end])

    return templates.TemplateResponse("contabilidad.html", {
        "request": request,
        "hoy": str(hoy),
        "mes": mes,
        "base_hoy": base_hoy,
        "gastos_hoy": gastos_hoy,
        "categorias": CATEGORIAS,
        "seguros_por_cobrador": seguros_por_cobrador,
        "gastos_mes_total": gastos_mes_total,
        "gastos_por_categoria": gastos_por_categoria,
        "prestado_total": prestado_total,
        "prestamos_lista": prestamos_lista,
    })


@router.post("/contabilidad/base")
def guardar_base(request: Request, fecha: str = Form(...), base_valor: str = Form(...)):
    _require_admin(request)

    base_pesos = to_pesos(base_valor)

    existe = db.fetch_one("SELECT fecha FROM base_dia WHERE fecha = ?", [fecha])
    if existe:
        db.execute("UPDATE base_dia SET base_valor = ? WHERE fecha = ?", [base_pesos, fecha])
    else:
        db.execute("INSERT INTO base_dia (fecha, base_valor) VALUES (?, ?)", [fecha, base_pesos])

    return RedirectResponse("/contabilidad", status_code=303)


@router.post("/contabilidad/gasto")
def crear_gasto(
    request: Request,
    fecha: str = Form(...),
    concepto: str = Form(...),
    categoria: str = Form("general"),
    valor: str = Form(...),
    cobrador_username: str = Form(""),
):
    _require_admin(request)

    v = to_pesos(valor)
    categoria = (categoria or "general").strip().lower()
    if categoria not in CATEGORIAS:
        categoria = "general"

    db.execute("""
        INSERT INTO gastos (fecha, concepto, categoria, valor, cobrador_username)
        VALUES (?, ?, ?, ?, ?)
    """, [fecha, concepto.strip(), categoria, v, (cobrador_username or "").strip()])

    return RedirectResponse("/contabilidad", status_code=303)


@router.post("/contabilidad/gasto/eliminar/{gasto_id}")
def eliminar_gasto(request: Request, gasto_id: int):
    _require_admin(request)
    db.execute("DELETE FROM gastos WHERE id = ?", [gasto_id])
    return RedirectResponse("/contabilidad", status_code=303)


@router.post("/contabilidad/seguro")
def agregar_seguro(
    request: Request,
    fecha: str = Form(...),
    cobrador_username: str = Form(...),
    valor: str = Form(...),
):
    _require_admin(request)

    v = to_pesos(valor)
    cobrador_username = (cobrador_username or "").strip()
    if not cobrador_username:
        return RedirectResponse("/contabilidad", status_code=303)

    db.execute("""
        INSERT INTO seguros_recaudos (fecha, cobrador_username, valor)
        VALUES (?, ?, ?)
    """, [fecha, cobrador_username, v])

    return RedirectResponse("/contabilidad", status_code=303)


@router.post("/contabilidad/prestamo")
def agregar_prestamo(
    request: Request,
    fecha: str = Form(...),
    valor: str = Form(...),
    cliente_id: str = Form(""),
    cobrador_username: str = Form(""),
    observaciones: str = Form(""),
):
    _require_admin(request)

    v = to_pesos(valor)

    cid = None
    if (cliente_id or "").strip().isdigit():
        cid = int(cliente_id.strip())

    db.execute("""
        INSERT INTO prestamos (fecha, cliente_id, cobrador_username, valor, observaciones)
        VALUES (?, ?, ?, ?, ?)
    """, [fecha, cid, (cobrador_username or "").strip(), v, (observaciones or "").strip()])

    return RedirectResponse("/contabilidad", status_code=303)
