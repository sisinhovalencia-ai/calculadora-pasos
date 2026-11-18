"""Ayudas para dibujar fórmulas y texto del motor dentro de la página.

Las fórmulas se convierten de LaTeX a MathML con `latex2mathml` (librería pura de
Python). Los navegadores actuales dibujan MathML sin cargar nada externo, así
que funciona sin internet y sin JavaScript extra.

IMPORTANTE: todo lo que se inserta en HTML pasa por `escape()`. Aunque el motor
solo produce dígitos y operadores, así nunca queda una puerta abierta si algún
día un solucionador devuelve texto escrito por el usuario.
"""

from html import escape

from latex2mathml.converter import convert


def mathml(latex: str, texto_plano: str = "") -> str:
    """LaTeX -> MathML. Si la conversión falla, muestra el texto plano (nunca rompe la pantalla)."""
    try:
        return convert(latex, display="inline")
    except Exception:  # noqa: BLE001 - cualquier fallo de la librería cae al texto plano
        return f'<span class="formula-plana">{escape(texto_plano or latex)}</span>'


def resaltar(explicacion: str, operacion: str) -> str:
    """HTML seguro: la explicación con la operación resuelta marcada con resaltador."""
    i = explicacion.find(operacion) if operacion else -1
    if i < 0:
        return escape(explicacion)
    antes, medio, despues = explicacion[:i], operacion, explicacion[i + len(operacion):]
    return f'{escape(antes)}<mark class="marca">{escape(medio)}</mark>{escape(despues)}'
