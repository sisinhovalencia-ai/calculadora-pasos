"""Pruebas de la aritmética.

Tres capas:
  1. Casos fijos con respuesta conocida (incluye los errores clásicos de estudiantes).
  2. Errores: mensajes claros, nunca trazas técnicas.
  3. Pruebas automáticas "de verdad": cientos de expresiones al azar comparadas
     contra Python (con Fraction, que es exacto) y una invariante de pasos:
     CADA paso intermedio, vuelto a resolver, debe dar el mismo resultado final.
"""

import math
import random
import re
from fractions import Fraction

import pytest

from motor import ErrorDeEntrada, ErrorMatematico, resolver


def _acepta_rechazo(mensaje: str, esperado) -> bool:
    """Rechazos que el motor hace A PROPÓSITO (no son un bug): 0^0, y raíces no exactas o de negativos cuando
    Python (que no es exacto) da un decimal o un número complejo."""
    if "indeterminada" in mensaje:
        return True
    if not isinstance(esperado, Fraction):
        return any(p in mensaje for p in ("exponente entero", "no es exacta", "No existe la raíz", "denominador 2, 3 o 4"))
    return False


def _iguales(obtenido: Fraction, esperado) -> bool:
    """Exacto si Python dio una Fraction; con tolerancia si dio un decimal (Python aproxima las raíces)."""
    if isinstance(esperado, Fraction):
        return obtenido == esperado
    return isinstance(esperado, (int, float)) and math.isclose(float(obtenido), float(esperado), rel_tol=1e-9)


def valor(texto: str) -> Fraction:
    """Resultado exacto como Fraction, leyendo el texto del resultado."""
    sol = resolver(texto)
    r = sol.resultado.replace("−", "-")
    return Fraction(r)


# ---------------------------------------------------------------------------
# 1. Casos fijos
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("texto, esperado", [
    ("2 + 3", 5),
    ("2 + 3 * 4", 14),
    ("(2 + 3) * 4", 20),
    ("10 - 4 - 3", 3),            # resta de izquierda a derecha
    ("100 / 10 / 5", 2),          # división de izquierda a derecha
    ("8 / 2 * 3", 12),            # NO es 8/6
    ("2^3^2", 512),               # potencia asociativa a la derecha
    ("-3^2", -9),                 # el clásico: no es 9
    ("(-3)^2", 9),
    ("2^-3", Fraction(1, 8)),
    ("2^0", 1),
    ("(-2)^3", -8),
    ("-(2 + 3)", -5),
    ("-(-(2 + 3))", 5),
    ("2 - -3", 5),
    ("2 * -3", -6),
    ("1/2 + 1/3", Fraction(5, 6)),
    ("1/2 - 1/3", Fraction(1, 6)),
    ("1/2 * 2/3", Fraction(1, 3)),
    ("(1/2) / (1/4)", 2),
    ("7/2", Fraction(7, 2)),
    ("0.1 + 0.2", Fraction(3, 10)),   # exacto, sin 0.30000000000000004
    ("0,5 + 0,25", Fraction(3, 4)),   # coma decimal
    ("3(4 + 1)", 15),                 # multiplicación implícita
    ("2(3 + 4)(1 + 1)", 28),
    ("8 ÷ 2(2 + 2)", 16),             # convención: igual precedencia, izquierda a derecha
    ("6 : 3", 2),
    ("2 × 3 · 4", 24),
    ("5 − 2 − 1", 2),                 # signo menos tipográfico
    ("2 ** 3", 8),
    ("42", 42),
    ("((((7))))", 7),
    ("0 * 5", 0),
])
def test_resultados(texto, esperado):
    assert valor(texto) == Fraction(esperado)


def test_orden_de_los_pasos():
    sol = resolver("2 + 3 * (4 - 1)^2")
    assert [p.regla for p in sol.pasos] == ["resta", "potencia", "multiplicacion", "suma"]
    assert [p.expresion for p in sol.pasos] == ["2 + 3 × 3^2", "2 + 3 × 9", "2 + 27", "29"]
    assert sol.pasos[0].en_parentesis is True
    assert sol.pasos[1].en_parentesis is False


# --- fracciones: "/" entre enteros es una fracción; "÷" y ":" son división ---

def test_fraccion_escrita_se_muestra_como_se_escribio():
    sol = resolver("1/2 + 1/3")
    assert sol.expresion_inicial == "1/2 + 1/3"       # no "1 ÷ 2 + 1 ÷ 3"
    assert [p.regla for p in sol.pasos] == ["suma"]    # va directo a sumar fracciones


def test_fraccion_simplificable_tiene_su_paso():
    sol = resolver("4/6 + 1/3")
    assert [p.regla for p in sol.pasos] == ["simplificacion", "suma"]
    assert sol.pasos[0].expresion == "2/3 + 1/3"
    assert "máximo común divisor" in sol.pasos[0].explicacion
    assert sol.resultado == "1"


@pytest.mark.parametrize("texto, esperado", [
    ("6/3", 2),
    ("-6/3", -2),
    ("0/5 + 1", 1),
    ("4/1", 4),
    ("8/2*3", 12),
    ("100/10/5", 2),
    ("2^6/3", Fraction(64, 3)),      # es (2^6)/3, NO 2^(6/3)
    ("3/4^2", Fraction(3, 16)),      # es 3/(4^2), NO (3/4)^2
    ("2^(6/3)", 4),                  # con paréntesis sí es el exponente
    ("6/-3", -2),
    ("(6/3)^2", 4),
    ("1/2/2", Fraction(1, 4)),
])
def test_fracciones_valores(texto, esperado):
    assert valor(texto) == Fraction(esperado)


def test_division_con_simbolo_no_es_fraccion():
    sol = resolver("6 ÷ 3")
    assert sol.expresion_inicial == "6 ÷ 3"
    assert [p.regla for p in sol.pasos] == ["division"]
    sol = resolver("6 : 3")
    assert [p.regla for p in sol.pasos] == ["division"]


def test_fraccion_irreducible_no_tiene_pasos():
    sol = resolver("7/2")
    assert sol.pasos == [] and sol.resultado == "7/2"


def test_cero_en_el_denominador_de_una_fraccion():
    for texto in ["5/0", "0/0", "1/2 + 3/0"]:
        with pytest.raises(ErrorMatematico):
            resolver(texto)


def test_con_decimales_la_barra_sigue_siendo_division():
    sol = resolver("1/2 + 0.5")
    assert sol.resultado == "1"
    assert all(p.regla != "simplificacion" for p in sol.pasos)


def test_numero_solo_no_tiene_pasos():
    sol = resolver("42")
    assert sol.pasos == []
    assert sol.resultado == "42"


def test_decimales_se_muestran_como_decimales():
    sol = resolver("0.1 + 0.2")
    assert sol.resultado == "0.3"
    assert sol.resultado_decimal is None   # ya es decimal, no hace falta repetirlo


def test_fraccion_ofrece_decimal():
    sol = resolver("7/2")
    assert sol.resultado == "7/2"
    assert sol.resultado_decimal == "3.5" and sol.decimal_exacto is True
    sol = resolver("1/3")
    assert sol.resultado == "1/3"
    assert sol.resultado_decimal == "0.333333" and sol.decimal_exacto is False


def test_motivo_y_explicacion_siempre_presentes():
    sol = resolver("2 + 3 * (4 - 1)^2 - 8 / 4")
    for p in sol.pasos:
        assert p.explicacion and p.motivo and p.operacion and p.latex


def test_signo_menos_se_explica():
    sol = resolver("-3^2")
    assert "signo menos" in sol.pasos[0].explicacion


def test_a_dict_es_serializable():
    import json
    sol = resolver("1/2 + 1/3")
    datos = json.loads(json.dumps(sol.a_dict(), ensure_ascii=False))
    assert datos["resultado"] == "5/6"
    assert len(datos["pasos"]) == 1


# ---------------------------------------------------------------------------
# 2. Errores
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("texto", [
    "", "   ", "2 +", "* 3", "(2 + 3", "2 + 3)", "()", "2 3", "2 + + * 3",
    "abc", "2 + x", "2 $ 3", "3.4.5", "2 +* 3",
])
def test_errores_de_entrada(texto):
    with pytest.raises(ErrorDeEntrada) as e:
        resolver(texto)
    assert str(e.value)   # siempre hay un mensaje legible


@pytest.mark.parametrize("texto", [
    "5 / 0", "1 / (2 - 2)", "0^0", "0^-1", "2^0.5", "2^(1/2)", "2^1001", "9^9^9",
])
def test_errores_matematicos(texto):
    with pytest.raises(ErrorMatematico) as e:
        resolver(texto)
    assert str(e.value)


def test_expresion_demasiado_larga():
    with pytest.raises(ErrorDeEntrada):
        resolver("1+" * 200 + "1")


def test_numeros_enormes_no_rompen():
    # sin la protección, mostrar esto lanzaría ValueError (límite de cifras de Python)
    with pytest.raises(ErrorMatematico):
        resolver("999^999 * 999^999 * 999^999")


# ---------------------------------------------------------------------------
# 3. Pruebas automáticas contra Python
# ---------------------------------------------------------------------------

def _referencia(texto: str):
    """Evalúa con Python usando Fraction. Python y esta calculadora comparten
    la misma jerarquía (** asociativo a la derecha, - unario más débil que **)."""
    t = texto.replace("^", "**")
    t = re.sub(r"\d+", lambda m: f"F({m.group(0)})", t)
    return eval(t, {"__builtins__": {}}, {"F": Fraction})


def _generar(rng: random.Random, profundidad: int) -> str:
    if profundidad <= 0 or rng.random() < 0.25:
        return str(rng.randint(0, 9))
    tipo = rng.random()
    if tipo < 0.15:
        return f"({_generar(rng, profundidad - 1)})"
    if tipo < 0.25:
        return f"-{_generar(rng, profundidad - 1)}" if rng.random() < 0.5 else f"(-{rng.randint(1, 9)})"
    if tipo < 0.40:
        exponente = rng.choice(["0", "1", "2", "3", "(-1)", "(-2)"])
        return f"{_generar(rng, profundidad - 1)}^{exponente}"
    op = rng.choice(["+", "-", "*", "/"])
    return f"{_generar(rng, profundidad - 1)}{op}{_generar(rng, profundidad - 1)}"


def test_contra_python_aleatorio():
    rng = random.Random(2026)     # semilla fija: si falla, se puede reproducir
    comparadas = 0
    for _ in range(600):
        expr = _generar(rng, 4)
        try:
            esperado = _referencia(expr)
        except ZeroDivisionError:
            with pytest.raises(ErrorMatematico):
                resolver(expr)
            continue
        try:
            obtenido = valor(expr)
        except ErrorMatematico as e:
            mensaje = str(e)
            if _acepta_rechazo(mensaje, esperado):
                continue
            raise AssertionError(f"{expr!r}: rechazo inesperado: {mensaje}")
        assert _iguales(obtenido, esperado), f"{expr!r}: motor={obtenido} python={esperado}"
        comparadas += 1
    assert comparadas > 300     # la prueba realmente comparó muchas expresiones


def test_cada_paso_conserva_el_resultado():
    """Invariante central: el texto de CADA paso intermedio, vuelto a resolver,
    da el mismo resultado final. Si esto falla, un paso mostró algo incorrecto."""
    rng = random.Random(7)
    revisadas = 0
    for _ in range(300):
        expr = _generar(rng, 4)
        try:
            sol = resolver(expr)
        except ErrorMatematico:
            continue
        final = Fraction(sol.resultado.replace("−", "-"))
        for p in sol.pasos:
            assert valor(p.expresion) == final, (
                f"{expr!r}: el paso {p.numero} ({p.expresion!r}) cambió el resultado"
            )
            revisadas += 1
    assert revisadas > 300


# ---------------------------------------------------------------------------
# 4. Lo mismo, pero con decimales (usan otro camino de formato)
# ---------------------------------------------------------------------------

def _generar_decimal(rng: random.Random, profundidad: int) -> str:
    if profundidad <= 0 or rng.random() < 0.3:
        return rng.choice([str(rng.randint(0, 9)),
                           f"{rng.randint(0, 9)}.{rng.randint(0, 99)}",
                           f"0.{rng.randint(1, 9)}"])
    tipo = rng.random()
    if tipo < 0.15:
        return f"({_generar_decimal(rng, profundidad - 1)})"
    if tipo < 0.30:
        return f"{_generar_decimal(rng, profundidad - 1)}^{rng.choice(['0', '1', '2', '3', '(-1)'])}"
    op = rng.choice(["+", "-", "*", "/"])
    return f"{_generar_decimal(rng, profundidad - 1)}{op}{_generar_decimal(rng, profundidad - 1)}"


def _referencia_decimal(texto: str):
    t = texto.replace("^", "**")
    t = re.sub(r"\d+(?:\.\d+)?", lambda m: f'F("{m.group(0)}")', t)
    return eval(t, {"__builtins__": {}}, {"F": Fraction})


def test_decimales_contra_python_y_pasos():
    rng = random.Random(99)
    comparadas = pasos = 0
    for _ in range(400):
        expr = _generar_decimal(rng, 4)
        try:
            esperado = _referencia_decimal(expr)
        except ZeroDivisionError:
            with pytest.raises(ErrorMatematico):
                resolver(expr)
            continue
        try:
            sol = resolver(expr)
        except ErrorMatematico as e:
            mensaje = str(e)
            if _acepta_rechazo(mensaje, esperado):
                continue
            raise AssertionError(f"{expr!r}: rechazo inesperado: {mensaje}")
        final = Fraction(sol.resultado.replace("−", "-"))
        assert _iguales(final, esperado), f"{expr!r}: motor={final} python={esperado}"
        comparadas += 1
        for p in sol.pasos:
            assert valor(p.expresion) == final, f"{expr!r}: el paso {p.numero} cambió el resultado"
            pasos += 1
    assert comparadas > 200 and pasos > 200


# ---------------------------------------------------------------------------
# 5. Porcentajes, números mixtos y raíces
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("texto, esperado", [
    # porcentajes
    ("20% de 150", 30),
    ("20% × 150", 30),
    ("50%", Fraction(1, 2)),
    ("100%", 1),
    ("0%", 0),
    ("12.5% de 80", 10),
    ("200% de 10", 20),
    ("10% + 10%", Fraction(1, 5)),
    ("25% de 80 + 5", 25),
    ("150 + 20% de 150", 180),
    # números mixtos
    ("3 1/2", Fraction(7, 2)),
    ("2 3/4 + 1 1/4", 4),
    ("3 1/2 * 2", 7),
    ("1 1/2 ÷ (3/4)", 2),
    ("-3 1/2", Fraction(-7, 2)),
    ("5 0/3", 5),
    ("2 5/3", Fraction(11, 3)),
    ("3 6/4", Fraction(9, 2)),
    ("(3 1/2)^2", Fraction(49, 4)),
    ("6 / 3 1/2", Fraction(12, 7)),
    # raíces
    ("√49", 7),
    ("√0", 0),
    ("√1", 1),
    ("√(16 + 9)", 5),
    ("∛27", 3),
    ("∛(−27)", -3),
    ("∜16", 2),
    ("√(9/16)", Fraction(3, 4)),
    ("√0.25", Fraction(1, 2)),
    ("√4 + √9", 5),
    ("2√9", 6),                      # multiplicación implícita
    ("√4 × √9", 6),
    ("-√9", -3),
    ("√√16", 2),
    ("raiz(25)", 5),
    ("raíz(25)", 5),
    ("sqrt(25)", 5),
    ("(√9)^2", 9),
    ("√9^2", 9),                     # convención: √ se aplica al 9 y luego se eleva al cuadrado
    ("2^3 + √9", 11),
])
def test_porcentajes_mixtos_y_raices(texto, esperado):
    assert valor(texto) == Fraction(esperado)


def test_dividir_entre_fraccion_sin_parentesis_se_lee_de_izquierda_a_derecha():
    """`a ÷ b/c` es (a ÷ b)/c, igual que en Python y en las calculadoras.
    Para dividir entre una fracción hay que escribir paréntesis: a ÷ (b/c)."""
    assert valor("1 1/2 ÷ 3/4") == Fraction(1, 8)
    assert valor("8 ÷ 2/4") == 1
    assert valor("8 ÷ (2/4)") == 16
    # la pantalla muestra cómo se interpretó, para que el estudiante lo note
    assert resolver("8 ÷ 2/4").expresion_inicial == "8 ÷ 2 ÷ 4"


def test_explicaciones_de_lo_nuevo():
    p = resolver("20% de 150").pasos
    assert p[0].regla == "porcentaje" and "de cada 100" in p[0].explicacion
    assert "multiplicar" in p[0].motivo                       # por usar «de»
    assert "multiplicar" not in resolver("20% + 1").pasos[0].motivo

    p = resolver("3 1/2").pasos
    assert p[0].regla == "mixto" and "número mixto" in p[0].explicacion and "7/2" in p[0].explicacion

    p = resolver("√49").pasos
    assert p[0].regla == "raiz" and "porque 7 × 7 = 49" in p[0].explicacion
    assert "cúbica" in resolver("∛8").pasos[0].explicacion


def test_orden_con_raices_y_parentesis():
    sol = resolver("√(16 + 9) + 1")
    assert [p.regla for p in sol.pasos] == ["suma", "raiz", "suma"]
    assert sol.pasos[0].en_parentesis is True
    assert sol.pasos[0].expresion == "√25 + 1"


def test_texto_de_lo_nuevo_se_muestra_como_se_escribio():
    assert resolver("3 1/2 + 2").expresion_inicial == "3 1/2 + 2"
    assert resolver("20% de 150").expresion_inicial == "20% × 150"
    assert resolver("raiz(49)").expresion_inicial == "√49"
    assert resolver("√(9/16)").expresion_inicial == "√(9/16)"


@pytest.mark.parametrize("texto", [
    "√2", "√(1 - 5)", "√(-4)", "∛2", "∜5", "√3 + 1", "3 1/0", "√(1/2)",
])
def test_errores_matematicos_nuevos(texto):
    with pytest.raises(ErrorMatematico) as e:
        resolver(texto)
    assert str(e.value)


@pytest.mark.parametrize("texto", [
    "√", "√+", "√-4", "%", "20 %%", "de 5", "5 de", "3 1/2^2", "(5)%", "raiz", "2 √",
])
def test_errores_de_entrada_nuevos(texto):
    with pytest.raises(ErrorDeEntrada) as e:
        resolver(texto)
    assert str(e.value)


def test_raiz_no_exacta_explica_el_limite():
    with pytest.raises(ErrorMatematico) as e:
        resolver("√2")
    assert "no es exacta" in str(e.value)


def _generar_doble(rng: random.Random, profundidad: int):
    """(texto para el motor, texto equivalente para Python) del mismo valor."""
    if profundidad <= 0 or rng.random() < 0.3:
        t = rng.random()
        if t < 0.50:
            n = rng.randint(0, 12)
            return str(n), f"F({n})"
        if t < 0.62:
            k = rng.randint(0, 9)
            return f"√{k * k}", f"F({k})"
        if t < 0.68:
            k = rng.randint(0, 5)
            return f"∛{k ** 3}", f"F({k})"
        if t < 0.74:
            k = rng.randint(1, 6)
            return f"√({k}×{k})", f"F({k})"
        if t < 0.87:
            p = rng.choice([5, 10, 12, 20, 25, 50, 75, 100, 150])
            return f"{p}%", f"(F({p})/F(100))"
        e, n, d = rng.randint(0, 9), rng.randint(0, 9), rng.randint(1, 9)
        return f"{e} {n}/{d}", f"(F({e})+F({n})/F({d}))"
    t = rng.random()
    a, ra = _generar_doble(rng, profundidad - 1)
    if t < 0.12:
        return f"({a})", f"({ra})"
    if t < 0.20:
        return f"-({a})", f"-({ra})"
    if t < 0.32:
        k = rng.choice(["2", "3", "(-1)"])
        return f"({a})^{k}", f"({ra})**{k}"
    b, rb = _generar_doble(rng, profundidad - 1)
    op = rng.choice(["+", "-", "*", "/", "de"])
    return f"{a} {op} {b}", f"{ra} {'*' if op == 'de' else op} {rb}"


def test_nuevos_contra_python_y_pasos():
    rng = random.Random(31)
    comparadas = pasos = 0
    for _ in range(500):
        texto, ref = _generar_doble(rng, 3)
        try:
            esperado = eval(ref, {"__builtins__": {}}, {"F": Fraction})
        except ZeroDivisionError:
            with pytest.raises(ErrorMatematico):
                resolver(texto)
            continue
        try:
            sol = resolver(texto)
        except ErrorMatematico as e:
            raise AssertionError(f"{texto!r}: rechazo inesperado: {e}")
        final = Fraction(sol.resultado.replace("−", "-"))
        assert final == esperado, f"{texto!r}: motor={final} python={esperado}"
        comparadas += 1
        for p in sol.pasos:
            assert valor(p.expresion) == final, (
                f"{texto!r}: el paso {p.numero} ({p.expresion!r}) cambió el resultado")
            pasos += 1
    assert comparadas > 300 and pasos > 500
