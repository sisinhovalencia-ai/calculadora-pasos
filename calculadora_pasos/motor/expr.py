"""Expresiones algebraicas para ESCRIBIR los pasos del álgebra (polinomios, factorizaciones,
fracciones algebraicas y radicales).

Por qué existe: SymPy simplifica solo (por ejemplo, convierte (x − 3)(x + 3)/(x − 3) en x + 3 al
crearlo), y para explicar un paso hay que poder escribir lo que SIN simplificar. Estas pequeñas
clases guardan la forma exacta que queremos mostrar, y el dibujo las escribe como en un libro:

    x² + 5x + 6          (x − 3)(x + 3)        (x² − 9)/(x − 3)        2√3 + 5        3a²b

Reglas de oro:
  - El texto que se muestra, vuelto a leer por nuestro parser, vale LO MISMO (las pruebas lo comprueban).
  - Los términos de un polinomio van de mayor a menor grado; los positivos antes que los negativos
    cuando hay empate; las letras en el orden en que las escribió el estudiante.
  - Los negativos se guardan con `ENeg` (nunca con un número negativo suelto), así el dibujo decide
    bien los signos y los paréntesis.

SymPy solo se importa cuando hace falta (al convertir), no al arrancar la aplicación.
"""

import re
from dataclasses import dataclass
from fractions import Fraction

from .arbol import Cociente, Frac, Mixto, Neg, Nodo, Num, Paren, Porc, Raiz, Var
from .errores import ErrorMatematico, ErrorMotor
from .numeros import MENOS

MAX_EXPONENTE = 20                    # exponente más grande que se desarrolla en el álgebra
_SUPER = {2: "²", 3: "³"}
_RAIZ = {2: "√", 3: "∛", 4: "∜"}


def _sp():
    import sympy
    return sympy


# ---------------------------------------------------------------------------
# Las clases
# ---------------------------------------------------------------------------

class E:
    """Una expresión algebraica lista para dibujar."""


@dataclass(frozen=True)
class ENum(E):
    v: Fraction                      # siempre >= 0: el signo menos es un ENeg


@dataclass(frozen=True)
class ESim(E):
    nombre: str                      # una letra (o π)


@dataclass(frozen=True)
class ESum(E):
    terminos: tuple                  # los restados son ENeg(término)


@dataclass(frozen=True)
class EProd(E):
    factores: tuple


@dataclass(frozen=True)
class EPot(E):
    base: E
    exp: int                         # >= 2


@dataclass(frozen=True)
class EFrac(E):
    num: E
    den: E


@dataclass(frozen=True)
class ENeg(E):
    x: E


@dataclass(frozen=True)
class ERad(E):
    indice: int                      # 2, 3 o 4
    rad: E


def num(v) -> E:
    """Un número cualquiera (entero, fracción, negativo) como ENum / ENeg(ENum)."""
    v = Fraction(v)
    return ENeg(ENum(-v)) if v < 0 else ENum(v)


def neg(x) -> E:
    return x.x if isinstance(x, ENeg) else ENeg(x)


# ---------------------------------------------------------------------------
# Dibujo: texto plano
# ---------------------------------------------------------------------------

def _entero(e: E) -> bool:
    return isinstance(e, ENum) and e.v.denominator == 1


def _atomo(e: E) -> bool:
    """¿Se puede poner solo, sin paréntesis, como denominador o base?"""
    if isinstance(e, ESim) or _entero(e):
        return True
    if isinstance(e, EPot):
        return isinstance(e.base, ESim) or _entero(e.base)
    if isinstance(e, ERad):
        return _entero(e.rad) or isinstance(e.rad, ESim)
    return False


def _con_parentesis(e: E) -> bool:
    """¿Este factor se escribe encerrado entre paréntesis dentro de un producto?"""
    return isinstance(e, (ESum, ENeg, EFrac, EProd)) or (isinstance(e, ENum) and e.v.denominator != 1)


def txt(e: E) -> str:
    return _t(e)


def _t(e: E, ctx: str = "top") -> str:
    if isinstance(e, ENum):
        return str(e.v.numerator) if e.v.denominator == 1 else f"{e.v.numerator}/{e.v.denominator}"
    if isinstance(e, ESim):
        return e.nombre
    if isinstance(e, ENeg):
        dentro = e.x
        interior = _t(dentro, "neg")
        if isinstance(dentro, (ESum, ENeg)):
            interior = f"({interior})"
        return MENOS + interior
    if isinstance(e, ESum):
        partes = []
        for i, t in enumerate(e.terminos):
            s = _t(t.x if isinstance(t, ENeg) and i > 0 else t, "sum")
            if isinstance(t, ESum):                              # una suma dentro de una suma: (x + 1) + (x − 1)
                s = f"({s})"
            if i == 0:
                partes.append(s)
            elif isinstance(t, ENeg):
                partes.append(f" {MENOS} " + (f"({s})" if isinstance(t.x, (ESum, ENeg)) else s))
            else:
                partes.append(" + " + s)
        return "".join(partes)
    if isinstance(e, EPot):
        base = _t(e.base, "base")
        if not _atomo(e.base) or (isinstance(e.base, ENum) and e.base.v.denominator != 1):
            base = f"({base})"
        return base + (_SUPER[e.exp] if e.exp in _SUPER else f"^{e.exp}")
    if isinstance(e, EFrac):
        n = _t(e.num, "frac")
        if isinstance(e.num, ESum) or (isinstance(e.num, EProd) and any(_con_parentesis(f) for f in e.num.factores)):
            n = f"({n})"
        d = _t(e.den, "frac")
        if not _atomo(e.den) and not isinstance(e.den, EPot):
            d = f"({d})"
        return f"{n}/{d}"
    if isinstance(e, ERad):
        if e.indice not in _RAIZ:
            raise ErrorMotor("Solo se dibujan raíces de índice 2, 3 o 4.")
        r = _t(e.rad, "rad")
        return _RAIZ[e.indice] + (r if (_entero(e.rad) or isinstance(e.rad, ESim)) else f"({r})")
    if isinstance(e, EProd):
        return _prod_txt(e)
    raise ErrorMotor(f"No sé dibujar {e!r}")  # pragma: no cover


def _prod_txt(e: EProd) -> str:
    piezas = []
    for f in e.factores:
        s = _t(f, "prod")
        if _con_parentesis(f):
            s = f"({s})"
        piezas.append((f, s))
    salida = piezas[0][1]
    for (f1, _s1), (f2, s2) in zip(piezas, piezas[1:]):
        salida += _separador(f1, f2) + s2
    return salida


def _letra(f: E) -> bool:
    return isinstance(f, ESim) or (isinstance(f, EPot) and isinstance(f.base, ESim))


def _base_letra(f: E):
    return f.nombre if isinstance(f, ESim) else f.base.nombre


def _separador(f1: E, f2: E) -> str:
    """Qué va entre dos factores: nada (2x, x(x + 1), (x − 3)(x + 3)) o un punto (2·3, x·x, fracción·fracción)."""
    if isinstance(f2, ENum) or isinstance(f1, EFrac) or isinstance(f2, EFrac):
        return "·"
    if isinstance(f1, ENum) and isinstance(f2, EProd):          # 2·(2x), no 2(2x)
        return "·"
    if _con_parentesis(f2):
        return ""
    if isinstance(f2, ERad):
        return ""
    if _letra(f2):
        if _letra(f1):
            if _base_letra(f1) == _base_letra(f2):
                return "·"
            if isinstance(f1, ESim) and isinstance(f2, ESim) and f1.nombre + f2.nombre == "de":
                return "·"
            if isinstance(f1, EPot) and f1.exp not in _SUPER:        # x^4y se lee mal: x^4·y
                return "·"
            return ""
        if isinstance(f1, ENum) and f1.v.denominator == 1:
            return ""
        if _con_parentesis(f1) or isinstance(f1, ERad):
            return ""
        return "·"
    if isinstance(f2, EPot):
        return "·"
    return "·"


# ---------------------------------------------------------------------------
# Dibujo: LaTeX
# ---------------------------------------------------------------------------

def tex(e: E) -> str:
    return _l(e)


def _par_l(s: str) -> str:
    return f"\\left({s}\\right)" if "\\frac" in s else f"({s})"


def _l(e: E) -> str:
    if isinstance(e, ENum):
        return str(e.v.numerator) if e.v.denominator == 1 else f"\\frac{{{e.v.numerator}}}{{{e.v.denominator}}}"
    if isinstance(e, ESim):
        return "\\pi" if e.nombre == "π" else e.nombre
    if isinstance(e, ENeg):
        s = _l(e.x)
        return "-" + (_par_l(s) if isinstance(e.x, (ESum, ENeg)) else s)
    if isinstance(e, ESum):
        partes = []
        for i, t in enumerate(e.terminos):
            s = _l(t.x if isinstance(t, ENeg) and i > 0 else t)
            if isinstance(t, ESum):
                s = _par_l(s)
            if i == 0:
                partes.append(s)
            elif isinstance(t, ENeg):
                partes.append(" - " + (_par_l(s) if isinstance(t.x, (ESum, ENeg)) else s))
            else:
                partes.append(" + " + s)
        return "".join(partes)
    if isinstance(e, EPot):
        b = _l(e.base)
        if not _atomo(e.base) or (isinstance(e.base, ENum) and e.base.v.denominator != 1):
            b = _par_l(b)
        return f"{b}^{{{e.exp}}}"
    if isinstance(e, EFrac):
        return f"\\frac{{{_l(e.num)}}}{{{_l(e.den)}}}"
    if isinstance(e, ERad):
        ind = "" if e.indice == 2 else f"[{e.indice}]"
        return f"\\sqrt{ind}{{{_l(e.rad)}}}"
    if isinstance(e, EProd):
        s = _l(e.factores[0])
        if _con_parentesis(e.factores[0]):
            s = _par_l(s)
        for f1, f2 in zip(e.factores, e.factores[1:]):
            t = _l(f2)
            if _con_parentesis(f2):
                t = _par_l(t)
            sep = _separador(f1, f2)
            s += (" \\cdot " if sep == "·" else (" " if (_letra(f1) and _letra(f2)) else "")) + t
        return s
    raise ErrorMotor(f"No sé dibujar {e!r}")  # pragma: no cover


# ---------------------------------------------------------------------------
# Del árbol que escribió el estudiante a E (conservando su forma)
# ---------------------------------------------------------------------------

def desde_arbol(n: Nodo) -> E:
    if isinstance(n, Num):
        return num(n.valor)
    if isinstance(n, Frac):
        return num(Fraction(n.num, n.den))
    if isinstance(n, Porc):
        return num(Fraction(n.valor) / 100)
    if isinstance(n, Mixto):
        if n.den == 0:
            raise ErrorMatematico("No se puede dividir entre cero.")
        return num(n.ent + Fraction(n.num, n.den))
    if isinstance(n, Var):
        return ESim(n.nombre)
    if isinstance(n, Neg):
        return neg(desde_arbol(n.hijo))
    if isinstance(n, Paren):
        return desde_arbol(n.hijo)
    if isinstance(n, Raiz):
        if n.indice not in _RAIZ:
            raise ErrorMatematico("Por ahora solo manejo raíces de índice 2, 3 y 4.")
        return ERad(n.indice, desde_arbol(n.hijo))
    if isinstance(n, Cociente):
        return EFrac(desde_arbol(n.num), desde_arbol(n.den))
    izq, der = desde_arbol(n.izq), desde_arbol(n.der)
    if n.op == "+":
        return ESum(tuple((izq.terminos if isinstance(izq, ESum) and not isinstance(n.izq, Paren) else (izq,)) + (der,)))
    if n.op == "-":
        base = izq.terminos if isinstance(izq, ESum) and not isinstance(n.izq, Paren) else (izq,)
        return ESum(tuple(base) + (neg(der),))
    if n.op == "*":
        izqs = izq.factores if isinstance(izq, EProd) and not isinstance(n.izq, Paren) else (izq,)
        ders = der.factores if isinstance(der, EProd) and not isinstance(n.der, Paren) else (der,)
        return EProd(tuple(izqs) + tuple(ders))
    if n.op == "/":
        return EFrac(izq, der)
    if n.op == "^":
        if isinstance(der, ENum) and der.v.denominator in _RAIZ and der.v.numerator >= 1:   # a^(p/q) = raíz q-ésima de a^p
            p_, q_ = der.v.numerator, der.v.denominator
            return ERad(q_, izq if p_ == 1 else EPot(izq, p_))
        if not (isinstance(der, ENum) and der.v.denominator == 1):
            raise ErrorMatematico("Por ahora solo manejo exponentes enteros positivos en el álgebra.")
        k = int(der.v)
        if k > MAX_EXPONENTE:
            raise ErrorMatematico(f"En el álgebra el exponente máximo es {MAX_EXPONENTE}: con exponentes más grandes "
                                  f"los resultados son larguísimos y la calculadora tardaría demasiado.")
        if k == 0:
            return ENum(Fraction(1))
        if k == 1:
            return izq
        return EPot(izq, k)
    raise ErrorMotor(f"Operador desconocido: {n.op}")  # pragma: no cover


# ---------------------------------------------------------------------------
# De E a SymPy (para verificar) y de SymPy a E (forma canónica de un libro)
# ---------------------------------------------------------------------------

def a_sympy(e: E, S: dict):
    sp = _sp()
    if isinstance(e, ENum):
        return sp.Rational(e.v.numerator, e.v.denominator)
    if isinstance(e, ESim):
        return sp.pi if e.nombre == "π" else S.setdefault(e.nombre, sp.Symbol(e.nombre))
    if isinstance(e, ENeg):
        return -a_sympy(e.x, S)
    if isinstance(e, ESum):
        return sp.Add(*[a_sympy(t, S) for t in e.terminos])
    if isinstance(e, EProd):
        return sp.Mul(*[a_sympy(f, S) for f in e.factores])
    if isinstance(e, EPot):
        return a_sympy(e.base, S) ** e.exp
    if isinstance(e, EFrac):
        d = a_sympy(e.den, S)
        if d == 0:
            raise ErrorMatematico("No se puede dividir entre cero.")
        return a_sympy(e.num, S) / d
    if isinstance(e, ERad):
        return sp.root(a_sympy(e.rad, S), e.indice)
    raise ErrorMotor(f"No sé convertir {e!r}")  # pragma: no cover


def _pos(e, orden: dict) -> tuple:
    return tuple(sorted(orden.get(str(s), 99) for s in e.free_symbols))


def _grados(t, orden: dict) -> tuple:
    """(−grado total, −exponente de cada letra en orden): los términos de mayor grado van primero."""
    pot = t.as_powers_dict()
    expo = {}
    for base, ex in pot.items():
        if base.is_Symbol and ex.is_Integer and ex > 0:
            expo[str(base)] = int(ex)
    total = sum(expo.values())
    letras = sorted(orden, key=lambda k: orden[k])
    resto = sorted(k for k in expo if k not in orden)
    vec = tuple(-expo.get(k, 0) for k in letras + resto)
    return (-total, vec)


def _clave_termino(t, orden: dict):
    negativo = 1 if t.as_coeff_Mul()[0] < 0 else 0
    return (_grados(t, orden), negativo, str(t))


def _clave_factor(f, orden: dict):
    """Orden de los factores en un producto: primero las letras; luego los paréntesis por grado y
    término independiente (x − 3)(x + 3); y, si empatan, (x − y) antes que (x + y)."""
    sp = _sp()
    if f.is_Add:
        grado = sp.Poly(f, *sorted(f.free_symbols, key=str)).total_degree() if f.free_symbols else 0
        const = f.subs({s: 0 for s in f.free_symbols})
        c = const if const.is_Rational else sp.Integer(0)
        negativos = sum(1 for t in sp.Add.make_args(f) if t.as_coeff_Mul()[0] < 0)
        return (1, grado, float(c), _pos(f, orden), -negativos, str(f))
    return (0, 0, 0.0, _pos(f, orden), 0, str(f))


def desde_sympy(e, orden: dict) -> E:
    """Forma canónica y limpia (la de un libro) de una expresión de SymPy."""
    sp = _sp()
    if e == sp.pi:
        return ESim("π")
    if e.is_Integer or e.is_Rational:
        return num(Fraction(int(e.p), int(e.q)))
    if e.is_Symbol:
        return ESim(str(e))
    if e.is_Add:
        terminos = sorted(sp.Add.make_args(e), key=lambda t: _clave_termino(t, orden))
        salida = []
        for t in terminos:
            c = t.as_coeff_Mul()[0]
            if c < 0:
                salida.append(neg(desde_sympy(-t, orden)))
            else:
                salida.append(desde_sympy(t, orden))
        return ESum(tuple(salida))
    if e.is_Mul:
        if e.could_extract_minus_sign():
            return neg(desde_sympy(-e, orden))
        n, d = sp.fraction(e)
        if d != 1:
            return EFrac(desde_sympy(n, orden), desde_sympy(d, orden))
        coef, resto = e.as_coeff_Mul()
        letras, radicales, sumas = [], [], []
        for f in sp.Mul.make_args(resto):
            base, ex = f.as_base_exp()
            if ex.is_Rational and not ex.is_Integer:
                radicales.append(f)
            elif base.is_Add:
                sumas.append(f)
            else:
                letras.append(f)
        letras.sort(key=lambda f: (_pos(f, orden), str(f)))
        sumas.sort(key=lambda f: _clave_factor(f.as_base_exp()[0], orden) + (f.as_base_exp()[1],))
        radicales.sort(key=str)
        piezas = []
        if coef != 1:
            piezas.append(desde_sympy(coef, orden))
        piezas += [desde_sympy(f, orden) for f in radicales + letras + sumas]
        return piezas[0] if len(piezas) == 1 else EProd(tuple(piezas))
    if e.is_Pow:
        base, ex = e.as_base_exp()
        if ex.is_Integer:
            if ex > 0:
                return EPot(desde_sympy(base, orden), int(ex)) if ex > 1 else desde_sympy(base, orden)
            return EFrac(ENum(Fraction(1)), desde_sympy(base ** (-ex), orden))
        if ex.is_Rational and ex.p == 1 and ex.q in _RAIZ:
            return ERad(int(ex.q), desde_sympy(base, orden))
        if ex.is_Rational and ex.p == -1 and ex.q in _RAIZ:
            return EFrac(ENum(Fraction(1)), ERad(int(ex.q), desde_sympy(base, orden)))
        raise ErrorMatematico("Por ahora solo manejo raíces de índice 2, 3 y 4.")
    raise ErrorMotor(f"No sé dibujar {e!r}")  # pragma: no cover


def orden_de_aparicion(texto: str) -> dict:
    """Cada letra, según el orden en que la escribió el estudiante (la primera, 0)."""
    orden: dict = {}
    for ch in texto:
        if ch.isalpha() and ch != "π" and ch not in orden:
            orden[ch] = len(orden)
    return orden


def tiene_letras(texto: str) -> bool:
    """¿El texto trae letras (incógnitas), sin contar las palabras de/raiz/sqrt/√?"""
    limpio = re.sub(r"(?<![A-Za-z])(?:de|raiz|raíz|sqrt)(?![A-Za-z])", " ", texto, flags=re.IGNORECASE)
    return re.search(r"[A-Za-zπ]", limpio) is not None
