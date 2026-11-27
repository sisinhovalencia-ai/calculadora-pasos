"""Pruebas del Formulario: catálogo de fórmulas, despejes y cálculo con números.

La prueba fuerte: para CADA fórmula y CADA letra, con números al azar, la respuesta tiene que CUMPLIR la fórmula original
(se comprueba con SymPy, por un camino distinto al del motor).
"""

import random
import re
from fractions import Fraction

import pytest
import sympy as sp

from motor import ErrorDeEntrada, ErrorMatematico
from motor.arbol import normalizar
from motor.expr import a_sympy, desde_arbol
from motor.formulario import FORMULAS, PI_APROX, TEMAS, TEMA_DE, calcular, despejar, formula
from motor.parser import parsear


def _a_fraccion(texto: str) -> Fraction:
    return Fraction(texto.replace("−", "-").replace(",", "."))


def _sympy_de(texto: str):
    arbol, _ = parsear(texto, variables=True)
    return a_sympy(desde_arbol(normalizar(arbol)), {})


# ---------------------------------------------------------------------------
# El catálogo
# ---------------------------------------------------------------------------

def test_el_catalogo_es_coherente():
    assert len(FORMULAS) >= 25 and len(TEMAS) >= 5
    assert len({f.id for t in TEMAS for f in t.formulas}) == len(FORMULAS)              # ids únicos
    for f in FORMULAS.values():
        izq, der = f.expresion.split("=")
        letras = {c for c in f.expresion if c.isalpha() and c != "π"}
        assert letras == {v.letra for v in f.variables}, f"{f.id}: las letras de la fórmula no son las que se explican"
        assert len({v.letra for v in f.variables}) == len(f.variables)
        assert all(v.nombre and v.unidad for v in f.variables) and f.nombre
        assert TEMA_DE[f.id].formulas.count(f) == 1


def test_todas_las_letras_de_todas_las_formulas_se_pueden_despejar():
    total = 0
    for f in FORMULAS.values():
        for v in f.variables:
            sol = despejar(f.id, v.letra)
            assert sol.resultado.startswith(f"{v.letra} = ") and sol.pasos, (f.id, v.letra)
            total += 1
    assert total >= 90


# ---------------------------------------------------------------------------
# Calcular con números
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("id_formula, objetivo, valores, esperado", [
    ("velocidad", "t", {"d": "20", "v": "4"}, "5"),
    ("velocidad", "v", {"d": "100", "t": "8"}, "25/2"),
    ("ohm", "I", {"V": "12", "R": "4"}, "3"),
    ("ohm", "R", {"V": "9", "I": "1/2"}, "18"),
    ("peso", "P", {"m": "70", "g": "9,8"}, "686"),
    ("newton", "a", {"F": "30", "m": "6"}, "5"),
    ("area_circulo", "r", {"A": "25"}, "±"),
    ("energia_cinetica", "v", {"K": "100", "m": "2"}, "±10"),
    ("fahrenheit", "C", {"F": "98.6"}, "37"),
    ("fahrenheit", "F", {"C": "100"}, "212"),
    ("monto", "C", {"M": "1050", "r": "0.05", "t": "1"}, "1000"),
    ("utilidad", "q", {"U": "0", "p": "10", "c": "6", "F": "2000"}, "500"),       # punto de equilibrio
    ("costo_total", "T", {"F": "500", "c": "3", "q": "100"}, "800"),
    ("aceleracion", "a", {"v": "20", "u": "5", "t": "3"}, "5"),
])
def test_resultados_conocidos(id_formula, objetivo, valores, esperado):
    sol = calcular(id_formula, objetivo, valores)
    respuesta = sol.resultado.split("=", 1)[1].strip()
    if esperado.startswith("±"):
        assert respuesta.startswith("±")
        if esperado == "±":
            assert sol.resultado_decimal is not None
        else:
            assert _a_fraccion(respuesta.removeprefix("±")) == _a_fraccion(esperado.removeprefix("±")), sol.resultado
    else:
        assert _a_fraccion(respuesta) == _a_fraccion(esperado), sol.resultado
    assert sol.tipo == "formula_numerica" and formula(id_formula).variable(objetivo).unidad in sol.nota


def test_los_pasos_son_despeje_sustitucion_y_operaciones():
    sol = calcular("velocidad", "t", {"d": "20", "v": "4"})
    reglas = [p.regla for p in sol.pasos]
    assert reglas[0] == "quitar_denominadores" and "comprobar" not in reglas        # el despeje, sin la comprobación simbólica
    i = reglas.index("sustituir")
    assert sol.pasos[i].expresion == "t = 20/4" and "v = 4 m/s, d = 20 m" in sol.pasos[i].explicacion
    assert [p.numero for p in sol.pasos] == list(range(1, len(sol.pasos) + 1))      # numeración seguida
    assert sol.resultado == "t = 5" and sol.nota == "Respuesta: t = 5 s (tiempo)."
    assert all(p.explicacion and p.motivo and p.latex for p in sol.pasos)


def test_pi_se_usa_aproximado_y_se_avisa():
    sol = calcular("circunferencia", "C", {"r": "5"})
    assert "π ≈ 3,1416" in sol.nota and "3,1416" in [p for p in sol.pasos if p.regla == "sustituir"][0].explicacion
    assert abs(float(sol.resultado.split("=")[1])) == pytest.approx(2 * 3.1416 * 5)


def test_despejes_no_lineales_calculan_radicales_y_muestran_unidades():
    area = calcular("area_circulo", "r", {"A": "25"})
    energia = calcular("energia_cinetica", "v", {"K": "100", "m": "2"})
    assert area.resultado.startswith("r = ±") and area.resultado_decimal
    assert "unidades" in area.nota and "≈" in area.nota
    assert energia.resultado == "v = ±10" and "m/s" in energia.nota


def test_valores_con_fraccion_decimal_con_coma_y_negativos():
    assert calcular("newton", "F", {"m": "2,5", "a": "4"}).resultado == "F = 10"
    assert _a_fraccion(calcular("newton", "F", {"m": "1/2", "a": "1/3"}).resultado.split("=")[1].strip()) == Fraction(1, 6)
    assert _a_fraccion(calcular("aceleracion", "a", {"v": "−10", "u": "10", "t": "4"}).resultado.split("=")[1].strip()) == -5


@pytest.mark.parametrize("id_formula, objetivo, valores, pista", [
    ("velocidad", "t", {"d": "20"}, "Falta el valor de v"),
    ("velocidad", "t", {"d": "20", "v": ""}, "Falta el valor de v"),
    ("velocidad", "t", {"d": "veinte", "v": "4"}, "debe ser un número"),
    ("velocidad", "t", {"d": "2+", "v": "4"}, "no se entiende"),
    ("velocidad", "z", {"d": "20", "v": "4"}, "no tiene la letra z"),
    ("no_existe", "t", {}, "No conozco la fórmula"),
    ("velocidad", "v", {"d": "5", "t": "0"}, "dividir entre cero"),
    ("velocidad", "t", {"d": "5", "v": "0"}, "dividir entre cero"),
])
def test_errores_claros(id_formula, objetivo, valores, pista):
    with pytest.raises((ErrorDeEntrada, ErrorMatematico)) as e:
        calcular(id_formula, objetivo, valores)
    assert pista in str(e.value)


# ---------------------------------------------------------------------------
# Al azar: la respuesta tiene que CUMPLIR la fórmula original (verificado con SymPy)
# ---------------------------------------------------------------------------

def test_cada_respuesta_cumple_la_formula_original():
    rng = random.Random(2026)
    pi = sp.Rational(PI_APROX.replace(".", ""), 10 ** len(PI_APROX.split(".")[1]))
    comprobadas = 0
    for f in FORMULAS.values():
        izq, der = f.expresion.split("=")
        ecuacion = _sympy_de(izq) - _sympy_de(der)
        simbolos = {v.letra: sp.Symbol(v.letra) for v in f.variables}
        for v in f.variables:
            for _ in range(6):
                valores = {w.letra: str(rng.choice([2, 3, 4, 5, 8, 10, 12, 20, 25])) + rng.choice(["", "", ".5"])
                           for w in f.variables if w.letra != v.letra}
                if f.id == "utilidad":                         # que (p − c) no sea cero y p > c
                    valores["p"], valores["c"] = "30", "12"
                try:
                    sol = calcular(f.id, v.letra, valores)
                except ErrorMatematico:
                    continue                                   # esos números hacen la fórmula imposible (÷ 0)
                texto_respuesta = sol.resultado.split("=", 1)[1].strip().removeprefix("±").replace("−", "-")
                if sol.resultado_decimal and not re.fullmatch(r"-?\d+(?:/\d+|\.\d+)?", texto_respuesta):
                    respuesta = sp.Float(sol.resultado_decimal.replace("−", "-"))
                elif re.fullmatch(r"-?\d+(?:/\d+|\.\d+)?", texto_respuesta):
                    respuesta = sp.Rational(_a_fraccion(texto_respuesta))
                else:
                    # El motor conserva el radical exacto en la respuesta; usa su aproximación para
                    # comprobar que satisface la fórmula con los datos numéricos elegidos.
                    assert sol.resultado_decimal, (f.id, v.letra, sol.resultado)
                    respuesta = sp.Float(sol.resultado_decimal)
                sustitucion = {simbolos[k]: sp.Rational(Fraction(x)) for k, x in valores.items()}
                sustitucion[simbolos[v.letra]] = respuesta
                sustitucion[sp.pi] = pi
                assert abs(float(ecuacion.subs(sustitucion))) < 1e-5, f"{f.id}: {v.letra} = {respuesta} con {valores} NO cumple {f.expresion}"
                comprobadas += 1
                assert all(p.explicacion and p.motivo for p in sol.pasos)
    assert comprobadas > 400
