"""Decisiones de arranque (dónde escuchar y en qué puerto), separadas para poder probarlas."""

from collections.abc import Mapping

VARIABLES_DE_RENDER = ("RENDER", "RENDER_SERVICE_ID", "RENDER_EXTERNAL_URL")


def en_la_nube(entorno: Mapping) -> bool:
    """¿Estamos corriendo en Render? (Render define estas variables en todos sus servicios.)"""
    return any(entorno.get(v) for v in VARIABLES_DE_RENDER)


def direccion_de_escucha(entorno: Mapping) -> str:
    """En tu computador solo él puede abrirla (127.0.0.1); en la nube tiene que aceptar conexiones de afuera (0.0.0.0).
    `APP_HOST` manda sobre todo lo demás si se define."""
    if entorno.get("APP_HOST"):
        return entorno["APP_HOST"]
    if en_la_nube(entorno):
        return "0.0.0.0"
    return entorno.get("HOST") or "127.0.0.1"


def puerto(entorno: Mapping, por_defecto: int = 8000) -> int:
    try:
        return int(entorno.get("PORT") or por_defecto)
    except ValueError:
        return por_defecto
