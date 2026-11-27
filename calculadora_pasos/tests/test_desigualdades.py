"""Pruebas de las desigualdades lineales (<, >, ≤, ≥).

El punto delicado es el SENTIDO del símbolo: se invierte al dividir entre un negativo y al
leer la desigualdad al revés. Aquí se comprueba contra la solución calculada por separado.
"""

import random
import re
from fractions import Fraction

import pytest

from motor import ErrorDeEntrada, ErrorMatematico, resolver_ecuacion, resolver_ejercicio
from tests.test_ecuaciones import _lado

INVERSA = {"<": ">", ">": "<", "≤": "≥", "≥": "≤"}


def leer(resultado: str):
    """'x ≤ −3' -> ('≤', Fraction(-3))."""
    m = re.fullmatch(r"x (<|>|≤|≥) (.+)", resultado)
    assert m, resultado
    return m.group(1), Fraction(m.group(2).replace("−", "-"))


@pytest.mark.parametrize("texto, esperado", [
    ("2x + 3 < 11", ("<", 4)),
    ("2x + 3 ≤ 11", ("≤", 4)),
    ("2x + 3 > 11", (">", 4)),
    ("2x + 3 ≥ 11", ("≥", 4)),
    ("2x + 3 <= 11", ("≤", 4)),                 # ASCII
    ("2x + 3 >= 11", ("≥", 4)),
    ("−2x + 1 ≥ 7", ("≤", -3)),                 # dividir entre un negativo invierte el símbolo
    ("−x > 4", ("<", -4)),
    ("−3x < 6", (">", -2)),
    ("x + 1 > 3x − 5", ("<", 3)),               # la x queda a la derecha: al leer al revés se invierte
    ("3(x − 1) > 2x + 4", (">", 7)),
    ("x/2 − 1 ≤ 3", ("≤", 8)),
    ("5 < 2x + 1", (">", 2)),                   # x a la derecha desde el inicio
    ("11 ≥ 2x + 3", ("≤", 4)),
    ("x ≥ 3", ("≥", 3)),
    ("3 < x", (">", 3)),
    ("2x ≤ 5", ("≤", Fraction(5, 2))),
    ("0.5x + 1 > 3", (">", 4)),
    ("−x/2 ≥ 3", ("≤", -6)),
])
def test_soluciones(texto, esperado):
    rel, valor = leer(resolver_ecuacion(texto).resultado)
    assert (rel, valor) == (esperado[0], Fraction(esperado[1]))


def test_tipo_y_nota_con_intervalo():
    sol = resolver_ecuacion("2x + 3 < 11")
    assert sol.tipo == "desigualdad_lineal" and sol.resultado == "x < 4"
    assert "(−∞, 4)" in sol.nota and "el 4 no cuenta" in sol.nota
    assert "[−3" not in resolver_ecuacion("−2x + 1 ≥ 7").nota
    assert "(−∞, −3]" in resolver_ecuacion("−2x + 1 ≥ 7").nota and "sí cuenta" in resolver_ecuacion("−2x + 1 ≥ 7").nota
    assert "(3, +∞)" in resolver_ecuacion("x > 3").nota
    assert "[3, +∞)" in resolver_ecuacion("x ≥ 3").nota
    assert resolver_ecuacion("2x + 3 = 11").tipo == "ecuacion_lineal"


def test_el_cambio_de_sentido_se_explica():
    sol = resolver_ecuacion("−2x + 1 ≥ 7")
    despejar = [p for p in sol.pasos if p.regla == "despejar"][0]
    assert "el sentido de la desigualdad se invierte (≥ pasa a ≤)" in despejar.explicacion
    assert despejar.intermedio == "(−2x) ÷ (−2) ≤ 6 ÷ (−2)"
    assert despejar.expresion == "x ≤ −3"
    # con un positivo NO se invierte
    sin = [p for p in resolver_ecuacion("2x + 3 < 11").pasos if p.regla == "despejar"][0]
    assert "invierte" not in sin.explicacion and sin.expresion == "x < 4"


def test_leer_al_reves_invierte_el_simbolo():
    sol = resolver_ecuacion("x + 1 > 3x − 5")
    ultimo = [p for p in sol.pasos if p.regla == "intercambiar"][0]
    assert ultimo.expresion == "x < 3"
    assert "se da vuelta y pasa a <" in ultimo.explicacion


def test_la_comprobacion_prueba_la_frontera_y_un_numero_de_la_solucion():
    est = resolver_ecuacion("2x + 3 < 11").pasos[-1]
    assert est.regla == "comprobar" and "NO es solución" in est.explicacion and "x = 3" in est.explicacion
    inc = resolver_ecuacion("2x + 3 ≤ 11").pasos[-1]
    assert "SÍ es solución" in inc.explicacion


@pytest.mark.parametrize("texto, esperado", [
    ("2x + 3 > 2x + 1", "Todos los números reales"),
    ("x + 1 ≥ x + 1", "Todos los números reales"),
    ("2x + 3 < 2x + 1", "Sin solución"),
    ("x + 1 > x + 2", "Sin solución"),
    ("x ≤ x", "Todos los números reales"),
    ("x < x", "Sin solución"),
])
def test_sin_solucion_y_todos_los_reales(texto, esperado):
    assert resolver_ecuacion(texto).resultado == esperado


def test_despachador():
    assert resolver_ejercicio("2x + 3 < 11").tipo == "desigualdad_lineal"
    assert resolver_ejercicio("x ≥ 3").tipo == "desigualdad_lineal"
    assert resolver_ejercicio("2x + 3 = 11").tipo == "ecuacion_lineal"


@pytest.mark.parametrize("texto", [
    "2x + 3 <", "< 5", "1 < x < 5", "x < 3 > 1", "x =< 3", "x <= = 3", "x => 3", "x < 3 = 5",
    "2 < 3", "x + y < 3", "(x + 1 < 3", "x < y",
])
def test_errores_de_entrada(texto):
    with pytest.raises(ErrorDeEntrada) as e:
        resolver_ecuacion(texto)
    assert str(e.value)


@pytest.mark.parametrize("texto", ["x² < 4", "3/x > 2", "2^x ≥ 8"])
def test_errores_matematicos(texto):
    with pytest.raises(ErrorMatematico):
        resolver_ecuacion(texto)


def test_azar_contra_la_solucion_calculada_aparte():
    rng = random.Random(77)
    revisadas = distintos = 0
    for _ in range(1500):
        tI, aL, bL = _lado(rng)
        tD, aR, bR = _lado(rng)
        rel = rng.choice(["<", ">", "≤", "≥"])
        texto = f"{tI} {rel} {tD}"
        if "x" not in texto:
            with pytest.raises(ErrorDeEntrada):
                resolver_ecuacion(texto)
            continue
        sol = resolver_ecuacion(texto)
        c, d = aL - aR, bR - bL
        if c == 0:
            cumple = {"<": bL < bR, ">": bL > bR, "≤": bL <= bR, "≥": bL >= bR}[rel]
            assert sol.resultado == ("Todos los números reales" if cumple else "Sin solución"), texto
            continue
        rel_final = rel if c > 0 else INVERSA[rel]
        assert leer(sol.resultado) == (rel_final, d / c), f"{texto!r}: motor={sol.resultado} esperado=x {rel_final} {d / c}"
        # cada paso intermedio debe tener la MISMA solución, con el mismo sentido
        for p in sol.pasos:
            for linea in (p.expresion, p.intermedio):
                if linea and "x" in linea:
                    assert resolver_ecuacion(linea).resultado == sol.resultado, f"{texto!r}: {linea!r} cambió la solución"
            if p.operacion:
                assert p.operacion in p.explicacion
        assert sol.nota and sol.pasos[-1].regla == "comprobar"
        revisadas += 1
        if c < 0:
            distintos += 1
    assert revisadas > 1000 and distintos > 200     # y se probó muchas veces el cambio de sentido
