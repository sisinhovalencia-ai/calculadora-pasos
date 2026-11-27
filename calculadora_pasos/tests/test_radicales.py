"""Pruebas de radicales: simplificar, operar, racionalizar y exponentes fraccionarios.

Se comprueba el VALOR con decimales (contra SymPy, que evalúa las raíces por su cuenta), que cada paso intermedio
valga lo mismo que lo escrito, y que el resultado final esté de verdad simplificado: ninguna raíz con un factor que
pueda salir, y ninguna raíz en un denominador.
"""

import math
import random

import pytest
import sympy as sp

from motor import ErrorDeEntrada, ErrorMatematico, resolver, resolver_ejercicio, resolver_radicales
from motor.arbol import normalizar
from motor.expr import ENum, ERad, desde_arbol
from motor.parser import parsear
from motor.radicales import _decimal, _extraer, _hijos


def decimal_de(texto: str) -> float:
    arbol, _ = parsear(texto)
    return _decimal(desde_arbol(normalizar(arbol)))


@pytest.mark.parametrize("texto, esperado, decimal", [
    ("√12", "2√3", 3.464102),
    ("√50 + √8", "7√2", 9.899495),
    ("√2 · √8", "4", None),
    ("1/√2", "√2/2", 0.707107),
    ("3/(2 + √5)", "−6 + 3√5", 0.708204),
    ("∛54", "3∛2", 3.779763),
    ("2√18 − √2", "5√2", 7.071068),
    ("√(16 + 9)", "5", None),
    ("(1 + √3)(1 − √3)", "−2", None),
    ("(2 + √3)²", "7 + 4√3", 13.928203),
    ("√75 − √12 + √27", "6√3", 10.392305),
    ("6/√3", "2√3", 3.464102),
    ("√8/√2", "2", None),
    ("(4 + 2√2)/2", "2 + √2", 3.414214),
    ("∜48", "2∜3", 2.632148),
    ("2^(1/2)", "√2", 1.414214),
    ("8^(1/3)", "2", None),
    ("27^(2/3)", "9", None),
    ("5√3 + 2√3", "7√3", 12.124356),
    ("√18/3", "√2", 1.414214),
    ("1/(√3 − √2)", "√2 + √3", 3.146264),
    ("2/(√5 + 1)", "(√5 − 1)/2", 0.618034),
    ("√3/(√3 + 1)", "(3 − √3)/2", 0.633975),
    ("1/∛2", "∛4/2", 0.793701),
    ("5/(2√3)", "5√3/6", 1.443376),
    ("√2 + √3", "√2 + √3", 3.146264),
    ("(√2 + 1)(√2 − 1)", "1", None),
    ("2√3 − 2√3", "0", None),
    ("√48/√3", "4", None),
    ("∛16 + ∛2", "3∛2", 3.779763),
    ("√(9/2)", "3√2/2", 2.121320),
])
def test_resultados(texto, esperado, decimal):
    sol = resolver_ejercicio(texto)
    assert sol.resultado == esperado, (texto, sol.resultado)
    if decimal is None:
        assert sol.resultado_decimal is None            # un entero no necesita decimales
    else:
        assert sol.resultado_decimal and abs(float(sol.resultado_decimal) - decimal) < 1e-5
        assert sol.decimal_exacto is False
    assert sol.tipo in ("radicales", "aritmetica")


def test_pasos_de_sacar_de_la_raiz():
    sol = resolver_radicales("√12")
    assert [p.regla for p in sol.pasos] == ["simplificar_raiz"]
    assert "12 = 2²·3" in sol.pasos[0].explicacion and sol.pasos[0].expresion == "2√3"
    sol = resolver_radicales("√50 + √8")
    assert [p.regla for p in sol.pasos] == ["simplificar_raiz", "simplificar_raiz", "combinar"]
    assert sol.pasos[0].expresion == "5√2 + √8" and sol.pasos[2].expresion == "7√2"


def test_pasos_de_racionalizar():
    sol = resolver_radicales("1/√2")
    assert sol.pasos[0].regla == "racionalizar" and "multiplicamos el numerador y el denominador por √2" in sol.pasos[0].explicacion
    conj = resolver_radicales("3/(2 + √5)")
    assert "conjugado" in conj.pasos[0].explicacion and "2 − √5" in conj.pasos[0].explicacion


def test_exponente_fraccionario_es_una_raiz():
    assert resolver_radicales("2^(1/2)").pasos[0].regla == "exponente_fraccionario"
    assert [p.regla for p in resolver_radicales("8^(1/3)").pasos] == ["exponente_fraccionario", "simplificar_raiz"]


def test_aritmetica_exacta_con_exponentes_fraccionarios():
    assert resolver("8^(1/3)").resultado == "2"
    assert resolver("27^(2/3)").resultado == "9"
    assert resolver("4^(−1/2)").resultado == "1/2"
    assert resolver("(−8)^(1/3)").resultado == "−2"
    assert "raíz" in resolver("16^(1/4)").pasos[0].explicacion
    for texto in ["2^(1/2)", "2^(1/5)", "(−4)^(1/2)", "0^(−1/2)"]:
        with pytest.raises(ErrorMatematico):
            resolver(texto)


def test_despachador_manda_las_raices_no_exactas_a_radicales():
    assert resolver_ejercicio("√12").tipo == "radicales"
    assert resolver_ejercicio("√49").tipo == "aritmetica"
    assert resolver_ejercicio("simplificar √12").resultado == "2√3"
    assert resolver_ejercicio("2 + 3 × 4").tipo == "aritmetica"
    with pytest.raises(ErrorMatematico):
        resolver_ejercicio("√(−4)")


@pytest.mark.parametrize("texto", ["", "5 + 3", "x + √2"])
def test_errores(texto):
    with pytest.raises((ErrorDeEntrada, ErrorMatematico)):
        resolver_radicales(texto)


# ---------------------------------------------------------------------------
# Al azar, contra SymPy
# ---------------------------------------------------------------------------

def _termino(rng):
    n, m = rng.randint(2, 75), rng.randint(2, 75)
    c, a, b = rng.randint(1, 6), rng.randint(1, 9), rng.randint(1, 6)
    t = rng.random()
    if t < 0.35:
        return f"{c}√{n}", f"{c}*sqrt({n})"
    if t < 0.45:
        return f"√{n}·√{m}", f"sqrt({n})*sqrt({m})"
    if t < 0.55:
        return f"{a}/√{n}", f"{a}/sqrt({n})"
    if t < 0.65:
        return f"{a}/({b} + √{n})", f"{a}/({b} + sqrt({n}))"
    if t < 0.72:
        return (f"{a}/(√{n} − √{m})", f"{a}/(sqrt({n}) - sqrt({m}))") if n != m else (f"{a}/√{n}", f"{a}/sqrt({n})")
    if t < 0.80:
        return f"({b} + √{n})²", f"({b} + sqrt({n}))**2"
    if t < 0.88:
        return f"({b} + √{n})(√{m} − {a})", f"({b} + sqrt({n}))*(sqrt({m}) - {a})"
    if t < 0.94:
        return f"∛{n}", f"{n}**(1/3)"
    return f"({a} + {c}√{n})/{b + 1}", f"({a} + {c}*sqrt({n}))/{b + 1}"


def _expresion(rng):
    t1, s1 = _termino(rng)
    texto, oraculo = t1, s1
    for _ in range(rng.randint(0, 2)):
        t, s = _termino(rng)
        op = rng.choice(["+", "−"])
        texto += f" {op} {t}" if op == "+" else f" − ({t})"
        oraculo += f" {'+' if op == '+' else '-'} ({s})"
    return texto, oraculo


def _radicales_irreducibles(e) -> bool:
    if isinstance(e, ERad) and isinstance(e.rad, ENum) and e.rad.v.denominator == 1:
        if _extraer(int(e.rad.v), e.indice)[0] != 1:
            return False
    return all(_radicales_irreducibles(h) for h in _hijos(e))


def test_azar_contra_sympy_y_pasos():
    rng = random.Random(2026)
    hechas = 0
    for _ in range(400):
        texto, oraculo = _expresion(rng)
        esperado = float(sp.sympify(oraculo).evalf(30))
        sol = resolver_ejercicio(texto)
        assert math.isclose(decimal_de(sol.resultado), esperado, rel_tol=1e-9, abs_tol=1e-9), (texto, sol.resultado)
        for p in sol.pasos:
            assert math.isclose(decimal_de(p.expresion), esperado, rel_tol=1e-9, abs_tol=1e-9), \
                f"{texto!r}: el paso {p.numero} ({p.expresion!r})"
            if p.operacion:
                assert p.operacion in p.explicacion, (texto, p.operacion, p.explicacion)
        if sol.tipo == "radicales":
            arbol, _ = parsear(sol.resultado)
            final = desde_arbol(normalizar(arbol))
            assert _radicales_irreducibles(final), f"{texto!r} → {sol.resultado}: queda un factor que puede salir de la raíz"
            assert sol.nota == "", f"{texto!r} → {sol.resultado}: {sol.nota}"
        assert all(p.explicacion and p.motivo and p.latex for p in sol.pasos)
        hechas += 1
    assert hechas == 400
