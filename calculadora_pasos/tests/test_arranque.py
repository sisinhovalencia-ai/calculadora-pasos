"""Pruebas del arranque: dónde escucha la app y que de verdad arranque como lo hará Render."""

import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

from web.arranque import direccion_de_escucha, en_la_nube, puerto

RAIZ = Path(__file__).resolve().parent.parent


def test_en_tu_computador_escucha_solo_en_local():
    assert direccion_de_escucha({}) == "127.0.0.1"
    assert direccion_de_escucha({"PORT": "8123"}) == "127.0.0.1"        # usar otro puerto no abre la app a la red
    assert not en_la_nube({"PORT": "8123"})


@pytest.mark.parametrize("entorno", [{"RENDER": "true"}, {"RENDER_SERVICE_ID": "srv-1"}, {"RENDER_EXTERNAL_URL": "https://a.b"}])
def test_en_render_escucha_en_todas_las_direcciones(entorno):
    assert en_la_nube(entorno) and direccion_de_escucha(entorno) == "0.0.0.0"


def test_hosts_explicitos_mandan():
    assert direccion_de_escucha({"RENDER": "true", "APP_HOST": "10.0.0.5"}) == "10.0.0.5"
    assert direccion_de_escucha({"HOST": "192.168.1.9"}) == "192.168.1.9"
    assert direccion_de_escucha({"RENDER": "true", "HOST": "extraño"}) == "0.0.0.0"   # una variable HOST rara no rompe Render


def test_puerto():
    assert puerto({}) == 8000 and puerto({"PORT": "10000"}) == 10000 and puerto({"PORT": "abc"}) == 8000


def _puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _esperar(url: str, segundos: float = 40) -> str:
    t0, ultimo = time.time(), None
    while time.time() - t0 < segundos:
        try:
            return urllib.request.urlopen(url, timeout=3).read().decode("utf-8")
        except Exception as e:  # noqa: BLE001
            ultimo = e
            time.sleep(0.4)
    raise AssertionError(f"{url} no respondió en {segundos} s: {ultimo}")


def test_asgi_arranca_como_en_render():
    """Arranca `uvicorn asgi:app` en un proceso aparte (igual que Render) y le pide /salud y un ejercicio."""
    puerto_libre = _puerto_libre()
    entorno = {**os.environ, "RENDER": "true", "PORT": str(puerto_libre), "PYTHONUNBUFFERED": "1"}
    proceso = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "asgi:app", "--host", "127.0.0.1", "--port", str(puerto_libre),
         "--log-level", "info"], cwd=RAIZ, env=entorno, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        assert _esperar(f"http://127.0.0.1:{puerto_libre}/salud") == "ok"
        pagina = _esperar(f"http://127.0.0.1:{puerto_libre}/?q=factorizar%20x%C2%B2%20%E2%88%92%209")
        assert "Resultado" in pagina and "diferencia de cuadrados" in pagina
    finally:
        proceso.terminate()
        salida = proceso.communicate(timeout=15)[0]
    for etapa in ("FastAPI cargado", "NiceGUI cargado", "Listo: la aplicación está montada"):
        assert etapa in salida, f"falta el mensaje de diagnóstico {etapa!r}"
    assert "Traceback" not in salida
