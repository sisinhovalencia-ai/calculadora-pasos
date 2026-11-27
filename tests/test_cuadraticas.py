"""Pruebas del solucionador cuadrático y su integración con el despachador."""

import random
import re

import pytest
import sympy as sp

from motor import ErrorDeEntrada, ErrorMatematico, resolver_cuadratica, resolver_ejercicio


def _raices_resultado(resultado: str):
    if resultado == "Sin soluciones reales":
        return []
    texto = resultado.replace("−", "-").replace(" (raíz doble)", "")
    valores = re.findall(r"(?:x₁|x₂|x)\s*=\s*([^,]+)", texto)
    return [sp.sympify(v.strip(), locals={"sqrt": sp.sqrt}) for v in valores]


@pytest.mark.parametrize("a,b,c", [
    (1, -5, 6),       # factores racionales distintos
    (1, 0, -2),       # raíces irracionales
    (1, 2, 1),        # raíz doble
    (1, 0, 1),        # sin raíces reales
    (2, 3, -2),
    (-1, 4, -3),
    (1, -2, -1),
    (2, -3, 1),
])
def test_raices_contra_sympy(a, b, c):
    x = sp.Symbol("x")
    texto = f"{a}x² + ({b})x + ({c}) = 0"
    sol = resolver_cuadratica(texto)
    esperadas = [r for r in sp.solve(a * x**2 + b * x + c, x) if r.is_real]
    obtenidas = _raices_resultado(sol.resultado)
    assert sorted(obtenidas, key=sp.default_sort_key) == sorted(esperadas, key=sp.default_sort_key)
    if esperadas:
        assert sol.pasos[-1].regla == "comprobar"
        assert "igualdad original" in sol.pasos[-1].explicacion
        assert "Sustitución verificada" in sol.nota
    else:
        assert sol.resultado == "Sin soluciones reales"
        assert sol.pasos[-1].regla == "sin_reales"


def test_usa_factorizacion_para_raices_racionales():
    sol = resolver_cuadratica("x² − 5x + 6 = 0")
    reglas = [p.regla for p in sol.pasos]
    assert any(regla.startswith("factor_") for regla in reglas)
    assert "producto_cero" in reglas
    assert sol.resultado == "x₁ = 2, x₂ = 3"
    assert sol.tipo == "ecuacion_cuadratica"


def test_normaliza_ambos_lados_y_acepta_otra_variable():
    sol = resolver_ejercicio("2y² + 1 = 3y")
    assert sol.tipo == "ecuacion_cuadratica"
    assert sol.expresion_inicial == "2y² + 1 = 3y"
    assert sol.resultado == "y₁ = 1/2, y₂ = 1"


def test_despachador_conserva_ecuaciones_lineales():
    assert resolver_ejercicio("2x + 3 = 11").tipo == "ecuacion_lineal"


def test_una_ecuacion_de_grado_mayor_que_dos_sigue_mostrando_error_claro():
    with pytest.raises(ErrorMatematico, match="no es lineal"):
        resolver_ejercicio("x³ − 1 = 0")


def test_rechaza_mas_de_una_incognita():
    with pytest.raises(ErrorDeEntrada):
        resolver_ejercicio("x² + y² = 1")


def test_dominio_con_terminos_racionales():
    sol = resolver_ejercicio("(x² − 1)/2 = 4")
    assert _raices_resultado(sol.resultado) == [-3, 3]


def test_casos_aleatorios_contra_sympy():
    azar = random.Random(202604)
    x = sp.Symbol("x")
    for _ in range(30):
        a = azar.choice([-4, -3, -2, -1, 1, 2, 3, 4])
        b = azar.randint(-8, 8)
        c = azar.randint(-8, 8)
        texto = f"({a})x² + ({b})x + ({c}) = 0"
        sol = resolver_cuadratica(texto)
        esperadas = [r for r in sp.solve(a * x**2 + b * x + c, x) if r.is_real]
        obtenidas = _raices_resultado(sol.resultado)
        assert sorted(obtenidas, key=sp.default_sort_key) == sorted(esperadas, key=sp.default_sort_key), texto
