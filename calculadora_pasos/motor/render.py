"""Convierte el árbol en texto plano o LaTeX.

Regla de oro: el texto que se muestra, si se vuelve a escribir en la
calculadora, tiene que dar el MISMO resultado. Por eso se ponen paréntesis
alrededor de negativos y fracciones cuando, sin ellos, cambiaría el significado
(ej.: 2 ÷ (1/2) no es lo mismo que 2 ÷ 1/2).
"""

from fractions import Fraction

from .arbol import BinOp, Cociente, Frac, Mixto, Neg, Nodo, Num, Paren, Porc, Raiz, Var
from .numeros import MENOS, formatear, formatear_latex, se_ve_como_fraccion

_SIMBOLO_TEXTO = {"+": " + ", "-": f" {MENOS} ", "*": " × ", "/": " ÷ ", "^": "^"}
_SIMBOLO_LATEX = {"+": " + ", "-": " - ", "*": " \\cdot ", "/": " \\div ", "^": "^"}


def _par_latex(interior: str) -> str:
    """Paréntesis para LaTeX: se estiran (\\left/\\right) solo si dentro hay una fracción."""
    if "\\frac" in interior:
        return f"\\left({interior}\\right)"
    return f"({interior})"


_SIMBOLO_RAIZ = {2: "√", 3: "∛", 4: "∜"}


def _hijo_raiz_texto(hijo: Nodo, decimales: bool) -> str:
    """Lo que va después de √: un entero o decimal sin signo va pegado (√9); todo lo
    demás (fracciones, negativos, paréntesis) va entre paréntesis para no cambiar el sentido."""
    t = a_texto(hijo, decimales)
    if isinstance(hijo, Paren):
        return t
    if isinstance(hijo, (Num, Raiz)) and "/" not in t and not t.startswith(MENOS):
        return t
    return f"({t})"


def _envuelve_cociente(hijo: Nodo) -> bool:
    """¿Hace falta paréntesis alrededor de esto cuando va en un numerador o denominador de a/b?"""
    return isinstance(hijo, (BinOp, Neg, Cociente)) or (isinstance(hijo, Num) and hijo.valor < 0)


def _necesita_parentesis(hijo: Nodo, op: str, lado: str, decimales: bool) -> bool:
    if isinstance(hijo, Mixto):
        return op in ("*", "/", "^")
    if isinstance(hijo, Frac):
        return op in ("*", "/", "^") or (hijo.num < 0 and lado == "der")
    if isinstance(hijo, Num):
        if hijo.valor < 0 and (lado == "der" or op == "^"):
            return True
        if se_ve_como_fraccion(hijo.valor, decimales) and op in ("*", "/", "^"):
            return True
        return False
    if isinstance(hijo, Neg):
        return lado == "der" or op == "^"
    return False


def a_texto(n: Nodo, decimales: bool = False) -> str:
    if isinstance(n, Num):
        return formatear(n.valor, decimales)
    if isinstance(n, Frac):
        return f"{MENOS if n.num < 0 else ''}{abs(n.num)}/{n.den}"
    if isinstance(n, Var):
        return n.nombre
    if isinstance(n, Cociente):
        partes = []
        for h in (n.num, n.den):
            t = a_texto(h, decimales)
            partes.append(f"({t})" if _envuelve_cociente(h) else t)
        return partes[0] + "/" + partes[1]
    if isinstance(n, Porc):
        return f"{formatear(n.valor, decimales)}%"
    if isinstance(n, Mixto):
        return f"{n.ent} {n.num}/{n.den}"
    if isinstance(n, Raiz):
        return _SIMBOLO_RAIZ[n.indice] + _hijo_raiz_texto(n.hijo, decimales)
    if isinstance(n, Paren):
        return "(" + a_texto(n.hijo, decimales) + ")"
    if isinstance(n, Neg):
        interior = a_texto(n.hijo, decimales)
        if isinstance(n.hijo, Neg):
            interior = f"({interior})"
        return MENOS + interior
    # BinOp
    if n.op == "*" and isinstance(n.izq, Num) and isinstance(n.der, Var):      # 2x, no 2 × x
        t = a_texto(n.izq, decimales)
        return f"({t})" + n.der.nombre if se_ve_como_fraccion(n.izq.valor, decimales) else t + n.der.nombre
    partes = []
    for lado, hijo in (("izq", n.izq), ("der", n.der)):
        t = a_texto(hijo, decimales)
        if _necesita_parentesis(hijo, n.op, lado, decimales):
            t = f"({t})"
        partes.append(t)
    return partes[0] + _SIMBOLO_TEXTO[n.op] + partes[1]


def a_latex(n: Nodo, decimales: bool = False) -> str:
    if isinstance(n, Num):
        return formatear_latex(n.valor, decimales)
    if isinstance(n, Frac):
        return f"{'-' if n.num < 0 else ''}\\frac{{{abs(n.num)}}}{{{n.den}}}"
    if isinstance(n, Var):
        return n.nombre
    if isinstance(n, Cociente):
        return f"\\frac{{{a_latex(n.num, decimales)}}}{{{a_latex(n.den, decimales)}}}"
    if isinstance(n, Porc):
        return f"{formatear_latex(n.valor, decimales)}\\%"
    if isinstance(n, Mixto):
        return f"{n.ent}\\frac{{{n.num}}}{{{n.den}}}"
    if isinstance(n, Raiz):
        interior = a_latex(n.hijo, decimales)
        if isinstance(n.hijo, Paren):          # √(…) se dibuja sin paréntesis: el radical ya agrupa
            interior = a_latex(n.hijo.hijo, decimales)
        indice = "" if n.indice == 2 else f"[{n.indice}]"
        return f"\\sqrt{indice}{{{interior}}}"
    if isinstance(n, Paren):
        return _par_latex(a_latex(n.hijo, decimales))
    if isinstance(n, Neg):
        interior = a_latex(n.hijo, decimales)
        if isinstance(n.hijo, Neg):
            interior = _par_latex(interior)
        return "-" + interior
    if n.op == "*" and isinstance(n.izq, Num) and isinstance(n.der, Var):      # 2x
        t = a_latex(n.izq, decimales)
        return (_par_latex(t) if se_ve_como_fraccion(n.izq.valor, decimales) else t) + n.der.nombre
    izq = a_latex(n.izq, decimales)
    der = a_latex(n.der, decimales)
    if _necesita_parentesis(n.izq, n.op, "izq", decimales):
        izq = _par_latex(izq)
    if n.op == "^":
        # el exponente va entre llaves y no necesita paréntesis propios
        return f"{izq}^{{{der}}}"
    if _necesita_parentesis(n.der, n.op, "der", decimales):
        der = _par_latex(der)
    return izq + _SIMBOLO_LATEX[n.op] + der


def operacion_texto(op: str, a: Fraction, b: Fraction, decimales: bool) -> str:
    """'3 + 4', '5 − (−3)', '(−2)^3' ... para mostrar la operación resuelta."""
    nodo = BinOp(op, Num(a), Num(b))
    return a_texto(nodo, decimales)
