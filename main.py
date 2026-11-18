"""Punto de entrada de la aplicación web.

    python main.py

Luego abre http://localhost:8000 en el navegador.

Si el puerto 8000 también está ocupado en tu computador, usa otro sin tocar el código:
    Windows (cmd):   set PORT=8123 && python main.py
    Mac/Linux:       PORT=8123 python main.py

En Render (u otro servicio en la nube) NO hay que tocar nada: Render define la variable PORT y la variable RENDER,
y entonces la aplicación escucha en todas las direcciones (0.0.0.0) en vez de solo en este computador.
Para probar ese modo en tu computador:
    Windows (cmd):   set RENDER=1 && set PORT=10000 && python main.py
"""

import os

from nicegui import ui

from web.app import registrar

registrar()

EN_LA_NUBE = bool(os.environ.get("RENDER"))
# En tu computador: solo él puede abrirla. En la nube: tiene que aceptar conexiones de afuera.
HOST = os.environ.get("HOST", "0.0.0.0" if EN_LA_NUBE else "127.0.0.1")

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        title="Calculadora paso a paso",
        favicon="🧮",
        language="es",
        reload=False,
        show=not EN_LA_NUBE,                    # en tu computador abre el navegador; en un servidor no hay navegador
        host=HOST,
        port=int(os.environ.get("PORT", 8000)),
        reconnect_timeout=10,                   # el celular pierde la señal un momento: espera 10 s antes de recargar
    )
