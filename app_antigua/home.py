from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
def home():
    html = """
    <html>
        <head>
            <title>Bless - Inicio</title>
        </head>
        <body style="font-family: Arial; text-align: center; margin-top: 50px;">
            <h1>📊 Sistema Bless</h1>

            <br><br>

            <a href="/clientes-ui">
                <button style="padding: 15px 30px; font-size: 18px;">
                    👤 Clientes
                </button>
            </a>

            <br><br>

            <a href="/pagos-ui">
                <button style="padding: 15px 30px; font-size: 18px;">
                    💰 Pagos
                </button>
            </a>

        </body>
    </html>
    """
    return HTMLResponse(html)
