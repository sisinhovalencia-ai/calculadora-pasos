"""Pruebas de fracciones algebraicas: simplificar, sumar, restar, multiplicar y dividir.

Se comprueba contra SymPy (`cancel`) y que el resultado quede de verdad SIMPLIFICADO
(numerador y denominador sin factores comunes); cada paso, vuelto a leer, debe valer lo mismo que lo escrito.
"""

import random

import pytest
import sympy as sp

from motor import ErrorDeEntrada, ErrorMatematico, resolver_ejercicio, resolver_fraccion
from motor.arbol import normalizar
from motor.expr import EFrac, a_sympy, desde_arbol, desde_sympy, txt
from motor.parser import parsear


def sympy_de(texto: str):
    arbol, _ = parsear(texto, variables=True)
    return a_sympy(desde_arbol(normalizar(arbol)), {})


def iguales(a, b) -> bool:
    return sp.cancel(sp.together(a - b)) == 0


@pytest.mark.parametrize("texto, esperado", [
    ("(x² − 9)/(x − 3)", "x + 3"),
    ("(x² − 5x + 6)/(x² − 4)", "(x − 3)/(x + 2)"),
    ("(2x + 4)/6", "(x + 2)/3"),
    ("(x² + 1)/(x + 1)", "(x² + 1)/(x + 1)"),
    ("x/x²", "1/x"),
    ("(6x²y)/(9xy²)", "2x/(3y)"),
    ("(x² − 4)/(x² − 4x + 4)", "(x + 2)/(x − 2)"),
    ("(a² − b²)/(a + b)", "a − b"),
    ("1/(x − 1) + 1/(x + 1)", "2x/((x − 1)(x + 1))"),
    ("(x + 1)/(x − 1) − 2/(x + 1)", "(x² + 3)/((x − 1)(x + 1))"),
    ("1/x + 1/y", "(x + y)/(xy)"),
    ("x/(x² − 9) + 3/(x² − 9)", "1/(x − 3)"),
    ("2/x − 3/x", "−1/x"),
    ("1/x − 1/x", "0"),
    ("(x² − 4)/(x + 1) · (x + 1)/(x − 2)", "x + 2"),
    ("(x + 1)/(x − 1) · (x − 1)/(x + 2)", "(x + 1)/(x + 2)"),
    ("((x + 1)/(x − 1)) ÷ ((x + 2)/(x − 1))", "(x + 1)/(x + 2)"),
    ("x/(x + 1) · (x + 1)/x", "1"),
    ("(x² − 1)/(x − 1) + 1", "x + 2"),
])
def test_resultados(texto, esperado):
    sol = resolver_fraccion(texto)
    assert iguales(sympy_de(sol.resultado), sympy_de(esperado)), (sol.resultado, esperado)
    assert sol.tipo == "fraccion_algebraica"


@pytest.mark.parametrize("texto, esperado", [
    ("(x² − 9)/(x − 3)", "x + 3"),
    ("1/(x − 1) + 1/(x + 1)", "2x/((x − 1)(x + 1))"),
    ("(x + 1)/(x − 1) · (x − 1)/(x + 2)", "(x + 1)/(x + 2)"),
])
def test_forma_exacta_de_algunos(texto, esperado):
    assert resolver_fraccion(texto).resultado == esperado


def test_pasos_de_simplificar():
    sol = resolver_fraccion("(x² − 9)/(x − 3)")
    assert [p.regla for p in sol.pasos] == ["factorizar_num", "cancelar"]
    assert sol.pasos[0].expresion in ("(x − 3)(x + 3)/(x − 3)", "((x − 3)(x + 3))/(x − 3)")
    assert "diferencia de cuadrados" in sol.pasos[0].explicacion
    assert "(x − 3)" in sol.pasos[1].explicacion and sol.pasos[1].expresion == "x + 3"


def test_pasos_de_una_suma():
    sol = resolver_fraccion("1/(x − 1) + 1/(x + 1)")
    reglas = [p.regla for p in sol.pasos]
    assert reglas[:3] == ["denominador_comun", "sumar_numeradores", "operar_numerador"]
    assert "(x − 1)(x + 1)" in sol.pasos[0].explicacion
    resta = resolver_fraccion("(x + 1)/(x − 1) − 2/(x + 1)")
    assert "afecta a todo el numerador" in [p for p in resta.pasos if p.regla == "sumar_numeradores"][0].explicacion


def test_restricciones():
    nota = resolver_fraccion("(x² − 9)/(x − 3)").nota
    assert "x ≠ 3" in nota and "−3" not in nota                 # solo el denominador manda: x = −3 sí se puede
    assert "x ≠ 1" in resolver_fraccion("1/(x − 1) + 1/(x + 1)").nota
    assert "a + b ≠ 0" in resolver_fraccion("(a² − b²)/(a + b)").nota
    nota = resolver_fraccion("((x + 1)/(x − 1)) ÷ ((x + 2)/(x − 1))").nota
    assert "x ≠ 1" in nota and "x ≠ −2" in nota                  # también el divisor no puede valer 0
    assert resolver_fraccion("(2x + 4)/6").nota == ""            # denominador numérico: sin restricciones


def test_ya_simplificada():
    assert resolver_fraccion("(x² + 1)/(x + 1)").pasos[-1].regla == "ya_simplificada"


def test_despachador():
    assert resolver_ejercicio("(x² − 9)/(x − 3)").tipo == "fraccion_algebraica"
    assert resolver_ejercicio("simplificar (x² − 9)/(x − 3)").resultado == "x + 3"
    assert resolver_ejercicio("simplificar 6/9").resultado == "2/3"           # sin letras es aritmética
    assert resolver_ejercicio("1/x + 1/y").tipo == "fraccion_algebraica"


@pytest.mark.parametrize("texto", ["", "x²", "x/y = 2", "1/√x"])
def test_errores(texto):
    with pytest.raises((ErrorDeEntrada, ErrorMatematico)):
        resolver_fraccion(texto)


# ---------------------------------------------------------------------------
# Al azar
# ---------------------------------------------------------------------------

def _lineal(rng, x):
    return rng.choice([1, 1, 2, 3]) * x + rng.choice([-1, 1]) * rng.randint(1, 6)


def _poli_azar(rng, x, y):
    t = rng.random()
    if t < 0.5:
        return _lineal(rng, x)
    if t < 0.7:
        return x ** 2 + rng.choice([-1, 1]) * rng.randint(1, 9)
    if t < 0.85:
        return _lineal(rng, x) * _lineal(rng, x)
    return x + rng.choice([-1, 1]) * y


def _texto(P, orden):
    return txt(desde_sympy(sp.expand(P), orden))


def _simplificado(texto_resultado: str) -> bool:
    """El numerador y el denominador del resultado no tienen ningún factor en común."""
    arbol, _ = parsear(texto_resultado, variables=True)
    e = desde_arbol(normalizar(arbol))
    if not isinstance(e, EFrac):
        return True
    n, d = sp.expand(a_sympy(e.num, {})), sp.expand(a_sympy(e.den, {}))
    return sp.gcd(n, d) == 1 or not (n.free_symbols and d.free_symbols)


def _caso_azar(rng):
    x, y = sp.symbols("x y")
    orden = {"x": 0, "y": 1}
    comun = _poli_azar(rng, x, y)
    t = rng.random()
    if t < 0.40:                                              # una fracción con un factor común
        N, D = comun * _poli_azar(rng, x, y), comun * _poli_azar(rng, x, y)
        return f"({_texto(N, orden)})/({_texto(D, orden)})"
    if t < 0.70:                                              # suma o resta de dos fracciones
        d1, d2 = _poli_azar(rng, x, y), _poli_azar(rng, x, y)
        if rng.random() < 0.4:
            d2 = d1 * _poli_azar(rng, x, y)
        n1, n2 = _poli_azar(rng, x, y), rng.randint(1, 5)
        op = rng.choice(["+", "−"])
        return f"({_texto(n1, orden)})/({_texto(d1, orden)}) {op} {n2}/({_texto(d2, orden)})"
    a, b, c = _poli_azar(rng, x, y), _poli_azar(rng, x, y), _poli_azar(rng, x, y)
    return f"({_texto(a * comun, orden)})/({_texto(b, orden)}) · ({_texto(c, orden)})/({_texto(comun, orden)})"


def test_azar_contra_sympy():
    rng = random.Random(2026)
    resueltas = 0
    for _ in range(300):
        texto = _caso_azar(rng)
        try:
            sol = resolver_fraccion(texto)
        except ErrorMatematico as e:
            assert "dividir entre cero" in str(e), (texto, str(e))
            continue
        original = sympy_de(texto)
        assert iguales(sympy_de(sol.resultado), original), f"{texto!r} → {sol.resultado}"
        assert _simplificado(sol.resultado), f"{texto!r} → {sol.resultado} no está simplificada"
        for p in sol.pasos:
            assert iguales(sympy_de(p.expresion), original), f"{texto!r}: el paso {p.numero} ({p.expresion!r})"
            if p.operacion:
                assert p.operacion in p.explicacion, (texto, p.operacion, p.explicacion)
        assert all(p.explicacion and p.motivo for p in sol.pasos)
        resueltas += 1
    assert resueltas > 250
