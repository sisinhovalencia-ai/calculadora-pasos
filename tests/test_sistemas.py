"""Pruebas de sistemas lineales 2×2 y del despacho por separadores."""

import random
import re

import pytest
import sympy as sp

from motor import ErrorDeEntrada, ErrorMatematico, resolver_ejercicio, resolver_sistema


def _resultado_par(resultado):
    pares = re.findall(r"([A-Za-z])\s*=\s*([^,]+)", resultado.replace("−", "-"))
    return {nombre: sp.sympify(valor.strip()) for nombre, valor in pares}


def test_resuelve_por_eliminacion_y_comprueba_ambas_ecuaciones():
    sol = resolver_ejercicio("2x + y = 5; x − y = 1")
    assert sol.tipo == "sistema_lineal"
    assert sol.resultado == "x = 2, y = 1"
    assert sol.pasos[0].regla == "normalizar_sistema"
    assert any(p.regla == "eliminar_variable" for p in sol.pasos)
    assert sol.pasos[-1].regla == "comprobar_sistema"
    assert "ambas ecuaciones originales" in sol.nota


def test_acepta_ecuaciones_en_lineas_separadas():
    sol = resolver_sistema("x + y = 7\n2x − y = 2")
    assert sol.resultado == "x = 3, y = 4"


@pytest.mark.parametrize("texto, esperado", [
    ("x + y = 2; 2x + 2y = 4", "Infinitas soluciones"),
    ("x + y = 2; 2x + 2y = 5", "Sin solución"),
])
def test_clasifica_sistemas_singulares(texto, esperado):
    sol = resolver_sistema(texto)
    assert sol.resultado == esperado
    assert sol.pasos[-1].regla in {"infinitas_soluciones", "sin_solucion"}


def test_sistema_con_una_variable_en_cada_ecuacion():
    sol = resolver_sistema("x = 3; x + y = 8")
    assert sol.resultado == "x = 3, y = 5"


@pytest.mark.parametrize("texto", [
    "x + y = 1", "x + y = 1; x − y = 2; x = 0", "x + y = 1; ",
    "x² + y = 1; x − y = 0", "x + y + z = 1; x − y + z = 0",
])
def test_rechaza_sistemas_fuera_del_alcance_actual(texto):
    with pytest.raises((ErrorDeEntrada, ErrorMatematico)):
        resolver_sistema(texto)


def test_despachador_no_confunde_una_igualdad_sola_con_sistema():
    assert resolver_ejercicio("2x + 3 = 11").tipo == "ecuacion_lineal"


def test_sistemas_aleatorios_unicos_contra_sympy():
    azar = random.Random(202611)
    x, y = sp.symbols("x y")
    for _ in range(30):
        while True:
            a, b, c, d = (azar.randint(-5, 5) for _ in range(4))
            if a * d - b * c:
                break
        xv, yv = azar.randint(-6, 6), azar.randint(-6, 6)
        r1, r2 = a * xv + b * yv, c * xv + d * yv
        texto = f"({a})x + ({b})y = {r1}; ({c})x + ({d})y = {r2}"
        sol = resolver_sistema(texto)
        obtenidas = _resultado_par(sol.resultado)
        esperadas = {"x": sp.Integer(xv), "y": sp.Integer(yv)}
        assert obtenidas == esperadas
