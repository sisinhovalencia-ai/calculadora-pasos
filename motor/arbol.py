"""Árbol de una expresión aritmética.

Nodos:
  Num(valor)            un número exacto (Fraction)
  Frac(num, den)        una fracción ESCRITA que se puede simplificar (6/3, 4/6, 0/5).
                        Las irreducibles (1/2, 7/2) son simplemente Num.
  Var(nombre)           la incógnita de una ecuación (x); solo existe al resolver ecuaciones
  Porc(valor)           un porcentaje escrito (20%, 12.5%); valor = 20, 12.5
  Mixto(ent, num, den)  un número mixto escrito (3 1/2)
  Raiz(indice, hijo)    raíz de índice 2 (√), 3 (∛) o 4 (∜) de `hijo`
  Cociente(num, den)    una fracción con letras (d/t), solo para DIBUJAR fórmulas como fracción
  Neg(hijo)             signo menos aplicado a algo que aún no es número
  Paren(hijo)           paréntesis (se conservan para mostrarlos tal cual)
  BinOp(op, izq, der)   op en  + - * / ^

Los nodos son inmutables. Para "cambiar" algo se construye un árbol nuevo.
Se comparan por identidad (`is`), no por valor: dos `Num(2)` distintos son
nodos distintos aunque valgan lo mismo.
"""

from dataclasses import dataclass
from fractions import Fraction
from typing import Iterator, Union


@dataclass(frozen=True, eq=False)
class Num:
    valor: Fraction


@dataclass(frozen=True, eq=False)
class Frac:
    num: int      # puede ser negativo
    den: int      # siempre positivo


@dataclass(frozen=True, eq=False)
class Var:
    nombre: str


@dataclass(frozen=True, eq=False)
class Porc:
    valor: Fraction     # el número que acompaña al %, no dividido entre 100


@dataclass(frozen=True, eq=False)
class Mixto:
    ent: int
    num: int
    den: int


@dataclass(frozen=True, eq=False)
class Raiz:
    indice: int
    hijo: "Nodo"


@dataclass(frozen=True, eq=False)
class Cociente:
    num: "Nodo"
    den: "Nodo"


@dataclass(frozen=True, eq=False)
class Neg:
    hijo: "Nodo"


@dataclass(frozen=True, eq=False)
class Paren:
    hijo: "Nodo"


@dataclass(frozen=True, eq=False)
class BinOp:
    op: str
    izq: "Nodo"
    der: "Nodo"
    barra: bool = False   # True si la división se escribió con "/" (barra de fracción)
                          # y no con "÷" o ":" (que son siempre una división)


Nodo = Union[Num, Frac, Var, Porc, Mixto, Raiz, Cociente, Neg, Paren, BinOp]


def hijos(n: Nodo) -> list:
    if isinstance(n, (Neg, Paren, Raiz)):
        return [n.hijo]
    if isinstance(n, BinOp):
        return [n.izq, n.der]
    if isinstance(n, Cociente):
        return [n.num, n.den]
    return []


def con_hijos(n: Nodo, nuevos: list) -> Nodo:
    if isinstance(n, Neg):
        return Neg(nuevos[0])
    if isinstance(n, Paren):
        return Paren(nuevos[0])
    if isinstance(n, Raiz):
        return Raiz(n.indice, nuevos[0])
    if isinstance(n, BinOp):
        return BinOp(n.op, nuevos[0], nuevos[1], n.barra)
    if isinstance(n, Cociente):
        return Cociente(nuevos[0], nuevos[1])
    return n


def preorden(n: Nodo) -> Iterator[Nodo]:
    """Padre antes que hijos, de izquierda a derecha."""
    yield n
    for h in hijos(n):
        yield from preorden(h)


def postorden(n: Nodo) -> Iterator[Nodo]:
    """Hijos (izq. a der.) antes que el padre."""
    for h in hijos(n):
        yield from postorden(h)
    yield n


def reemplazar(raiz: Nodo, objetivo: Nodo, nuevo: Nodo) -> Nodo:
    """Copia de `raiz` donde el nodo `objetivo` (por identidad) pasa a ser `nuevo`."""
    if raiz is objetivo:
        return nuevo
    hs = hijos(raiz)
    if not hs:
        return raiz
    return con_hijos(raiz, [reemplazar(h, objetivo, nuevo) for h in hs])


def normalizar(n: Nodo) -> Nodo:
    """Limpieza que no cuenta como "paso" para el estudiante:
       Neg(Num)      -> Num negativo       (−3 es un número, no una operación)
       Paren(Num)    -> Num                ((5) es simplemente 5)
    """
    if isinstance(n, (Num, Frac, Var, Porc, Mixto)):
        return n
    n2 = con_hijos(n, [normalizar(h) for h in hijos(n)])
    if isinstance(n2, Neg) and isinstance(n2.hijo, Num):
        return Num(-n2.hijo.valor)
    if isinstance(n2, Paren) and isinstance(n2.hijo, Num):
        return n2.hijo
    return n2
