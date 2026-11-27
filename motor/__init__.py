"""Motor matemático paso a paso.

Uso rápido:
    from motor import resolver
    sol = resolver("2 + 3 × (4 − 1)^2")
    for paso in sol.pasos:
        print(paso.explicacion, "→", paso.expresion)
    print(sol.resultado)

Para que la calculadora decida sola qué solucionador usar, `resolver_ejercicio(texto)`.
"""

import re
from dataclasses import replace

from .algebra import leer, separar_comando, tiene_comando
from .aritmetica import resolver
from .columnas import resolver_columnas
from .cuadraticas import es_cuadratica, resolver_cuadratica
from .ecuaciones import resolver_ecuacion
from .errores import ErrorDeEntrada, ErrorMatematico, ErrorMotor
from .expr import tiene_letras
from .factorizacion import resolver_factorizacion
from .formulas import resolver_formula
from .fracciones_alg import resolver_fraccion
from .pasos import Paso, Solucion
from .polinomios import resolver_polinomio
from .radicales import resolver_radicales


def resolver_ejercicio(texto: str) -> "Solucion":
    """Decide solo qué solucionador usar, según lo que se escribió:

    «despejar t en v = d/t»                       → fórmula
    con "=", "<", ">", "≤" o "≥"                  → ecuación o desigualdad
    «factorizar …» / «desarrollar …» / «simplificar …» / «reducir …» → álgebra
    con letras y sin nada más                     → álgebra (fracción si hay letras abajo; si no, polinomio)
    solo números                                  → aritmética (y si una raíz no es exacta, radicales)
    """
    if texto is not None and re.search(r"\bdespejar\b", texto, re.IGNORECASE):
        return resolver_formula(texto)
    if texto is not None and "=" in texto and es_cuadratica(texto):
        return resolver_cuadratica(texto)
    if texto is not None and any(c in texto for c in "=<>≤≥"):
        return resolver_ecuacion(texto)
    if texto is not None and tiene_comando(texto):
        comando, resto = separar_comando(texto)
        return _algebra(comando, resto, texto)
    if texto is not None and tiene_letras(texto):
        return _algebra(None, texto.strip(), texto)
    try:
        return resolver(texto)
    except ErrorMatematico as e:
        if "no es exacta" in str(e):
            return resolver_radicales(texto)
        raise


def _algebra(comando, resto: str, entrada: str) -> "Solucion":
    """Álgebra de polinomios, factorización, fracciones algebraicas y radicales."""
    if comando == "factorizar":
        return resolver_factorizacion(resto, entrada)
    if not tiene_letras(resto):
        if re.search(r"[√∛∜]|raiz|raíz|sqrt|\^\s*\(?\s*\d+/\d", resto, re.IGNORECASE):
            return resolver_radicales(resto, entrada)
        if comando in ("simplificar", "reducir", "desarrollar"):
            return resolver(resto)                                      # solo números: es aritmética
    from .polinomios import _con_division_por_letras
    _arbol, e0, _orden = leer(resto)
    if _con_division_por_letras(e0):
        return resolver_fraccion(resto, entrada)
    sol = resolver_polinomio(resto, entrada)
    if comando is None and sol.pasos and sol.pasos[0].regla == "ya_reducida" and len(sol.resultado) > 3:
        sol = replace(sol, nota=f"Si lo que querías era factorizarla, escribe «factorizar {resto}».")
    return sol


__all__ = ["resolver", "resolver_columnas", "resolver_ecuacion", "resolver_formula", "resolver_factorizacion",
           "resolver_fraccion", "resolver_polinomio", "resolver_radicales", "resolver_cuadratica",
           "es_cuadratica", "resolver_ejercicio", "Paso", "Solucion",
           "ErrorMotor", "ErrorDeEntrada", "ErrorMatematico"]
