"""Pruebas de las operaciones en columnas.

  1. Casos fijos (llevadas en cadena, préstamos en cadena, ceros, decimales, residuos…).
  2. Errores con mensajes claros.
  3. Miles de operaciones al azar comparadas con la aritmética exacta de Python.
  4. Revisión de la pizarra: líneas coherentes y marcas dentro de los límites.
"""

import random
from decimal import Decimal
from fractions import Fraction

import pytest

from motor import ErrorDeEntrada, ErrorMatematico, resolver_columnas


def valor(sol) -> Fraction:
    return Fraction(sol.resultado.replace("−", "-"))


# ---------------------------------------------------------------------------
# 1. Casos fijos
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("texto, esperado", [
    ("4567 + 289", "4856"),
    ("999 + 1", "1000"),                     # llevadas en cadena
    ("0 + 0", "0"),
    ("5 + 0", "5"),
    ("123 + 456 + 789", "1368"),
    ("1 + 2 + 3 + 4 + 5", "15"),
    ("3.5 + 2.25", "5.75"),
    ("0.5 + 0.5", "1"),
    ("0.1 + 0.2", "0.3"),
    ("12.345 + 0.655", "13"),
    ("905 − 267", "638"),
    ("1000 − 1", "999"),                     # préstamos en cadena
    ("1000 − 999", "1"),
    ("500 − 500", "0"),
    ("10 − 3", "7"),
    ("5 − 12", "−7"),                        # resultado negativo (se resta al revés)
    ("2.5 − 0.75", "1.75"),
    ("10 − 0.1", "9.9"),
    ("123 × 45", "5535"),
    ("5 × 0", "0"),
    ("0 × 7", "0"),
    ("1000 × 1000", "1000000"),
    ("999 × 999", "998001"),
    ("305 × 207", "63135"),                  # cifras 0 en el multiplicador
    ("2.5 × 4", "10"),
    ("0.5 × 0.5", "0.25"),
    ("1.2 × 0.03", "0.036"),
    ("7845 ÷ 12", "653.75"),
    ("100 ÷ 4", "25"),
    ("7 ÷ 12", "0.5833"),                    # el dividendo es menor que el divisor
    ("1 ÷ 3", "0.3333"),                     # no termina: se corta en 4 decimales
    ("10 ÷ 4", "2.5"),
    ("0 ÷ 5", "0"),
    ("5 ÷ 5", "1"),
    ("1.5 ÷ 0.5", "3"),
    ("4.5 ÷ 0.25", "18"),
    ("1000 ÷ 25", "40"),
    ("1005 ÷ 5", "201"),                     # cifras 0 en el cociente
    ("6 : 3", "2"),
    ("6 / 3", "2"),
    ("2 × 3", "6"),
    ("2 * 3", "6"),
    ("8 − 3", "5"),
])
def test_resultados(texto, esperado):
    assert resolver_columnas(texto).resultado == esperado


def test_pasos_de_una_suma():
    sol = resolver_columnas("4567 + 289")
    assert sol.tipo == "columnas_suma"
    assert sol.pasos[0].regla == "preparacion"
    assert [p.regla for p in sol.pasos[1:-1]] == ["columna_suma"] * 4
    assert "7 + 9 = 16" in sol.pasos[1].explicacion and "llevamos 1" in sol.pasos[1].explicacion
    assert sol.pasos[-1].regla == "resultado"


def test_prestamos_en_cadena_se_explican():
    sol = resolver_columnas("1000 − 1")
    textos = " ".join(p.explicacion for p in sol.pasos)
    assert "pedimos prestado" in textos
    assert "ya habíamos prestado" in textos       # el 0 que también tiene que pedir


def test_resta_negativa_explica_que_se_resta_al_reves():
    sol = resolver_columnas("5 − 12")
    assert "al revés" in sol.pasos[0].explicacion
    assert sol.pasos[-1].pizarra["lineas"][-1].lstrip().startswith("−")


def test_division_con_residuo_trae_nota():
    sol = resolver_columnas("7845 ÷ 12")
    assert "cociente 653 y residuo 9" in sol.nota
    assert sol.decimal_exacto is True              # termina: 653.75


def test_division_que_no_termina_avisa():
    sol = resolver_columnas("1 ÷ 3")
    assert sol.decimal_exacto is False
    assert "no termina" in sol.nota and "no se redondeó" in sol.nota


def test_division_decimal_explica_mover_la_coma():
    sol = resolver_columnas("4.5 ÷ 0.25")
    assert "movemos la coma" in sol.pasos[0].explicacion and "450 ÷ 25" in sol.pasos[0].explicacion


def test_multiplicacion_decimal_explica_la_coma():
    sol = resolver_columnas("1.2 × 0.03")
    assert sol.pasos[-1].regla == "decimales"
    assert "3 lugares" in sol.pasos[-1].explicacion or "3 lugar" in sol.pasos[-1].explicacion


def test_a_dict_serializable():
    import json
    sol = resolver_columnas("123 × 45")
    datos = json.loads(json.dumps(sol.a_dict(), ensure_ascii=False))
    assert datos["resultado"] == "5535"
    assert datos["pasos"][1]["pizarra"]["lineas"]


# ---------------------------------------------------------------------------
# 2. Errores
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("texto", [
    "", "   ", "5", "2 + 3 × 4", "(2 + 3) × 4", "2 + x", "-5 + 3", "5 + -3", "2 +", "abc",
    "1 + 2 − 3", "2 × 3 × 4", "10 ÷ 2 ÷ 5", "1 − 2 − 3", "√4 + 1", "3 1/2 + 1",
    "1 + 2 + 3 + 4 + 5 + 6", "1.1234567 + 1", "123456789 × 2", "1 ÷ 1234567",
    "1234567890123 ÷ 2", "1234567890123456 + 1",
])
def test_errores_de_entrada(texto):
    with pytest.raises(ErrorDeEntrada) as e:
        resolver_columnas(texto)
    assert str(e.value)


@pytest.mark.parametrize("texto", ["5 ÷ 0", "0 ÷ 0", "5 / 0.0"])
def test_division_entre_cero(texto):
    with pytest.raises(ErrorMatematico):
        resolver_columnas(texto)


# ---------------------------------------------------------------------------
# 3. Al azar contra la aritmética exacta
# ---------------------------------------------------------------------------

def _num(rng, max_cifras=6, decimales=True):
    ip = str(rng.randint(0, 10 ** rng.randint(1, max_cifras) - 1))
    if decimales and rng.random() < 0.4:
        return ip + "." + str(rng.randint(0, 10 ** rng.randint(1, 3) - 1)).zfill(rng.randint(1, 3))[:3]
    return ip


def _caso(rng):
    op = rng.choice(["+", "−", "×", "÷"])
    if op == "+":
        return " + ".join(_num(rng, 7) for _ in range(rng.randint(2, 5))), op
    if op == "×":
        return f"{_num(rng, 4)} × {_num(rng, 4)}", op
    if op == "÷":
        return f"{_num(rng, 7)} ÷ {_num(rng, 3)}", op
    return f"{_num(rng, 8)} − {_num(rng, 8)}", op


def _esperado(texto, op):
    t = texto.replace("−", "-").replace("×", "*").replace("÷", "/")
    nums = [Fraction(Decimal(x)) for x in t.replace("+", " ").replace("*", " ").replace("/", " ")
            .replace("-", " ").split()]
    if op == "+":
        return sum(nums)
    if op == "−":
        return nums[0] - nums[1]
    if op == "×":
        return nums[0] * nums[1]
    return nums[0] / nums[1]


def _marcas_validas(sol):
    for p in sol.pasos:
        pz = p.pizarra
        assert pz and pz["lineas"], f"paso {p.numero} sin pizarra"
        for l, a, b in pz["marcas"]:
            assert 0 <= l < len(pz["lineas"]), (p.numero, l, len(pz["lineas"]))
            assert 0 <= a < b <= len(pz["lineas"][l]), (p.numero, l, a, b, pz["lineas"][l])


def test_azar_contra_python():
    rng = random.Random(2026)
    hechas = 0
    for _ in range(1500):
        texto, op = _caso(rng)
        try:
            sol = resolver_columnas(texto)
        except ErrorMatematico:
            assert op == "÷" and Fraction(Decimal(texto.split("÷")[1])) == 0
            continue
        esp = _esperado(texto, op)
        got = valor(sol)
        if op == "÷" and not sol.decimal_exacto:
            # cortado en 4 decimales: debe quedar por debajo y a menos de 1/10000
            assert got <= esp < got + Fraction(1, 10 ** 4), f"{texto}: {got} vs {esp}"
        else:
            assert got == esp, f"{texto}: motor={got} python={esp}"
        _marcas_validas(sol)
        assert len(sol.pasos) < 250
        assert all(p.explicacion and p.motivo for p in sol.pasos)
        hechas += 1
    assert hechas > 1400


def test_division_entera_cociente_y_residuo():
    rng = random.Random(5)
    for _ in range(300):
        n, d = rng.randint(0, 10 ** 8), rng.randint(1, 10 ** 4)
        sol = resolver_columnas(f"{n} ÷ {d}")
        if n % d:
            assert f"cociente {n // d} y residuo {n % d}" in sol.nota
        else:
            assert sol.nota == "" and valor(sol) == n // d


# ---------------------------------------------------------------------------
# 4. La pizarra final muestra el resultado
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("texto", ["4567 + 289", "3.5 + 2.25", "905 − 267", "5 − 12", "123 × 45", "1.2 × 0.03",
                                   "999 + 1", "1000 − 1"])
def test_pizarra_final_muestra_el_resultado(texto):
    sol = resolver_columnas(texto)
    ultima = sol.pasos[-1].pizarra["lineas"][-1]
    limpio = ultima.replace("=", "").replace(" ", "")
    esperado = sol.resultado
    # en decimales la pizarra puede conservar ceros finales (0.50): se comparan como números
    assert Fraction(limpio.replace("−", "-")) == Fraction(esperado.replace("−", "-"))


def test_pizarra_final_de_la_division():
    sol = resolver_columnas("7845 ÷ 12")
    cociente = sol.pasos[-1].pizarra["lineas"][2].split("│")[1].strip()
    assert cociente == "653.75"


def test_la_operacion_resaltada_aparece_en_la_explicacion():
    """El resaltador marca `operacion` dentro de la explicación: tienen que coincidir
    (si no, el amarillo cubriría un pedazo equivocado, como '0 − 1' dentro de '10 − 1')."""
    rng = random.Random(77)
    revisados = 0
    for _ in range(600):
        texto, op = _caso(rng)
        try:
            sol = resolver_columnas(texto)
        except ErrorMatematico:
            continue
        for p in sol.pasos:
            if p.operacion and p.regla in ("columna_suma", "columna_resta", "fila_mult", "div_bajar"):
                assert p.operacion in p.explicacion, f"{texto!r} paso {p.numero}: {p.operacion!r} no está en {p.explicacion!r}"
                # y no debe quedar "pegado" a otro número (como el 0 de '10')
                i = p.explicacion.find(p.operacion)
                antes = p.explicacion[i - 1] if i > 0 else " "
                assert not antes.isdigit(), f"{texto!r} paso {p.numero}: resalta dentro de un número"
                revisados += 1
    assert revisados > 500
