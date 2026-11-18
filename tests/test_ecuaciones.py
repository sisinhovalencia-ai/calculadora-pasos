"""Pruebas de las ecuaciones lineales.

  1. Casos fijos con solución conocida (y los casos raros: sin solución, infinitas).
  2. Errores claros (no lineal, dos incógnitas, falta un lado…).
  3. Ecuaciones al azar de formas variadas, cuya solución se calcula por separado.
  4. Invariantes de los pasos: cada ecuación intermedia tiene la MISMA solución.
"""

import random
from fractions import Fraction

import pytest

from motor import ErrorDeEntrada, ErrorMatematico, resolver, resolver_ecuacion, resolver_ejercicio


def solucion(texto):
    """Valor de x como Fraction, o el texto 'Sin solución' / 'Infinitas soluciones'."""
    r = resolver_ecuacion(texto).resultado
    if "=" in r:
        return Fraction(r.split("=")[1].strip().replace("−", "-"))
    return r


# ---------------------------------------------------------------------------
# 1. Casos fijos
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("texto, esperado", [
    ("2x + 3 = 11", 4),
    ("2x+3=11", 4),
    ("x + 5 = 9", 4),
    ("x − 5 = 7", 12),
    ("3x = 12", 4),
    ("x = 5", 5),
    ("−3x = 6", -2),
    ("−x = 4", -4),
    ("3x − 5 = 2x + 7", 12),
    ("5x + 2 = 3x + 10", 4),
    ("2x + 10 = 5x + 1", 3),
    ("2(x + 3) = 14", 4),
    ("3(x − 1) = 2(x + 4)", 11),
    ("−2(x − 3) = 10", -2),
    ("x/2 + 1 = 5", 8),
    ("x/3 = 4", 12),
    ("(x + 1)/3 = 2", 5),
    ("(1/2)x − 1 = 3", 8),
    ("3/4x = 6", 8),
    ("5 = 2x + 1", 2),
    ("11 = 2x + 3", 4),
    ("2x + 1 = 2", Fraction(1, 2)),
    ("4x = 2", Fraction(1, 2)),
    ("3x + 1 = 0", Fraction(-1, 3)),
    ("0.5x + 1 = 3", 4),
    ("0,5x + 1 = 3", 4),
    ("2.5x = 10", 4),
    ("x + 0.1 = 0.3", Fraction(1, 5)),
    ("2x + x = 9", 3),                       # términos parecidos
    ("3 + 2x = 11", 4),                      # orden distinto
    ("5 + 6 = x + 1", 10),
    ("2a + 4 = 10", 3),                      # otra letra
    ("y − 1 = 1", 2),
    ("x + 4 = 9", 5),
    ("20% de 150 = x + 5", 25),
    ("√49 + x = 10", 3),
    ("2x = 3 1/2", Fraction(7, 4)),
    ("0x + x = 6", 6),
])
def test_soluciones(texto, esperado):
    assert solucion(texto) == Fraction(esperado)


def test_sin_solucion_e_infinitas():
    assert resolver_ecuacion("x + 1 = x + 2").resultado == "Sin solución"
    assert resolver_ecuacion("2x + 3 = 2x + 5").resultado == "Sin solución"
    assert resolver_ecuacion("2x + 2 = 2(x + 1)").resultado == "Infinitas soluciones"
    assert resolver_ecuacion("x = x").resultado == "Infinitas soluciones"
    assert resolver_ecuacion("x − x = 5").resultado == "Sin solución"
    assert resolver_ecuacion("x − x = 0").resultado == "Infinitas soluciones"
    assert "no tiene solución" in resolver_ecuacion("x + 1 = x + 2").pasos[-1].explicacion
    assert "infinitas soluciones" in resolver_ecuacion("x = x").pasos[-1].explicacion


def test_pasos_de_2x_mas_3():
    sol = resolver_ecuacion("2x + 3 = 11")
    assert [p.regla for p in sol.pasos] == ["mover_constante", "despejar", "comprobar"]
    assert sol.pasos[0].expresion == "2x = 8"
    assert "restamos 3 en ambos lados" in sol.pasos[0].explicacion
    assert sol.pasos[1].expresion == "x = 4"
    assert "dividimos ambos lados entre 2" in sol.pasos[1].explicacion
    assert sol.resultado == "x = 4"
    assert sol.expresion_inicial == "2x + 3 = 11"


def test_pasos_con_x_en_los_dos_lados():
    sol = resolver_ecuacion("3x − 5 = 2x + 7")
    assert [p.regla for p in sol.pasos] == ["mover_x", "mover_constante", "comprobar"]
    assert sol.pasos[0].expresion == "x − 5 = 7"
    assert "restamos 2x" in sol.pasos[0].explicacion
    assert "sumamos 5" in sol.pasos[1].explicacion


def test_distributiva_y_reduccion_en_pasos_separados():
    sol = resolver_ecuacion("2(x + 3) = 14")
    assert [p.regla for p in sol.pasos[:2]] == ["distribuir", "simplificar"]
    assert sol.pasos[0].expresion == "2x + 2 × 3 = 14"
    assert sol.pasos[1].expresion == "2x + 6 = 14"
    assert "propiedad distributiva" in sol.pasos[0].explicacion


def test_distributiva_con_negativos():
    assert solucion("−2(x − 3) = 10") == -2
    sol = resolver_ecuacion("−2(x − 3) = 10")
    assert sol.pasos[0].expresion == "(−2) × x − (−2) × 3 = 10"
    assert solucion("−(x + 3) = 5") == -8
    assert resolver_ecuacion("−(x + 3) = 5").pasos[0].expresion == "−x − 3 = 5"


def test_la_x_se_junta_donde_queda_positiva():
    sol = resolver_ecuacion("2(x + 3) − 4 = 3x − 9")
    mx = [p for p in sol.pasos if p.regla == "mover_x"][0]
    assert mx.expresion == "2 = x − 9" and "lado derecho" in mx.explicacion
    assert mx.intermedio == "2x + 2 − 2x = 3x − 9 − 2x"
    assert sol.pasos[-2].regla == "intercambiar" and sol.pasos[-2].expresion == "x = 11"
    assert sol.resultado == "x = 11"
    for texto in ["3x + 1 = 5x − 7", "x − 4 = 3x + 2", "2x = 5x − 9", "x + 1 = 3x − 5", "2x + 1 = −x + 7"]:
        explicaciones = " ".join(p.explicacion for p in resolver_ecuacion(texto).pasos)
        assert "dividimos ambos lados entre −" not in explicaciones, texto


def test_x_a_la_derecha_sin_intercambio_inicial():
    sol = resolver_ecuacion("5 = 2x + 1")
    assert [p.regla for p in sol.pasos] == ["mover_constante", "despejar", "intercambiar", "comprobar"]
    assert sol.pasos[0].intermedio == "5 − 1 = 2x + 1 − 1" and sol.pasos[0].expresion == "4 = 2x"
    assert sol.pasos[1].intermedio == "4 ÷ 2 = 2x ÷ 2" and sol.pasos[1].expresion == "2 = x"
    assert sol.pasos[2].expresion == "x = 2"


def test_cada_operacion_se_muestra_en_los_dos_lados():
    sol = resolver_ecuacion("2x + 3 = 11")
    assert sol.pasos[0].intermedio == "2x + 3 − 3 = 11 − 3" and sol.pasos[0].expresion == "2x = 8"
    assert sol.pasos[1].intermedio == "2x ÷ 2 = 8 ÷ 2"
    assert "\\frac" in sol.pasos[1].latex_intermedio


def test_dividir_entre_fraccion_y_negativo():
    assert "inverso" in resolver_ecuacion("x/2 + 1 = 5").pasos[-2].explicacion
    assert "cambiar el signo" in resolver_ecuacion("−x = 4").pasos[0].explicacion


def test_resultado_decimal_de_una_fraccion():
    sol = resolver_ecuacion("4x = 2")
    assert sol.resultado == "x = 1/2" and sol.resultado_decimal == "0.5" and sol.decimal_exacto is True
    sol = resolver_ecuacion("3x = 1")
    assert sol.resultado == "x = 1/3" and sol.decimal_exacto is False


def test_con_decimales_se_muestra_en_decimales():
    sol = resolver_ecuacion("0.5x + 1 = 3")
    assert sol.resultado == "x = 4"
    assert "0.5x" in sol.expresion_inicial


def test_despachador():
    assert resolver_ejercicio("2x + 3 = 11").tipo == "ecuacion_lineal"
    assert resolver_ejercicio("2 + 3").tipo == "aritmetica"


def test_superindices_en_aritmetica():
    assert resolver("3² + 1").resultado == "10"
    assert resolver("2³").resultado == "8"


def test_a_dict_serializable():
    import json
    datos = json.loads(json.dumps(resolver_ecuacion("2x + 3 = 11").a_dict(), ensure_ascii=False))
    assert datos["resultado"] == "x = 4" and len(datos["pasos"]) == 3


# ---------------------------------------------------------------------------
# 2. Errores
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("texto", [
    "", "   ", "2x + 3", "2x + 3 =", "= 5", "2x = 3 = 4", "2x + 3 == 11",
    "2 + 3 = 5", "x + y = 3", "x y = 3", "2x + = 3", "(x + 1 = 3", "x = 3)", "xy = 3", "2x3 = 6",
    "1.2.3x = 4",
])
def test_errores_de_entrada(texto):
    with pytest.raises(ErrorDeEntrada) as e:
        resolver_ecuacion(texto)
    assert str(e.value)


@pytest.mark.parametrize("texto, pista", [
    ("x² = 4", "no es lineal"),
    ("x^2 = 4", "no es lineal"),
    ("x * x = 4", "no es lineal"),
    ("x(x + 1) = 4", "no es lineal"),
    ("(x + 1)(x − 1) = 0", "no es lineal"),
    ("3/x = 2", "denominador"),
    ("2^x = 8", "exponente"),
    ("√x = 3", "raíz"),
    ("x/0 = 1", "dividir entre cero"),
    ("x = 5/0", "dividir entre cero"),
    ("x = √2", "no es exacta"),
])
def test_errores_matematicos(texto, pista):
    with pytest.raises(ErrorMatematico) as e:
        resolver_ecuacion(texto)
    assert pista in str(e.value)


# ---------------------------------------------------------------------------
# 3. Al azar, con la solución calculada por separado
# ---------------------------------------------------------------------------

def _entero(rng, bajo=-9, alto=9):
    return rng.randint(bajo, alto)


def _termino(rng):
    """(texto, a, b): un término que vale a·x + b."""
    t = rng.random()
    if t < 0.20:
        k = _entero(rng, 0, 20)
        return f"{k}", Fraction(0), Fraction(k)
    if t < 0.28:
        p, q = _entero(rng, 0, 9), _entero(rng, 1, 9)
        return f"{p}/{q}", Fraction(0), Fraction(p, q)
    if t < 0.50:
        k = _entero(rng, 1, 9)
        return f"{k}x", Fraction(k), Fraction(0)
    if t < 0.58:
        return "x", Fraction(1), Fraction(0)
    if t < 0.76:
        k, m = _entero(rng, 1, 6), _entero(rng, -6, 6)
        signo = "+" if m >= 0 else "−"
        return f"{k}(x {signo} {abs(m)})", Fraction(k), Fraction(k * m)
    if t < 0.88:
        d, m = _entero(rng, 1, 6), _entero(rng, -6, 6)
        signo = "+" if m >= 0 else "−"
        return f"(x {signo} {abs(m)})/{d}", Fraction(1, d), Fraction(m, d)
    d = _entero(rng, 1, 6)
    return f"x/{d}", Fraction(1, d), Fraction(0)


def _lado(rng):
    texto, a, b = _termino(rng)
    for _ in range(rng.randint(0, 2)):
        t, ta, tb = _termino(rng)
        if rng.random() < 0.5:
            texto, a, b = f"{texto} + {t}", a + ta, b + tb
        else:
            texto, a, b = f"{texto} − {t}" if "(" not in t and "/" not in t and "+" not in t else f"{texto} − ({t})", a - ta, b - tb
    return texto, a, b


def test_azar_contra_la_solucion_calculada_aparte():
    rng = random.Random(2026)
    unicas = sin = infinitas = 0
    for _ in range(1200):
        tI, aL, bL = _lado(rng)
        tD, aR, bR = _lado(rng)
        texto = f"{tI} = {tD}"
        if "x" not in texto:                       # sin incógnita: el motor debe avisarlo
            with pytest.raises(ErrorDeEntrada):
                resolver_ecuacion(texto)
            continue
        sol = resolver_ecuacion(texto)
        if aL != aR:
            esperado = (bR - bL) / (aL - aR)
            assert solucion(texto) == esperado, f"{texto!r}: motor={sol.resultado} esperado={esperado}"
            unicas += 1
            # cada ecuación intermedia que aún tiene x debe tener la misma solución
            for p in sol.pasos:
                if "x" in p.expresion:
                    assert solucion(p.expresion) == esperado, f"{texto!r}: paso {p.numero} ({p.expresion!r}) cambió la solución"
                if p.intermedio:
                    assert solucion(p.intermedio) == esperado, f"{texto!r}: la línea previa del paso {p.numero} ({p.intermedio!r}) cambió la solución"
        elif bL == bR:
            assert sol.resultado == "Infinitas soluciones", texto
            infinitas += 1
        else:
            assert sol.resultado == "Sin solución", texto
            sin += 1
        assert all(p.explicacion and p.motivo and p.latex for p in sol.pasos)
        for p in sol.pasos:
            if p.operacion:
                assert p.operacion in p.explicacion, f"{texto!r}: {p.operacion!r} no está en {p.explicacion!r}"
    assert unicas > 1000 and sin + infinitas > 5
