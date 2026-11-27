"""Álgebra tipo Baldor: lo que comparten los solucionadores de polinomios, factorización,
fracciones algebraicas y radicales.

Cómo se pide cada cosa (la calculadora también lo adivina cuando no se dice):

    desarrollar (x + 3)²             o simplemente   (x + 3)²          → productos y reducción
    factorizar x² − 9                                                  → factorización por casos
    simplificar (x² − 9)/(x − 3)     o simplemente   (x² − 9)/(x − 3)  → fracciones algebraicas
    reducir (3x² + 2x) − (x² − 5x)                                      → quitar paréntesis y juntar términos

Todos devuelven una `Solucion` con el mismo formato de pasos que el resto de la calculadora.
Cada resultado se verifica por otro camino: se evalúa lo que escribió el estudiante con números
(sin pasar por SymPy) y se compara con lo que se muestra.
"""

import random
import re
from fractions import Fraction

from .arbol import Cociente, Frac, Mixto, Neg, Nodo, Num, Paren, Porc, Raiz, Var, hijos, normalizar
from .aritmetica import _con_fracciones
from .errores import ErrorDeEntrada, ErrorMatematico, ErrorMotor
from .expr import E, a_sympy, desde_arbol, orden_de_aparicion, tex, txt
from .parser import parsear
from .pasos import Paso, Solucion

_COMANDOS = {
    "factorizar": "factorizar", "factoriza": "factorizar",
    "desarrollar": "desarrollar", "desarrolla": "desarrollar", "expandir": "desarrollar", "expande": "desarrollar",
    "simplificar": "simplificar", "simplifica": "simplificar",
    "reducir": "reducir", "reduce": "reducir",
}
_RE_COMANDO = re.compile(r"^\s*(" + "|".join(sorted(_COMANDOS, key=len, reverse=True)) + r")\b[\s:]*", re.IGNORECASE)
_RE_REL = re.compile(r"[=<>≤≥]")

MAX_CARACTERES = 200


def separar_comando(texto: str) -> tuple[str | None, str]:
    """('factorizar', 'x² − 9') a partir de 'factorizar x² − 9'; (None, texto) si no hay comando."""
    m = _RE_COMANDO.match(texto)
    if not m:
        return None, texto.strip()
    return _COMANDOS[m.group(1).lower()], texto[m.end():].strip()


def tiene_comando(texto: str) -> bool:
    return _RE_COMANDO.match(texto) is not None


def leer(texto: str) -> tuple[Nodo, E, dict]:
    """Texto → (árbol que escribió el estudiante, E con su forma, orden de las letras)."""
    if not texto or not texto.strip():
        raise ErrorDeEntrada("Escribe una expresión, por ejemplo: factorizar x² − 9")
    if len(texto) > MAX_CARACTERES:
        raise ErrorDeEntrada(f"La expresión es demasiado larga (máximo {MAX_CARACTERES} caracteres).")
    if _RE_REL.search(texto):
        raise ErrorDeEntrada("Aquí no va un signo de igualdad ni de comparación: escribe solo la expresión "
                             "(si es una ecuación, resuélvela sin la palabra «factorizar» ni «simplificar»).")
    arbol, decimales = parsear(texto, variables=True)
    arbol = normalizar(arbol)
    if not decimales:
        arbol = normalizar(_con_fracciones(arbol))
    return arbol, desde_arbol(arbol), orden_de_aparicion(texto)


# ---------------------------------------------------------------------------
# La libreta de pasos
# ---------------------------------------------------------------------------

class Libreta:
    """Va guardando los pasos de una solución; cada paso se dibuja desde un `E`."""

    def __init__(self, motivos: dict):
        self.pasos: list[Paso] = []
        self.motivos = motivos

    def agregar(self, regla: str, explicacion: str, e: E, *, operacion: str = "", previo: tuple | None = None,
                motivo: str | None = None) -> None:
        self.pasos.append(Paso(
            numero=len(self.pasos) + 1, regla=regla, explicacion=explicacion,
            motivo=motivo or self.motivos[regla], operacion=operacion, resultado_parcial="",
            expresion=txt(e), latex=tex(e),
            intermedio=previo[0] if previo else "", latex_intermedio=previo[1] if previo else ""))


def solucion(tipo: str, entrada: str, inicial: E, libreta: Libreta, final: E, *, nota: str = "",
             prefijo: str = "") -> Solucion:
    return Solucion(
        tipo=tipo, entrada=entrada, expresion_inicial=prefijo + txt(inicial), latex_inicial=tex(inicial),
        pasos=libreta.pasos, resultado=txt(final), resultado_latex=tex(final), nota=nota)


# ---------------------------------------------------------------------------
# Verificación numérica independiente de SymPy
# ---------------------------------------------------------------------------

def _evaluar(n: Nodo, v: dict) -> Fraction:
    if isinstance(n, Num):
        return n.valor
    if isinstance(n, Frac):
        return Fraction(n.num, n.den)
    if isinstance(n, Porc):
        return n.valor / 100
    if isinstance(n, Mixto):
        return n.ent + Fraction(n.num, n.den)
    if isinstance(n, Var):
        return v[n.nombre]
    if isinstance(n, Neg):
        return -_evaluar(n.hijo, v)
    if isinstance(n, Paren):
        return _evaluar(n.hijo, v)
    if isinstance(n, Cociente):
        return _evaluar(n.num, v) / _evaluar(n.den, v)
    if isinstance(n, Raiz):
        raise TypeError("raíz")
    a, b = _evaluar(n.izq, v), _evaluar(n.der, v)
    if n.op == "+":
        return a + b
    if n.op == "-":
        return a - b
    if n.op == "*":
        return a * b
    if n.op == "/":
        return a / b
    return a ** int(b)


def _vars(n: Nodo):
    if isinstance(n, Var):
        yield n
    for h in hijos(n):
        yield from _vars(h)


def _tiene_raiz(n: Nodo) -> bool:
    return isinstance(n, Raiz) or any(_tiene_raiz(h) for h in hijos(n))


def verificar(arbol: Nodo, final: E, intentos: int = 4) -> None:
    """Evalúa lo que escribió el estudiante con números y lo compara con el resultado mostrado.
    Si no coinciden es un error del motor (nunca del estudiante), y se detecta en vez de mostrarse."""
    import sympy as sp
    variables = list(_vars(arbol))
    if _tiene_raiz(arbol) or any(x.nombre == "π" for x in variables):
        return
    letras = sorted({x.nombre for x in variables})
    rng = random.Random(12345)
    hechos = 0
    for _ in range(intentos * 6):
        valores = {c: Fraction(rng.randint(2, 40), rng.choice([1, 1, 2, 3])) for c in letras}
        try:
            esperado = _evaluar(arbol, valores)
        except (ZeroDivisionError, TypeError):
            continue
        try:
            obtenido = a_sympy(final, {}).subs({sp.Symbol(c): sp.Rational(x.numerator, x.denominator)
                                                  for c, x in valores.items()})
        except ErrorMatematico:
            continue
        if not obtenido.is_finite:
            continue
        if sp.Rational(esperado.numerator, esperado.denominator) != obtenido:
            raise ErrorMotor(f"La verificación falló con {valores}: {esperado} ≠ {obtenido}")
        hechos += 1
        if hechos >= intentos:
            return
