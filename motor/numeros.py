"""Formato de números exactos.

El motor trabaja siempre con `Fraction` (nunca con float), así 0.1 + 0.2 da
exactamente 0.3 y las divisiones no pierden precisión.

Este módulo decide cómo se *muestra* cada número:
  - enteros: 7
  - fracciones: 7/2
  - decimales: 3.5   (solo si el estudiante escribió decimales en su ejercicio)
"""

from fractions import Fraction

# Si algún día quieres coma decimal (0,5), cámbialo aquí.
SEPARADOR_DECIMAL = "."
MENOS = "−"  # signo menos tipográfico (U+2212); el parser también lo entiende


def es_decimal_exacto(f: Fraction) -> bool:
    """True si la fracción tiene expansión decimal finita (denominador 2^a·5^b)."""
    d = f.denominator
    for p in (2, 5):
        while d % p == 0:
            d //= p
    return d == 1


def _decimal_exacto(f: Fraction) -> str:
    """Texto decimal exacto de |f|. Requiere es_decimal_exacto(f)."""
    f = abs(f)
    if f.denominator == 1:
        return str(f.numerator)
    # k = menor cantidad de cifras decimales tal que 10^k sea múltiplo del denominador
    k = 1
    while (10 ** k) % f.denominator != 0:
        k += 1
    n = f.numerator * ((10 ** k) // f.denominator)
    s = str(n).rjust(k + 1, "0")
    entero, decimales = s[:-k], s[-k:].rstrip("0")
    return entero + (SEPARADOR_DECIMAL + decimales if decimales else "")


def se_ve_como_fraccion(f: Fraction, decimales: bool) -> bool:
    """¿Este número se mostrará como a/b (y no como entero o decimal)?"""
    if f.denominator == 1:
        return False
    return not (decimales and es_decimal_exacto(f))


def formatear(f: Fraction, decimales: bool = False) -> str:
    """Texto plano de un número: '3', '−3', '7/2', '3.5'."""
    signo = MENOS if f < 0 else ""
    a = abs(f)
    if a.denominator == 1:
        return f"{signo}{a.numerator}"
    if decimales and es_decimal_exacto(a):
        return f"{signo}{_decimal_exacto(a)}"
    return f"{signo}{a.numerator}/{a.denominator}"


def formatear_latex(f: Fraction, decimales: bool = False) -> str:
    """LaTeX de un número: '3', '-3', '\\frac{7}{2}', '3.5'."""
    signo = "-" if f < 0 else ""
    a = abs(f)
    if a.denominator == 1:
        return f"{signo}{a.numerator}"
    if decimales and es_decimal_exacto(a):
        return f"{signo}{_decimal_exacto(a)}"
    return f"{signo}\\frac{{{a.numerator}}}{{{a.denominator}}}"


def decimal_aproximado(f: Fraction, cifras: int = 6) -> tuple[str, bool]:
    """Decimal de f. Devuelve (texto, es_exacto). None-safe para enteros."""
    if es_decimal_exacto(f):
        return formatear(f, True), True
    signo = MENOS if f < 0 else ""
    a = abs(f)
    escala = 10 ** cifras
    n = (a.numerator * escala * 2 + a.denominator) // (a.denominator * 2)  # redondeo
    s = str(n).rjust(cifras + 1, "0")
    entero, dec = s[:-cifras], s[-cifras:].rstrip("0") or "0"
    return f"{signo}{entero}{SEPARADOR_DECIMAL}{dec}", False
