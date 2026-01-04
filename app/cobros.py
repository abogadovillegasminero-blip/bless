import os
from datetime import date, timedelta

import pandas as pd
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth import require_user

router = APIRouter()
templates = Jinja2Templates(directory="templates")

DATA_DIR = "data"
CLIENTES_XLSX = f"{DATA_DIR}/clientes.xlsx"
PAGOS_X
