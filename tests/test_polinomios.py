"""Pruebas de polinomios y productos notables.

  1. Casos fijos con el resultado de un libro de texto.
  2. Cada producto notable se reconoce con su nombre y su fórmula.
  3. Expresiones al azar comparadas con SymPy y con evaluación numérica.
"""

import random

import pytest
import sympy as sp

from motor import ErrorDeEntrada, ErrorMatematico, resolver_ejercicio, resolver_polinomio
from motor.arbol import normalizar
from motor.expr import a_sympy, desde_arbol
from motor.parser import parsear


def valor_sympy(texto: str):
    arbol, _ = parsear(texto, variables=True)
    return a_sympy(desde_arbol(normalizar(arbol)), {})


@pytest.mark.parametrize("texto, esperado", [
    ("(x + 3)²", "x² + 6x + 9"),
    ("(x − 3)²", "x² − 6x + 9"),
    ("(2x − 5)²", "4x² − 20x + 25"),
    ("(a + b)³", "a³ + 3a²b + 3ab² + b³"),
    ("(x − 2)³", "x³ − 6x² + 12x − 8"),
    ("(x − 2)^4", "x^4 − 8x³ + 24x² − 32x + 16"),
    ("(2x + 3)(2x − 3)", "4x² − 9"),
    ("(a + b)(a − b)", "a² − b²"),
    ("(x + 2)(x + 5)", "x² + 7x + 10"),
    ("(x − 4)(x + 7)", "x² + 3x − 28"),
    ("(x + y + 1)²", "x² + 2xy + y² + 2x + 2y + 1"),
    ("(2x + 3)(x − 5)", "2x² − 7x − 15"),
    ("(3x² + 2x − 1) + (x² − 5x + 4)", "4x² − 3x + 3"),
    ("(3x² + 2x) − (x² − 5x)", "2x² + 7x"),
    ("2(x + 3) − 4(x − 1)", "−2x + 10"),
    ("3x + 2x − 7 + 4", "5x − 3"),
    ("x(x + 1)(x − 1)", "x³ − x"),
    ("(x + 1)(x² − x + 1)", "x³ + 1"),
    ("x²", "x²"),
    ("(x/2 + 1)²", "x²/4 + x + 1"),
    ("(x + 1)/2 + (x − 1)/3", "5x/6 + 1/6"),
    ("−(x − 3)", "3 − x"),
])
def test_resultados(texto, esperado):
    sol = resolver_polinomio(texto)
    assert sp.expand(valor_sympy(sol.resultado) - valor_sympy(esperado)) == 0, (sol.resultado, esperado)


@pytest.mark.parametrize("texto, esperado", [
    ("(x + 3)²", "x² + 6x + 9"), ("(a + b)³", "a³ + 3a²b + 3ab² + b³"), ("(x + 2)(x + 5)", "x² + 7x + 10"),
    ("(2x + 3)(2x − 3)", "4x² − 9"), ("(3x² + 2x) − (x² − 5x)", "2x² + 7x"),
])
def test_forma_exacta_del_resultado(texto, esperado):
    assert resolver_polinomio(texto).resultado == esperado


@pytest.mark.parametrize("texto, nombre", [
    ("(x + 3)²", "el cuadrado de un binomio"),
    ("(2x − 5)²", "el cuadrado de un binomio"),
    ("(x + 3)(x + 3)", "el cuadrado de un binomio"),
    ("(a + b)³", "el cubo de un binomio"),
    ("(x − 2)^4", "un binomio elevado a una potencia"),
    ("(x + y + 1)²", "el cuadrado de un trinomio"),
    ("(2x + 3)(2x − 3)", "la suma por la diferencia"),
    ("(3 − x)(3 + x)", "la suma por la diferencia"),
    ("(x + 2)(x + 5)", "el producto de binomios con un término común"),
    ("(x − 4)(x + 7)", "el producto de binomios con un término común"),
])
def test_producto_notable_reconocido(texto, nombre):
    sol = resolver_polinomio(texto)
    assert sol.pasos[0].regla == "producto_notable"
    assert nombre in sol.pasos[0].explicacion
    assert "Fórmula usada" in sol.nota and sol.pasos[0].intermedio       # la fórmula, en gris


def test_pasos_de_un_cuadrado_de_binomio():
    sol = resolver_polinomio("(2x + 3)²")
    assert [p.regla for p in sol.pasos] == ["producto_notable", "reducir"]
    assert sol.pasos[0].expresion == "(2x)² + 2·(2x)·3 + 3²"
    assert sol.pasos[0].intermedio == "(a + b)² = a² + 2ab + b²"
    assert "a = 2x y b = 3" in sol.pasos[0].explicacion
    assert sol.pasos[1].expresion == "4x² + 12x + 9"


def test_no_notable_distribuye_y_reduce():
    sol = resolver_polinomio("(2x + 3)(x − 5)")
    assert [p.regla for p in sol.pasos] == ["distribuir", "reducir"]
    assert sol.pasos[0].expresion == "2x·x − 2x·5 + 3x − 3·5"
    assert sol.nota == ""


def test_quitar_parentesis_con_signo_menos():
    sol = resolver_polinomio("(3x² + 2x) − (x² − 5x)")
    assert sol.pasos[0].regla == "quitar_parentesis"
    assert sol.pasos[0].expresion == "3x² + 2x − x² + 5x"
    assert sol.resultado == "2x² + 7x"


def test_ya_reducida():
    sol = resolver_polinomio("x² + 5x + 6")
    assert [p.regla for p in sol.pasos] == ["ya_reducida"]


def test_despachador_y_pista_de_factorizar():
    assert resolver_ejercicio("(x + 3)²").tipo == "polinomio"
    assert resolver_ejercicio("desarrollar (x + 3)²").resultado == "x² + 6x + 9"
    assert resolver_ejercicio("reducir 3x + 2x").resultado == "5x"
    sol = resolver_ejercicio("x² + 5x + 6")
    assert "factorizar x² + 5x + 6" in sol.nota
    assert resolver_ejercicio("desarrollar x² + 5x + 6").nota == ""


@pytest.mark.parametrize("texto", ["", "x/y", "1/x + 1", "√x + 1", "x = 3"])
def test_errores(texto):
    with pytest.raises((ErrorDeEntrada, ErrorMatematico)):
        resolver_polinomio(texto)


@pytest.mark.parametrize("texto", ["(x + 1)^21", "(x + y + 1)^1000", "x^99999999"])
def test_exponente_demasiado_grande_se_rechaza_rapido(texto):
    import time
    t0 = time.time()
    with pytest.raises(ErrorMatematico) as e:
        resolver_ejercicio(texto)
    assert "exponente máximo" in str(e.value) and time.time() - t0 < 1
    assert resolver_polinomio("(x + 1)^20").resultado.startswith("x^20 + 20x^19")      # el límite en sí sí se permite


def test_a_dict_serializable():
    import json
    datos = json.loads(json.dumps(resolver_polinomio("(x + 3)²").a_dict(), ensure_ascii=False))
    assert datos["resultado"] == "x² + 6x + 9" and datos["pasos"][0]["intermedio"]


# ---------------------------------------------------------------------------
# Al azar, contra SymPy
# ---------------------------------------------------------------------------

LET = list("abcxyz")


def _binomio(rng, letras):
    a = rng.randint(1, 5) * rng.choice([1, 1, -1])
    b = rng.randint(1, 6) * rng.choice([1, -1])
    return f"{a}{rng.choice(letras)} {'+' if b > 0 else '−'} {abs(b)}" if a != 1 else \
        f"{rng.choice(letras)} {'+' if b > 0 else '−'} {abs(b)}"


def _expresion(rng):
    letras = rng.sample(LET, 2)
    t = rng.random()
    if t < 0.25:
        return f"({_binomio(rng, letras)})²"
    if t < 0.40:
        return f"({_binomio(rng, letras)})³"
    if t < 0.60:
        return f"({_binomio(rng, letras)})({_binomio(rng, letras)})"
    if t < 0.75:
        return f"({_binomio(rng, letras)}) − ({_binomio(rng, letras)}) + {rng.randint(1, 9)}{letras[0]}"
    if t < 0.88:
        return f"{rng.randint(2, 5)}({_binomio(rng, letras)}) − {rng.randint(2, 5)}({_binomio(rng, letras)})"
    return f"({letras[0]} + {letras[1]} + {rng.randint(1, 4)})²"


def test_azar_contra_sympy_y_pasos():
    rng = random.Random(2026)
    notables = 0
    for _ in range(500):
        texto = _expresion(rng)
        sol = resolver_polinomio(texto)
        esperado = sp.expand(valor_sympy(texto))
        assert sp.expand(valor_sympy(sol.resultado) - esperado) == 0, f"{texto!r} → {sol.resultado}"
        for p in sol.pasos:
            assert sp.expand(valor_sympy(p.expresion) - esperado) == 0, f"{texto!r}: el paso {p.numero} ({p.expresion!r})"
            if p.operacion:
                assert p.operacion in p.explicacion, (texto, p.operacion, p.explicacion)
        assert all(p.explicacion and p.motivo and p.latex for p in sol.pasos)
        notables += sol.pasos[0].regla == "producto_notable"
    assert notables > 150
