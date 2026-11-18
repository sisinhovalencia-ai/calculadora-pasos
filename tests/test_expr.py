"""Pruebas del dibujo de expresiones algebraicas (motor/expr.py).

Regla de oro: el texto que se dibuja, vuelto a leer por el parser, vale EXACTAMENTE lo mismo.
"""

import random
from fractions import Fraction

import sympy as sp

from motor.arbol import normalizar
from motor.expr import (EFrac, ENeg, ENum, EPot, EProd, ESim, ESum, a_sympy, desde_arbol, desde_sympy, tex, tiene_letras,
                        txt)
from motor.parser import parsear

LETRAS = list("abcdxyzmn")


def leer(texto: str):
    arbol, _ = parsear(texto, variables=True)
    return a_sympy(desde_arbol(normalizar(arbol)), {})


def _monomio(rng, letras):
    m = sp.Integer(rng.choice([1, 1, 2, 3, 5, 7, -1, -2, -3, -6]))
    for L in rng.sample(letras, rng.randint(0, 2)):
        m *= sp.Symbol(L) ** rng.randint(1, 4)
    return m


def _poli(rng, letras, n=None):
    return sp.Add(*[_monomio(rng, letras) for _ in range(n or rng.randint(1, 4))])


def _expr(rng, letras):
    t = rng.random()
    if t < 0.30:
        return _poli(rng, letras)
    if t < 0.50:
        return _poli(rng, letras, 2) * _poli(rng, letras, 2)
    if t < 0.62:
        return _poli(rng, letras, 2) ** rng.randint(2, 4)
    if t < 0.80:
        d = _poli(rng, letras, 2)
        return _poli(rng, letras) / d if d != 0 else _poli(rng, letras)
    if t < 0.90:
        return _poli(rng, letras) / rng.choice([2, 3, 5, 7])
    return sp.Rational(rng.randint(-9, 9), rng.randint(1, 9)) * _poli(rng, letras, 2)


def test_dibujar_y_releer_al_azar():
    rng = random.Random(100)
    hechas = 0
    for _ in range(700):
        letras = rng.sample(LETRAS, 3)
        e = _expr(rng, letras)
        if e == 0:
            continue
        orden = {l: i for i, l in enumerate(letras)}
        texto = txt(desde_sympy(e, orden))
        assert tex(desde_sympy(e, orden))                     # el LaTeX también se arma
        assert sp.cancel(sp.together(leer(texto) - e)) == 0, f"{texto!r} no vale lo mismo que {e}"
        hechas += 1
    assert hechas > 600


def test_signos_y_parentesis():
    x, y = ESim("x"), ESim("y")
    uno = ENum(Fraction(1))
    assert txt(ESum((x, ENeg(ESum((y, uno)))))) == "x − (y + 1)"
    assert txt(ENeg(ESum((x, y)))) == "−(x + y)"
    assert txt(EProd((ESum((x, ENeg(uno))), ESum((x, uno))))) == "(x − 1)(x + 1)"
    assert txt(EProd((ENum(Fraction(2)), x))) == "2x"
    assert txt(EProd((x, x))) == "x·x"                         # dos x seguidas no se escriben «xx»
    assert txt(EProd((ESim("d"), ESim("e")))) == "d·e"         # «de» sería la palabra «de»
    assert txt(EProd((ENum(Fraction(2)), EProd((ENum(Fraction(2)), x))))) == "2·(2x)"
    assert txt(EFrac(x, ESum((y, uno)))) == "x/(y + 1)"
    assert txt(EFrac(ESum((x, uno)), y)) == "(x + 1)/y"
    assert txt(EPot(ESum((x, uno)), 2)) == "(x + 1)²"
    assert txt(EFrac(uno, EPot(ESum((x, uno)), 2))) == "1/(x + 1)²"
    assert txt(EPot(x, 5)) == "x^5"
    assert tex(EFrac(x, y)) == "\\frac{x}{y}"


def test_orden_de_los_terminos_y_factores():
    x, y, a = sp.symbols("x y a")
    o = {"x": 0, "y": 1, "a": 2}
    assert txt(desde_sympy(x**2 + 5*x + 6, o)) == "x² + 5x + 6"
    assert txt(desde_sympy(1 - x, o)) == "−x + 1"              # mayor a menor grado
    assert txt(desde_sympy(sp.expand((x - 3) * (x + 3)), o)) == "x² − 9"
    assert txt(desde_sympy(x*y + x**2 + y**2, o)) == "x² + xy + y²"
    assert txt(desde_sympy(sp.Mul(x + 3, x - 3, evaluate=False), o)) == "(x − 3)(x + 3)"
    assert txt(desde_sympy(sp.Mul(x - y, x + y, evaluate=False), o)) == "(x − y)(x + y)"
    assert txt(desde_sympy(sp.Rational(1, 2) * x, o)) == "x/2"


def test_tiene_letras():
    assert tiene_letras("x + 1") and tiene_letras("2π") and tiene_letras("ab")
    assert not tiene_letras("2 + 3") and not tiene_letras("20% de 150") and not tiene_letras("√12")
    assert not tiene_letras("raiz(25) + sqrt(4)")
