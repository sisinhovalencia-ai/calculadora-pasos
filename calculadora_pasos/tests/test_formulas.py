"""Pruebas de «despejar una letra de una fórmula».

  1. Casos fijos con la respuesta que daría un libro de texto.
  2. Errores claros.
  3. Fórmulas al azar, verificadas de DOS maneras independientes del motor:
       - el texto de la respuesta, vuelto a leer y evaluado con números, debe coincidir con lo que da SymPy;
       - cada paso intermedio (y cada línea gris) debe tener la MISMA solución que la fórmula original.
"""

import random
from fractions import Fraction

import pytest
import sympy as sp

from motor import ErrorDeEntrada, ErrorMatematico, resolver, resolver_ejercicio, resolver_formula
from motor.arbol import BinOp, Cociente, Neg, Num, Paren, Var, normalizar
from motor.formulas import _a_sympy
from motor.parser import parsear


# ---------------------------------------------------------------------------
# Ayudas: leer y evaluar un texto con letras
# ---------------------------------------------------------------------------

def evaluar(n, valores):
    if isinstance(n, Num):
        return n.valor
    if isinstance(n, Var):
        return valores[n.nombre]
    if isinstance(n, Neg):
        return -evaluar(n.hijo, valores)
    if isinstance(n, Paren):
        return evaluar(n.hijo, valores)
    a, b = evaluar(n.izq, valores), evaluar(n.der, valores)
    return {"+": lambda: a + b, "-": lambda: a - b, "*": lambda: a * b, "/": lambda: a / b,
            "^": lambda: a ** int(b)}[n.op]()


def valor_de(texto, valores):
    arbol, _ = parsear(texto, variables=True)
    return evaluar(normalizar(arbol), valores)


def lado_derecho(resultado: str) -> str:
    return resultado.split("=", 1)[1].strip()


# ---------------------------------------------------------------------------
# 1. Casos fijos
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("texto, esperado", [
    ("despejar t en v = d/t", "t = d/v"),
    ("despejar d en v = d/t", "d = v·t"),
    ("despejar v en v = d/t", "v = d/t"),                       # ya despejada
    ("despejar a en F = ma", "a = F/m"),
    ("despejar m en F = ma", "m = F/a"),
    ("F = m·a, despejar a", "a = F/m"),                         # el orden da igual
    ("despejar a: F = m·a", "a = F/m"),
    ("Despejar a en F = ma", "a = F/m"),
    ("despejar h en A = b·h/2", "h = 2A/b"),
    ("despejar b en A = b·h/2", "b = 2A/h"),
    ("despejar w en P = 2l + 2w", "w = (P − 2l)/2"),
    ("despejar l en P = 2(l + w)", "l = (P − 2w)/2"),
    ("despejar C en F = 9C/5 + 32", "C = (5F − 160)/9"),
    ("despejar a en v = u + at", "a = (v − u)/t"),
    ("despejar u en v = u + at", "u = v − a·t"),
    ("despejar r en C = 2πr", "r = C/(2π)"),
    ("despejar R en V = IR", "R = V/I"),
    ("despejar x en y = −x + 3", "x = 3 − y"),
    ("despejar x en 2x = 4a + 6", "x = 2a + 3"),                # simplifica el factor común
    ("despejar x en a·x = a·c", "x = c"),
    ("despejar x en a(x + b) = c", "x = (c − a·b)/a"),
    ("despejar v en 1/f = 1/u + 1/v", "v = f·u/(u − f)"),
    ("despejar x en ax + bx = c", "x = c/(a + b)"),             # factor común
    ("despejar x en 2x + 3 = 11", "x = 4"),                     # una sola letra: es una ecuación normal
])
def test_resultados(texto, esperado):
    assert resolver_formula(texto).resultado == esperado


def test_pasos_de_v_igual_d_sobre_t():
    sol = resolver_formula("despejar t en v = d/t")
    assert sol.tipo == "formula"
    assert [p.regla for p in sol.pasos] == ["quitar_denominadores", "despejar", "comprobar"]
    assert sol.pasos[0].intermedio == "v·t = (d/t)·t" and sol.pasos[0].expresion == "v·t = d"
    assert sol.pasos[1].intermedio == "(v·t)/v = d/v" and sol.pasos[1].expresion == "t = d/v"
    assert "\\frac" in sol.pasos[1].latex_intermedio and sol.pasos[1].latex == "t = \\frac{d}{v}"
    assert "t, v no valen 0" in sol.nota
    assert sol.resultado_latex == "t = \\frac{d}{v}"
    assert sol.expresion_inicial == "despejar t en v = d/t"


def test_si_la_letra_queda_a_la_derecha_se_lee_al_reves():
    sol = resolver_formula("despejar h en A = b·h/2")
    assert [p.regla for p in sol.pasos] == ["quitar_denominadores", "despejar", "intercambiar", "comprobar"]
    assert sol.pasos[1].expresion == "2A/b = h" and sol.pasos[2].expresion == "h = 2A/b"


def test_distributiva_aparte():
    sol = resolver_formula("despejar l en P = 2(l + w)")
    assert sol.pasos[0].regla == "distribuir" and sol.pasos[0].expresion == "P = 2l + 2w"
    assert "propiedad distributiva" in sol.pasos[0].explicacion


def test_factor_comun_y_coeficiente_con_letras():
    sol = resolver_formula("despejar x en ax + bx = c")
    reglas = [p.regla for p in sol.pasos]
    assert reglas == ["factor_comun", "despejar", "comprobar"]
    assert sol.pasos[0].expresion == "(a + b)·x = c"
    assert "a + b no vale 0" in sol.nota


def test_ya_despejada_no_hace_pasos_de_mas():
    sol = resolver_formula("despejar F en F = 9C/5 + 32")
    assert [p.regla for p in sol.pasos] == ["comprobar"]


def test_el_texto_dice_que_se_supone_distinto_de_cero():
    assert "b no vale 0" in resolver_formula("despejar h en A = b·h/2").nota
    assert resolver_formula("despejar w en P = 2l + 2w").nota == ""     # solo se divide entre 2


def test_despachador_y_letras_pegadas():
    assert resolver_ejercicio("despejar a en F = ma").tipo == "formula"
    assert resolver_ejercicio("2x + 3 = 11").tipo == "ecuacion_lineal"
    with pytest.raises(ErrorDeEntrada):
        resolver("ab + 1")                                           # en aritmética siguen siendo un error


def test_a_dict_serializable():
    import json
    datos = json.loads(json.dumps(resolver_formula("despejar t en v = d/t").a_dict(), ensure_ascii=False))
    assert datos["resultado"] == "t = d/v" and datos["pasos"][0]["latex_intermedio"]


def test_varias_letras_sin_decir_cual_despejar_ayuda():
    with pytest.raises(ErrorDeEntrada) as e:
        resolver_ejercicio("v = d/t")
    assert "despejar d en v = d/t" in str(e.value)


# ---------------------------------------------------------------------------
# 2. Errores
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("texto", [
    "despejar", "despejar t", "despejar t en", "despejar t en 2x + 3", "despejar z en v = d/t",
    "despejar t en v < d/t", "despejar t en v = d/t = 3", "despejar t en = d/t", "despejar t en v =",
    "despejar t en v = d/", "despejar t en (v = d/t",
])
def test_errores_de_entrada(texto):
    with pytest.raises(ErrorDeEntrada) as e:
        resolver_ejercicio(texto)
    assert str(e.value)


@pytest.mark.parametrize("texto, pista", [
    ("despejar x en x² = a", "potencia"),
    ("despejar x en x·x = a", "potencia"),
    ("despejar x en x + a = x + b", "se cancela"),
    ("despejar t en v = d/t + t", "potencia"),
    ("despejar x en y = x/0", "dividir entre cero"),
])
def test_errores_matematicos(texto, pista):
    with pytest.raises(ErrorMatematico) as e:
        resolver_ejercicio(texto)
    assert pista in str(e.value)


# ---------------------------------------------------------------------------
# 3. Al azar, verificadas con SymPy y con números
# ---------------------------------------------------------------------------

LETRAS = list("abcdmnpqrstvw")


def _termino(rng, T, otras, familia):
    o1, o2 = rng.sample(otras, 2)
    k = rng.randint(2, 9)
    opciones = [f"{k}*{T}", f"{o1}*{T}", f"{T}/{k}", f"{T}/{o1}", f"{o1}*{o2}", f"{o1}", f"{k}",
                f"{o1}/{k}", f"{o1}/{o2}", f"({T} + {o1})*{o2}", f"{k}*({T} - {o1})", f"{o1}*{o2}*{T}"]
    return rng.choice(opciones)


def _lado(rng, T, otras):
    texto = _termino(rng, T, otras, "A")
    for _ in range(rng.randint(0, 2)):
        t = _termino(rng, T, otras, "A")
        texto += rng.choice([" + ", " - "]) + (f"({t})" if (" " in t or "/" in t) else t)
    return texto


def _formula_azar(rng):
    T = rng.choice(LETRAS)
    otras = rng.sample([x for x in LETRAS if x != T], 3)
    if rng.random() < 0.25:                    # la letra aparece UNA vez, dentro de un denominador
        o1, o2, o3 = otras
        plantillas = [f"{o1} = {o2}/{T}", f"{o1} = {o2}/{T} + {o3}", f"1/{o1} = 1/{o2} + 1/{T}",
                      f"{o1}/{T} = {o2}*{o3}", f"{o1} + {o2}/{T} = {o3}"]
        izq, der = rng.choice(plantillas).split(" = ")
    else:
        izq, der = _lado(rng, T, otras), _lado(rng, T, otras)
    return T, izq, der


def _a_texto_motor(s: str) -> str:
    return s.replace("*", "·")


def test_azar_contra_sympy_y_los_pasos():
    rng = random.Random(2026)
    resueltas = errores = 0
    for _ in range(180):
        T, izq, der = _formula_azar(rng)
        Ts = sp.Symbol(T)
        S = {c: sp.Symbol(c) for c in LETRAS}
        oraculo = sp.solve(sp.sympify(izq, locals=S) - sp.sympify(der, locals=S), Ts)
        texto = f"despejar {T} en {_a_texto_motor(izq)} = {_a_texto_motor(der)}"
        if len(oraculo) != 1:
            with pytest.raises((ErrorMatematico, ErrorDeEntrada)):
                resolver_ejercicio(texto)
            errores += 1
            continue
        sol = resolver_formula(texto)
        assert sol.resultado.startswith(f"{T} = "), texto
        # (a) la respuesta mostrada, leída de nuevo y evaluada, coincide con SymPy
        for _intento in range(3):
            valores = {c: Fraction(n) for c, n in zip((c for c in LETRAS if c != T), rng.sample(range(2, 40), len(LETRAS) - 1))}
            esperado = oraculo[0].subs({sp.Symbol(c): sp.Rational(v.numerator, v.denominator) for c, v in valores.items()})
            if not esperado.is_finite:                      # esos números hacen la fórmula imposible (÷ 0): otro intento
                continue
            try:
                obtenido = valor_de(lado_derecho(sol.resultado), valores)
            except ZeroDivisionError:
                continue
            assert sp.Rational(obtenido.numerator, obtenido.denominator) == esperado, f"{texto!r}: {sol.resultado}"
        # (b) cada paso (y cada línea gris) tiene la misma solución que la fórmula original
        valores = {c: sp.Integer(n) for c, n in zip((c for c in LETRAS if c != T), rng.sample(range(2, 40), len(LETRAS) - 1))}
        esperado = oraculo[0].subs(valores_a_sym(valores))
        if not esperado.is_finite:
            resueltas += 1
            continue
        for p in sol.pasos:
            for linea in (p.expresion, p.intermedio):
                if not linea or T not in linea:
                    continue
                lt, rt = linea.split(" = ")
                eq = _a_sympy_texto(lt) - _a_sympy_texto(rt)
                num = eq.subs(valores_a_sym(valores))
                sols = sp.solve(num, Ts)
                assert sols == [esperado], f"{texto!r}: paso {p.numero} ({linea!r}) cambió la solución: {sols} vs {esperado}"
            if p.operacion:
                assert p.operacion in p.explicacion, f"{texto!r}: {p.operacion!r} no está en {p.explicacion!r}"
        assert sol.pasos[-1].regla == "comprobar" and all(p.motivo and p.latex for p in sol.pasos)
        resueltas += 1
    assert resueltas > 120 and errores >= 0


def valores_a_sym(valores):
    return {sp.Symbol(c): v for c, v in valores.items()}


def _a_sympy_texto(texto):
    arbol, _ = parsear(texto, variables=True)
    return _a_sympy(normalizar(arbol), {})
