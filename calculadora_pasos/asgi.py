"""Arranque para servidores (Render): la forma estándar de poner una aplicación web en producción.

    uvicorn asgi:app --host 0.0.0.0 --port $PORT

En tu computador sigues usando `python main.py` (abre el navegador solo). Este archivo es para la nube.

Imprime un mensaje en cada etapa del arranque: si algo falla en Render, el registro muestra EXACTAMENTE en cuál.
"""

import os
import sys
import time

_t0 = time.time()


def _decir(mensaje: str) -> None:
    print(f"[asgi +{time.time() - _t0:5.1f}s] {mensaje}", flush=True)


_decir(f"Python {sys.version.split()[0]} · PORT={os.environ.get('PORT')} · RENDER={os.environ.get('RENDER')}")

from fastapi import FastAPI                      # noqa: E402
from fastapi.responses import PlainTextResponse  # noqa: E402

_decir("FastAPI cargado")
from nicegui import ui                           # noqa: E402

_decir("NiceGUI cargado")
from web.app import registrar                    # noqa: E402

_decir("Calculadora (motor y pantalla) cargada")

app = FastAPI(title="Calculadora paso a paso")


@app.get("/salud")
def salud() -> PlainTextResponse:
    """Dirección que consulta Render para saber que la aplicación está viva. No depende de NiceGUI."""
    return PlainTextResponse("ok")


registrar()
ui.run_with(
    app,
    title="Calculadora paso a paso",
    favicon="🧮",
    language="es",
    reconnect_timeout=10,        # el celular pierde la señal un momento: espera 10 s antes de recargar
    show_welcome_message=False,
)
_decir("Listo: la aplicación está montada y esperando conexiones")
