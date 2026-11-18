"""Parser de expresiones aritméticas.

Gramática (de menor a mayor precedencia):

    expr    := term (('+' | '-') term)*
    term    := unario (('*' | '/') unario | '(' ...)*      # '(' = multiplicación implícita
    unario  := ('-' | '+') unario | potencia
    potencia:= atomo ('^' unario)?                         # asociativa a la derecha
    atomo   := NUMERO '%'?                 # 20%  (porcentaje)
             | ENTERO ENTERO '/' ENTERO    # 3 1/2  (número mixto)
             | RAIZ atomo                  # √9  ∛27  raiz(16+9)
             | LETRA                       # x   (solo al resolver ecuaciones)
             | '(' expr ')'

Consecuencias importantes (coinciden con lo que se enseña y con Python):
    -3^2   = -(3^2) = -9
    (-3)^2 = 9
    2^3^2  = 2^(3^2) = 512
    2^-3   = 1/8
    2(3+4) = 2 × (3+4)

La barra "/" entre dos números enteros se interpreta después (en aritmetica.py)
como una FRACCIÓN: 1/2 es la fracción un medio, no la división 1 ÷ 2. En cambio
"÷" y ":" son siempre una división.

Símbolos aceptados:
    multiplicar:  *  ×  ·  ⋅
    dividir:      /  ÷  :
    restar:       -  −  –  —
    potencia:     ^  **
    decimales:    punto o coma  (1.5  o  1,5)
    porcentaje:   20%      ("de" significa multiplicar:  20% de 150)
    raíz:         √  ∛  ∜  raiz(...)  raíz(...)  sqrt(...)
"""

import re
from fractions import Fraction

from .arbol import BinOp, Mixto, Neg, Nodo, Num, Paren, Porc, Raiz, Var
from .errores import ErrorDeEntrada

_MAX_LARGO = 300

_EQUIVALENCIAS = {
    "×": "*", "·": "*", "⋅": "*",
    "÷": "/", ":": "/",
    "−": "-", "–": "-", "—": "-",
}

_NUMERO = re.compile(r"\d+(?:[.,]\d+)?|[.,]\d+")
_PALABRA = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+")     # solo letras (con tildes y ñ)
_SUPERINDICES = {"²": 2, "³": 3}                          # x² se lee x^2
_RAICES = {"√": 2, "∛": 3, "∜": 4}


def _tokenizar(texto: str, variables: bool = False):
    """Devuelve (tokens, usa_decimales).
    Cada token es (tipo, valor, posicion, texto_original)."""
    tokens = []
    usa_decimales = False
    pos = 0
    while pos < len(texto):
        c = texto[pos]
        if c.isspace():
            pos += 1
            continue
        m = _NUMERO.match(texto, pos)
        if m:
            crudo = m.group(0)
            if "." in crudo or "," in crudo:
                usa_decimales = True
            tokens.append(("NUM", Fraction(crudo.replace(",", ".")), pos, crudo))
            pos = m.end()
            continue
        if texto.startswith("**", pos):
            tokens.append(("OP", "^", pos, "**"))
            pos += 2
            continue
        if c in _SUPERINDICES:
            tokens.append(("OP", "^", pos, c))
            tokens.append(("NUM", Fraction(_SUPERINDICES[c]), pos, str(_SUPERINDICES[c])))
            pos += 1
            continue
        if c == "π" and variables:
            tokens.append(("VAR", "π", pos, "π"))
            pos += 1
            continue
        if c.isalpha() and _PALABRA.match(texto, pos):
            m = _PALABRA.match(texto, pos)
            palabra = m.group(0)
            if palabra.lower() == "de":
                tokens.append(("OP", "*", pos, "de"))
            elif palabra.lower() in ("raiz", "raíz", "sqrt"):
                tokens.append(("RAIZ", 2, pos, palabra))
            elif len(palabra) == 1 and variables:
                tokens.append(("VAR", palabra, pos, palabra))
            elif variables:                    # "ma" en una fórmula = m·a (multiplicación implícita)
                for k, letra in enumerate(palabra):
                    tokens.append(("VAR", letra, pos + k, letra))
            elif len(palabra) == 1:
                raise ErrorDeEntrada(
                    f"Por ahora solo trabajo con números: no entiendo la letra '{palabra}' "
                    f"(posición {pos + 1})."
                )
            else:
                raise ErrorDeEntrada(
                    f"Por ahora solo trabajo con números: no entiendo '{palabra}' "
                    f"(posición {pos + 1})."
                )
            pos = m.end()
            continue
        if c in _RAICES:
            tokens.append(("RAIZ", _RAICES[c], pos, c))
            pos += 1
            continue
        if c == "%":
            tokens.append(("PCT", "%", pos, c))
            pos += 1
            continue
        c2 = _EQUIVALENCIAS.get(c, c)
        if c2 in "+-*/^":
            tokens.append(("OP", c2, pos, c))
        elif c2 == "(":
            tokens.append(("LP", c2, pos, c))
        elif c2 == ")":
            tokens.append(("RP", c2, pos, c))
        else:
            raise ErrorDeEntrada(f"No entiendo el símbolo '{c}' (posición {pos + 1}).")
        pos += 1
    tokens.append(("EOF", "", len(texto), ""))
    return tokens, usa_decimales


class _Parser:
    def __init__(self, tokens):
        self.t = tokens
        self.i = 0

    # --- utilidades -------------------------------------------------------
    def _ver(self):
        return self.t[self.i]

    def _tomar(self):
        tok = self.t[self.i]
        self.i += 1
        return tok

    def _es_op(self, *ops):
        tipo, val, _, _t = self._ver()
        return tipo == "OP" and val in ops

    def _entero(self, k: int) -> bool:
        """¿El token k posiciones adelante es un número entero escrito sin decimales?"""
        if self.i + k >= len(self.t):
            return False
        tipo, _, _, crudo = self.t[self.i + k]
        return tipo == "NUM" and crudo.isdigit()

    def _intentar_mixto(self):
        """Número mixto: ENTERO ENTERO '/' ENTERO (ej. 3 1/2). Devuelve Mixto o None.

        No es mixto si la fracción va seguida de '^' (3 1/2^2 sería ambiguo)."""
        if not (self._entero(0) and self._entero(1) and self.i + 3 < len(self.t)):
            return None
        _, _, _, barra = self.t[self.i + 2]
        if barra != "/" or not self._entero(3):
            return None
        sig = self.t[self.i + 4] if self.i + 4 < len(self.t) else ("EOF", "", 0, "")
        if sig[0] == "OP" and sig[1] == "^":
            return None
        ent, num, den = self.t[self.i][1], self.t[self.i + 1][1], self.t[self.i + 3][1]
        self.i += 4
        return Mixto(int(ent), int(num), int(den))

    # --- gramática --------------------------------------------------------
    def expr(self) -> Nodo:
        nodo = self.term()
        while self._es_op("+", "-"):
            op = self._tomar()[1]
            nodo = BinOp(op, nodo, self.term())
        return nodo

    def term(self) -> Nodo:
        nodo = self.unario()
        while True:
            if self._es_op("*", "/"):
                tok = self._tomar()
                op = tok[1]
                # "/" escrito con la barra = posible fracción; "÷" y ":" = división
                barra = op == "/" and tok[3] == "/"
                nodo = BinOp(op, nodo, self.unario(), barra)
            elif self._ver()[0] in ("LP", "RAIZ", "VAR"):  # multiplicación implícita: 2(3+4), 2√9, 2x
                nodo = BinOp("*", nodo, self.unario())
            else:
                return nodo

    def unario(self) -> Nodo:
        if self._es_op("-"):
            self._tomar()
            return Neg(self.unario())
        if self._es_op("+"):
            self._tomar()
            return self.unario()
        return self.potencia()

    def potencia(self) -> Nodo:
        base = self.atomo()
        if self._es_op("^"):
            self._tomar()
            return BinOp("^", base, self.unario())
        return base

    def atomo(self) -> Nodo:
        tipo, val, pos, texto = self._ver()
        if tipo == "NUM":
            mixto = self._intentar_mixto()
            if mixto is not None:
                return mixto
            self._tomar()
            if self._ver()[0] == "PCT":
                self._tomar()
                return Porc(val)
            return Num(val)
        if tipo == "VAR":
            self._tomar()
            return Var(val)
        if tipo == "RAIZ":
            self._tomar()
            if self._ver()[0] not in ("NUM", "LP", "RAIZ", "VAR"):
                raise ErrorDeEntrada(
                    f"Después de '{texto}' debe ir un número o un paréntesis (posición {pos + 1})."
                )
            return Raiz(val, self.atomo())
        if tipo == "LP":
            self._tomar()
            if self._ver()[0] == "RP":
                raise ErrorDeEntrada(f"Hay un paréntesis vacío (posición {pos + 1}).")
            nodo = self.expr()
            if self._ver()[0] != "RP":
                raise ErrorDeEntrada("Falta cerrar un paréntesis: cada '(' necesita su ')'.")
            self._tomar()
            return Paren(nodo)
        if tipo == "EOF":
            raise ErrorDeEntrada("La expresión está incompleta: después del último operador falta un número.")
        if tipo == "RP":
            raise ErrorDeEntrada(f"Hay un ')' que no tiene su '(' (posición {pos + 1}).")
        raise ErrorDeEntrada(f"No puede haber un '{texto}' en la posición {pos + 1}: ahí debería ir un número o un paréntesis.")


def parsear(texto: str, variables: bool = False) -> tuple[Nodo, bool]:
    """Texto -> (árbol, usa_decimales). Con `variables=True` acepta una letra como incógnita (x)."""
    if texto is None or not texto.strip():
        raise ErrorDeEntrada("Escribe una operación para resolver.")
    if len(texto) > _MAX_LARGO:
        raise ErrorDeEntrada(f"La expresión es demasiado larga (máximo {_MAX_LARGO} caracteres).")

    tokens, usa_decimales = _tokenizar(texto, variables)
    p = _Parser(tokens)
    nodo = p.expr()

    tipo, val, pos, texto_tok = p._ver()
    if tipo == "RP":
        raise ErrorDeEntrada(f"Hay un ')' que no tiene su '(' (posición {pos + 1}).")
    if tipo != "EOF":
        raise ErrorDeEntrada(
            f"Falta un operador (+, −, ×, ÷) antes de '{texto_tok}' (posición {pos + 1})."
        )
    return nodo, usa_decimales
