"""Pruebas de la factorización por casos.

  1. Casos fijos, con el resultado de un libro de texto y el caso que se usó.
  2. Los pasos de los casos largos (trinomio ax² + bx + c, agrupación).
  3. Polinomios armados multiplicando factores al azar: deben factorizarse COMPLETOS (cada factor irreducible),
     el producto debe dar el polinomio original y cada paso debe conservarlo.
"""

import random

import pytest
import sympy as sp

from motor import ErrorDeEntrada, ErrorMatematico, resolver_ejercicio, resolver_factorizacion
from motor.arbol import normalizar
from motor.expr import ENeg, EPot, EProd, a_sympy, desde_arbol, desde_sympy, txt
from motor.factorizacion import _irreducible
from motor.parser import parsear


def _factores(e):
    """Los factores «de verdad» de un producto: sin el signo menos, aplanando productos y quitando exponentes."""
    if isinstance(e, ENeg):
        return _factores(e.x)
    if isinstance(e, EProd):
        return [g for f in e.factores for g in _factores(f)]
    if isinstance(e, EPot):
        return _factores(e.base)
    return [e]


def sympy_de(texto: str):
    arbol, _ = parsear(texto, variables=True)
    return a_sympy(desde_arbol(normalizar(arbol)), {})


@pytest.mark.parametrize("texto, esperado, caso", [
    ("x² − 9", "(x − 3)(x + 3)", "diferencia de cuadrados"),
    ("4x² − 9", "(2x − 3)(2x + 3)", "diferencia de cuadrados"),
    ("x² − y²", "(x − y)(x + y)", "diferencia de cuadrados"),
    ("a² − 4b²", "(a − 2b)(a + 2b)", "diferencia de cuadrados"),
    ("x² + 5x + 6", "(x + 2)(x + 3)", "trinomio x² + bx + c"),
    ("x² − 5x + 6", "(x − 3)(x − 2)", "trinomio x² + bx + c"),
    ("x² + x − 6", "(x − 2)(x + 3)", "trinomio x² + bx + c"),
    ("x² + 5xy + 6y²", "(x + 2y)(x + 3y)", "trinomio x² + bx + c"),
    ("x² + 6x + 9", "(x + 3)²", "trinomio cuadrado perfecto"),
    ("4x² − 12x + 9", "(2x − 3)²", "trinomio cuadrado perfecto"),
    ("9x² + 6xy + y²", "(3x + y)²", "trinomio cuadrado perfecto"),
    ("2x² + 7x + 3", "(2x + 1)(x + 3)", "trinomio ax² + bx + c"),
    ("6x² − x − 2", "(3x − 2)(2x + 1)", "trinomio ax² + bx + c"),
    ("12x² + 5x − 2", "(4x − 1)(3x + 2)", "trinomio ax² + bx + c"),
    ("3x² + 6x", "3x(x + 2)", "factor común"),
    ("−x² − 5x", "−x(x + 5)", "factor común"),
    ("−x² + 9", "−(x − 3)(x + 3)", "factor común"),
    ("2x² − 18", "2(x − 3)(x + 3)", "diferencia de cuadrados"),
    ("5x³ − 20x", "5x(x − 2)(x + 2)", "factor común"),
    ("ax + ay + bx + by", "(a + b)(x + y)", "agrupación de términos"),
    ("x³ + x² + x + 1", "(x + 1)(x² + 1)", "agrupación de términos"),
    ("x³ − 8", "(x − 2)(x² + 2x + 4)", "suma o diferencia de cubos"),
    ("x³ + 27", "(x + 3)(x² − 3x + 9)", "suma o diferencia de cubos"),
    ("8x³ − 1", "(2x − 1)(4x² + 2x + 1)", "suma o diferencia de cubos"),
    ("x³ + 3x² + 3x + 1", "(x + 1)³", "cubo perfecto de binomio"),
    ("x³ − 6x² + 12x − 8", "(x − 2)³", "cubo perfecto de binomio"),
    ("x^4 − 16", "(x − 2)(x + 2)(x² + 4)", "diferencia de cuadrados"),
    ("x^4 − 5x² + 4", "(x − 2)(x − 1)(x + 1)(x + 2)", "trinomio x² + bx + c"),
    ("x^6 − 7x³ − 8", "(x − 2)(x + 1)(x² − x + 1)(x² + 2x + 4)", "suma o diferencia de cubos"),
    ("(x + 1)² − 4", "(x − 1)(x + 3)", "trinomio x² + bx + c"),
    ("x³ − 2x² − 5x + 6", "(x − 3)(x − 1)(x + 2)", "método avanzado"),
    ("x³ + y³", "(x + y)(x² − xy + y²)", "suma o diferencia de cubos"),            # cubos CON LETRAS
    ("x³ − y³", "(x − y)(x² + xy + y²)", "suma o diferencia de cubos"),
    ("8a³ − 27b³", "(2a − 3b)(4a² + 6ab + 9b²)", "suma o diferencia de cubos"),
    ("27x³ + 8y³", "(3x + 2y)(9x² − 6xy + 4y²)", "suma o diferencia de cubos"),
    ("a³ + 3a²b + 3ab² + b³", "(a + b)³", "cubo perfecto de binomio"),
    ("x³ − 3x²y + 3xy² − y³", "(x − y)³", "cubo perfecto de binomio"),
    ("x^6 + 3x^4y² + 3x²y^4 + y^6", "(x² + y²)³", "cubo perfecto de binomio"),
])
def test_resultados_y_caso(texto, esperado, caso):
    sol = resolver_factorizacion(texto)
    assert sol.resultado == esperado
    assert caso in sol.nota and sol.tipo == "factorizacion"
    assert sol.expresion_inicial.startswith("factorizar ")


@pytest.mark.parametrize("texto", ["x² + 1", "x² + x + 1", "x² − 2", "x² + 2x + 5"])
def test_irreducibles(texto):
    sol = resolver_factorizacion(texto)
    assert [p.regla for p in sol.pasos] == ["irreducible"] and "irreducible" in sol.nota
    assert sol.resultado == texto


def test_monomio_y_ya_factorizado():
    assert resolver_factorizacion("6x²y").pasos[0].regla == "irreducible"
    assert "monomio" in resolver_factorizacion("6x²y").pasos[0].explicacion
    assert resolver_factorizacion("(x − 3)(x + 3)").resultado == "(x − 3)(x + 3)"      # se desarrolla y vuelve a factorizar


def test_pasos_trinomio_ax2_bx_c():
    sol = resolver_factorizacion("2x² + 7x + 3")
    assert [p.regla for p in sol.pasos] == ["trinomio_general_1", "trinomio_general_2", "trinomio_general_3"]
    assert sol.pasos[0].expresion == "2x² + x + 6x + 3"
    assert sol.pasos[1].expresion == "x(2x + 1) + 3(2x + 1)"
    assert sol.pasos[2].expresion == "(2x + 1)(x + 3)"
    assert "a·c = 6" in sol.pasos[0].explicacion


def test_pasos_agrupacion():
    sol = resolver_factorizacion("ax + ay + bx + by")
    assert [p.regla for p in sol.pasos if p.regla != "ordenar"] == ["agrupacion_1", "agrupacion_2"]
    assert any(p.expresion == "a(x + y) + b(x + y)" for p in sol.pasos)


def test_factor_comun_y_luego_diferencia_de_cuadrados():
    sol = resolver_factorizacion("2x² − 18")
    assert [p.regla for p in sol.pasos] == ["factor_comun", "diferencia_cuadrados"]
    assert sol.pasos[0].expresion == "2(x² − 9)" and sol.pasos[1].expresion == "2(x − 3)(x + 3)"
    assert "a² − b² = (a − b)(a + b)" == sol.pasos[1].intermedio


def test_desarrolla_antes_si_no_esta_desarrollado():
    sol = resolver_factorizacion("(x + 1)² − 4")
    assert sol.pasos[0].regla == "ordenar" and sol.pasos[0].expresion == "x² + 2x − 3"


def test_despachador():
    assert resolver_ejercicio("factorizar x² − 9").resultado == "(x − 3)(x + 3)"
    assert resolver_ejercicio("Factoriza: x² − 9").resultado == "(x − 3)(x + 3)"


@pytest.mark.parametrize("texto", ["", "5", "x/y", "√x", "x = 3"])
def test_errores(texto):
    with pytest.raises((ErrorDeEntrada, ErrorMatematico)):
        resolver_factorizacion(texto)


def test_error_sin_nada_que_factorizar_con_el_despachador():
    with pytest.raises(ErrorDeEntrada):
        resolver_ejercicio("factorizar")
    with pytest.raises(ErrorMatematico):
        resolver_ejercicio("factorizar 25")


# ---------------------------------------------------------------------------
# Al azar: se arma el polinomio multiplicando factores, y se pide factorizarlo
# ---------------------------------------------------------------------------

def _factor_azar(rng, x, y):
    t = rng.random()
    a, b = rng.randint(1, 7), rng.randint(1, 7)
    if t < 0.30:
        return x + rng.choice([-1, 1]) * a
    if t < 0.45:
        return rng.randint(2, 4) * x + rng.choice([-1, 1]) * b
    if t < 0.55:
        return x ** 2 + rng.choice([1, 2, 3, 5])                       # irreducible
    if t < 0.62:
        return x ** 2 + x + 1                                          # irreducible
    if t < 0.72:
        return x + rng.choice([-1, 1]) * y * rng.randint(1, 3)
    if t < 0.80:
        return x ** 2 + y ** 2
    if t < 0.84:
        return x
    if t < 0.89:
        return (x + rng.choice([-1, 1]) * y) ** 2                      # un cuadrado con letras adentro
    return sp.Integer(rng.choice([2, 3, 5, 6, -1, -2]))


def test_azar_se_factoriza_completo():
    rng = random.Random(2026)
    x, y = sp.symbols("x y")
    revisados = casos = 0
    for _ in range(400):
        factores = [_factor_azar(rng, x, y) for _ in range(rng.randint(2, 4))]
        P = sp.expand(sp.Mul(*factores))
        if not P.free_symbols or sp.Poly(P, x, y).total_degree() > 8:
            continue
        orden = {"x": 0, "y": 1}
        texto = txt(desde_sympy(P, orden))
        if len(texto) > 200:                                  # más largo que el límite de entrada: se rechaza
            continue
        sol = resolver_factorizacion(texto)
        assert sp.expand(sympy_de(sol.resultado) - P) == 0, f"{texto!r} → {sol.resultado}"
        e = desde_arbol(normalizar(parsear(sol.resultado, variables=True)[0]))
        for base in _factores(e):
            assert _irreducible(sp.expand(a_sympy(base, {}))), f"{texto!r}: {txt(base)} todavía se factoriza"
        for p in sol.pasos:
            assert sp.expand(sympy_de(p.expresion) - P) == 0, f"{texto!r}: el paso {p.numero} ({p.expresion!r})"
            if p.operacion:
                assert p.operacion in p.explicacion, (texto, p.operacion, p.explicacion)
        assert all(p.explicacion and p.motivo for p in sol.pasos)
        revisados += 1
        casos += len({p.regla for p in sol.pasos})
    assert revisados > 300 and casos > 600
