def layout(titulo, contenido):
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>{titulo}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background: #f4f6f8;
                margin: 0;
                padding: 0;
            }}
            header {{
                background: #111827;
                padding: 15px;
                color: white;
                text-align: center;
                font-size: 22px;
                font-weight: bold;
            }}
            nav {{
                background: #1f2937;
                padding: 10px;
                text-align: center;
            }}
            nav a {{
                color: white;
                margin: 0 10px;
                text-decoration: none;
                font-weight: bold;
            }}
            nav a:hover {{
                text-decoration: underline;
            }}
            .container {{
                max-width: 900px;
                margin: 30px auto;
                background: white;
                padding: 25px;
                border-radius: 10px;
                box-shadow: 0 0 10px #ccc;
            }}
            h2 {{
                margin-top: 0;
            }}
        </style>
    </head>
    <body>
        <header>B L E S S</header>
        <nav>
            <a href="/">🏠 Inicio</a>
            <a href="/clientes">👥 Clientes</a>
            <a href="/pagos">💵 Pagos</a>
            <a href="/saldos">🧮 Saldos</a>
            <a href="/reportes">📊 Reportes</a>
        </nav>
        <div class="container">
            <h2>{titulo}</h2>
            {contenido}
        </div>
    </body>
    </html>
    """
