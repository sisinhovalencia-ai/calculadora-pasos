"""Punto de entrada de la aplicación web EN TU COMPUTADOR.

    python main.py

Luego abre http://localhost:8000 en el navegador.

Si el puerto 8000 también está ocupado en tu computador, usa otro sin tocar el código:
    Windows (cmd):   set PORT=8123 && python main.py
    Mac/Linux:       PORT=8123 python main.py

En Render NO se usa este archivo: Render arranca `asgi.py` con uvicorn (ver render.yaml y el README).
Si quieres probar el modo nube en tu computador, usa `python main.py` con RENDER=1 (escucha en todas las direcciones):
    Windows (cmd):   set RENDER=1 && set PORT=10000 && python main.py
"""

import os

from nicegui import ui

from web.app import registrar
from web.arranque import direccion_de_escucha, en_la_nube, puerto

registrar()

if __name__ in {"__main__", "__mp_main__"}:
    nube = en_la_nube(os.environ)
    host, port = direccion_de_escucha(os.environ), puerto(os.environ)
    print(f"Arrancando en {host}:{port} (modo nube: {nube})", flush=True)
    ui.run(
        title="Calculadora paso a paso",
        favicon="🧮",
        language="es",
        reload=False,
        show=not nube,                          # en tu computador abre el navegador; en un servidor no hay navegador
        host=host,
        port=port,
        reconnect_timeout=10,                   # el celular pierde la señal un momento: espera 10 s antes de recargar
        uvicorn_logging_level="info",           # en el registro de Render se ve cuándo está listo
    )
