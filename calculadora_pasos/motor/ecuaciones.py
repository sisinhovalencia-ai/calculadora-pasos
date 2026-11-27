"""Ecuaciones y desigualdades lineales de una incógnita, paso a paso.

    2x + 3 = 11         3x − 5 = 2x + 7        2(x + 3) = 14        x/2 + 1 = 5
    2x + 3 < 11         −2x + 1 ≥ 7            3(x − 1) > 2x + 4    (también <=, >=)
    x + 1 = x + 2   (sin solución)             2x + 2 = 2(x + 1)   (infinitas soluciones)

Método (el de la escuela, con tres cuidados didácticos):
  1. Propiedad distributiva y reducción de términos semejantes, en pasos SEPARADOS.
  2. Las incógnitas se juntan del lado donde su coeficiente queda POSITIVO (así casi nunca
     hay que dividir entre un negativo). Si queda a la derecha, al final se lee al revés.
  3. Cada operación se muestra escrita en los DOS lados antes de simplificarla:
     "2x + 2 − 3x = 3x − 9 − 3x"  →  "−x + 2 = −9".

En una desigualdad, el sentido (<, >) se invierte al dividir entre un número negativo y al
leerla al revés; el motor lo explica en cada caso. Al final se COMPRUEBA con el motor de
aritmética (otro camino de cálculo): si algún paso estuviera mal, se detecta en vez de mostrarse.

Cada lado se lleva a la forma  a·x + b  (con a y b exactos, `Fraction`).
"""

import re
from fractions import Fraction

from .arbol import (BinOp, Frac, Mixto, Neg, Nodo, Num, Paren, Porc, Raiz, Var, con_hijos, hijos,
                    normalizar)
from .aritmetica import _calcular, _calcular_raiz, _con_fracciones, resolver
from .errores import ErrorDeEntrada, ErrorMatematico, ErrorMotor
from .numeros import MENOS, decimal_aproximado, formatear, formatear_latex, se_ve_como_fraccion
from .parser import parsear
from .pasos import Paso, Solucion
from .render import a_latex, a_texto

_NO_LINEAL = ("Esto no es lineal: tiene la incógnita multiplicada por sí misma o elevada a una "
              "potencia. Por ahora solo resuelvo ecuaciones y desigualdades lineales, como 2x + 3 = 11.")
_NO_SOPORTADO = ("Todavía no resuelvo ecuaciones con la incógnita en un denominador, una raíz o un exponente. "
                 "Por ahora solo resuelvo ecuaciones y desigualdades lineales, como 2x + 3 = 11.")

_INVERSA = {"<": ">", ">": "<", "≤": "≥", "≥": "≤", "=": "="}
_REL_LATEX = {"<": "<", ">": ">", "≤": "\\leq", "≥": "\\geq", "=": "="}
_REL = re.compile(r"<=|>=|≤|≥|<|>")

_MOTIVO = {
    "distribuir": "El número de afuera multiplica a TODO lo que está dentro del paréntesis, no solo al primer término.",
    "simplificar": "Antes de despejar conviene dejar cada lado lo más sencillo posible: así se ve claro cuántas "
                   "incógnitas hay y cuántos números sueltos.",
    "mover_x": "Para despejar la incógnita hay que juntarlas todas en un solo lado. Lo que se hace a un lado se "
               "hace al otro, y así se mantiene la igualdad (o la desigualdad). Se juntan donde el coeficiente "
               "queda positivo, para evitar dividir entre un negativo.",
    "mover_constante": "Para dejar sola la incógnita primero hay que deshacer lo que se le suma o se le resta: la "
                       "operación contraria quita ese número de ese lado (y se hace también en el otro).",
    "despejar": "La incógnita está multiplicada por un número; la operación contraria es dividir entre ese número, "
                "y se hace en los dos lados.",
    "intercambiar": "Leer una igualdad al revés no la cambia; con una desigualdad, el símbolo se da vuelta "
                    "(si 11 es menor que x, entonces x es mayor que 11).",
    "clasificar": "Si las incógnitas se cancelan, lo que queda es una comparación entre números: es verdadera o "
                  "falsa, y eso dice si hay infinitas soluciones o ninguna.",
    "comprobar": "Reemplazar la solución en el ejercicio original comprueba que no nos equivocamos.",
}


# ---------------------------------------------------------------------------
# Cada lado como  a·x + b
# ---------------------------------------------------------------------------

def _lin(n: Nodo, vars_: set) -> tuple[Fraction, Fraction]:
    """Devuelve (a, b) tales que el lado vale a·x + b. Registra la incógnita en `vars_`."""
    cero = Fraction(0)
    if isinstance(n, Num):
        return cero, n.valor
    if isinstance(n, Frac):
        return cero, Fraction(n.num, n.den)
    if isinstance(n, Porc):
        return cero, n.valor / 100
    if isinstance(n, Mixto):
        if n.den == 0:
            raise ErrorMatematico("No se puede dividir entre cero.")
        return cero, n.ent + Fraction(n.num, n.den)
    if isinstance(n, Var):
        vars_.add(n.nombre)
        return Fraction(1), cero
    if isinstance(n, Neg):
        a, b = _lin(n.hijo, vars_)
        return -a, -b
    if isinstance(n, Paren):
        return _lin(n.hijo, vars_)
    if isinstance(n, Raiz):
        a, b = _lin(n.hijo, vars_)
        if a != 0:
            raise ErrorMatematico(_NO_SOPORTADO)
        return cero, _calcular_raiz(n.indice, b)
    la, lb = _lin(n.izq, vars_)
    ra, rb = _lin(n.der, vars_)
    if n.op == "+":
        return la + ra, lb + rb
    if n.op == "-":
        return la - ra, lb - rb
    if n.op == "*":
        if la != 0 and ra != 0:
            raise ErrorMatematico(_NO_LINEAL)
        return la * rb + lb * ra, lb * rb
    if n.op == "/":
        if ra != 0:
            raise ErrorMatematico(_NO_SOPORTADO)
        if rb == 0:
            raise ErrorMatematico("No se puede dividir entre cero.")
        return la / rb, lb / rb
    if n.op == "^":
        if ra != 0:
            raise ErrorMatematico(_NO_SOPORTADO)
        if la == 0:
            return cero, _calcular("^", lb, rb)
        if rb == 1:
            return la, lb
        if rb == 0:
            return cero, Fraction(1)
        raise ErrorMatematico(_NO_LINEAL)
    raise ErrorMotor(f"Operador desconocido: {n.op}")  # pragma: no cover


def _incognitas(n: Nodo, encontradas: set) -> set:
    """Todas las letras que aparecen en el árbol."""
    if isinstance(n, Var):
        encontradas.add(n.nombre)
    for h in hijos(n):
        _incognitas(h, encontradas)
    return encontradas


# ---------------------------------------------------------------------------
# Propiedad distributiva (sobre el árbol, SIN simplificar)
# ---------------------------------------------------------------------------

def _terminos(n: Nodo) -> list:
    """Aplana una suma/resta en [(+1 | −1, término)]."""
    if isinstance(n, Paren):
        return _terminos(n.hijo)
    if isinstance(n, Neg):
        return [(-s, t) for s, t in _terminos(n.hijo)]
    if isinstance(n, BinOp) and n.op in "+-":
        izq, der = _terminos(n.izq), _terminos(n.der)
        if n.op == "-":
            der = [(-s, t) for s, t in der]
        return izq + der
    return [(1, n)]


def _suma(terminos: list) -> Nodo:
    nodo = None
    for signo, t in terminos:
        if nodo is None:
            nodo = t if signo == 1 else Neg(t)
        else:
            nodo = BinOp("+" if signo == 1 else "-", nodo, t)
    return nodo


def _distribuir(n: Nodo, general: bool = False) -> tuple[Nodo, bool]:
    """Multiplica un factor por cada término de un paréntesis que tiene letras.
    Con `general=False` (ecuaciones) el factor debe ser un número; con `general=True` (fórmulas)
    puede llevar letras. Devuelve (árbol nuevo, ¿se hizo algo?). No junta términos: es otro paso."""
    if isinstance(n, BinOp) and n.op == "*":
        for factor, par, factor_izq in ((n.izq, n.der, True), (n.der, n.izq, False)):
            if isinstance(par, Paren) and _incognitas(par, set()) and (general or not _incognitas(factor, set())):
                k = Paren(factor) if isinstance(factor, Num) and factor.valor < 0 else factor
                prods = [(s, BinOp("*", k, t) if factor_izq else BinOp("*", t, k)) for s, t in _terminos(par)]
                return _suma(prods), True
    if isinstance(n, Neg) and isinstance(n.hijo, Paren) and _incognitas(n.hijo, set()):
        return _suma([(-s, t) for s, t in _terminos(n.hijo)]), True
    hs = hijos(n)
    if not hs:
        return n, False
    nuevos, hizo = [], False
    for h in hs:
        nh, hh = _distribuir(h, general)
        nuevos.append(nh)
        hizo = hizo or hh
    return (con_hijos(n, nuevos), True) if hizo else (n, False)


# ---------------------------------------------------------------------------
# Dibujo de las ecuaciones
# ---------------------------------------------------------------------------

def _coef_texto(a: Fraction, v: str, dec: bool) -> str:
    if a == 1:
        return v
    if a == -1:
        return MENOS + v
    t = formatear(abs(a), dec)
    if se_ve_como_fraccion(abs(a), dec):
        t = f"({t})"
    return (MENOS if a < 0 else "") + t + v


def _lado_texto(a: Fraction, b: Fraction, v: str, dec: bool) -> str:
    partes = []
    if a != 0:
        partes.append(_coef_texto(a, v, dec))
    if b != 0 or a == 0:
        if not partes:
            partes.append(formatear(b, dec))
        else:
            partes.append(("+ " if b > 0 else f"{MENOS} ") + formatear(abs(b), dec))
    return " ".join(partes)


def _coef_latex(a: Fraction, v: str, dec: bool) -> str:
    if a == 1:
        return v
    if a == -1:
        return "-" + v
    return ("-" if a < 0 else "") + formatear_latex(abs(a), dec) + v


def _lado_latex(a: Fraction, b: Fraction, v: str, dec: bool) -> str:
    partes = []
    if a != 0:
        partes.append(_coef_latex(a, v, dec))
    if b != 0 or a == 0:
        if not partes:
            partes.append(formatear_latex(b, dec))
        else:
            partes.append(("+ " if b > 0 else "- ") + formatear_latex(abs(b), dec))
    return " ".join(partes)


def _ec(aL, bL, aR, bR, v, dec, rel):
    return (f"{_lado_texto(aL, bL, v, dec)} {rel} {_lado_texto(aR, bR, v, dec)}",
            f"{_lado_latex(aL, bL, v, dec)} {_REL_LATEX[rel]} {_lado_latex(aR, bR, v, dec)}")


def _previo_suma(aL, bL, aR, bR, v, dec, rel, signo, oper_txt, oper_tex):
    """'2x + 2 − 3x = 3x − 9 − 3x': la operación escrita en los dos lados."""
    s_t = "+" if signo == "+" else MENOS
    txt = (f"{_lado_texto(aL, bL, v, dec)} {s_t} {oper_txt} {rel} "
           f"{_lado_texto(aR, bR, v, dec)} {s_t} {oper_txt}")
    tex = (f"{_lado_latex(aL, bL, v, dec)} {signo} {oper_tex} {_REL_LATEX[rel]} "
           f"{_lado_latex(aR, bR, v, dec)} {signo} {oper_tex}")
    return txt, tex


def _envolver(s: str) -> str:
    return f"({s})" if (s.startswith(MENOS) or " " in s or "/" in s) else s


def _previo_division(izq_t, izq_l, der_t, der_l, a, dec, rel):
    a_t, a_l = formatear(a, dec), formatear_latex(a, dec)
    txt = f"{_envolver(izq_t)} ÷ {_envolver(a_t)} {rel} {_envolver(der_t)} ÷ {_envolver(a_t)}"
    tex = f"\\frac{{{izq_l}}}{{{a_l}}} {_REL_LATEX[rel]} \\frac{{{der_l}}}{{{a_l}}}"
    return txt, tex


def _sustituir(n: Nodo, valor: Fraction) -> Nodo:
    if isinstance(n, Var):
        return Num(valor)
    hs = hijos(n)
    return con_hijos(n, [_sustituir(h, valor) for h in hs]) if hs else n


def _evaluar(texto: str) -> Fraction:
    """Valor exacto de una expresión numérica, usando el motor de aritmética."""
    return Fraction(resolver(texto).resultado.replace(MENOS, "-"))


def _cumple(a: Fraction, rel: str, b: Fraction) -> bool:
    return {"<": a < b, ">": a > b, "≤": a <= b, "≥": a >= b, "=": a == b}[rel]


def _intervalo(rel: str, v: str) -> str:
    return {">": f"({v}, +∞)", "≥": f"[{v}, +∞)", "<": f"(−∞, {v})", "≤": f"(−∞, {v}]"}[rel]


def _conjunto(rel: str, v: str) -> str:
    return {">": f"todos los números mayores que {v} (el {v} no cuenta)",
            "≥": f"todos los números mayores o iguales que {v} (el {v} sí cuenta)",
            "<": f"todos los números menores que {v} (el {v} no cuenta)",
            "≤": f"todos los números menores o iguales que {v} (el {v} sí cuenta)"}[rel]


def _separar(texto: str) -> tuple[str, str, str]:
    """(relación, lado izquierdo, lado derecho). La relación es '=', '<', '>', '≤' o '≥'."""
    rels = _REL.findall(texto)
    if len(rels) > 1:
        raise ErrorDeEntrada("Solo puede haber un signo de comparación (<, >, ≤, ≥), no varios.")
    if rels:
        partes = _REL.split(texto)
        if "=" in "".join(partes):
            raise ErrorDeEntrada("Usa un solo tipo de signo: = o una desigualdad (<, >, ≤, ≥).")
        return rels[0].replace("<=", "≤").replace(">=", "≥"), partes[0], partes[1]
    if texto.count("=") != 1:
        raise ErrorDeEntrada("Una ecuación tiene un solo signo = (por ejemplo 2x + 3 = 11).")
    izq, der = texto.split("=")
    return "=", izq, der


# ---------------------------------------------------------------------------
# Resolver
# ---------------------------------------------------------------------------

def resolver_ecuacion(texto: str) -> Solucion:
    """Resuelve una ecuación o desigualdad lineal de una incógnita y explica cada paso."""
    if texto is None or not texto.strip():
        raise ErrorDeEntrada("Escribe una ecuación o desigualdad para resolver, por ejemplo 2x + 3 = 11.")
    rel, izq_t, der_t = _separar(texto)
    cosa = "ecuación" if rel == "=" else "desigualdad"
    if not izq_t.strip() or not der_t.strip():
        raise ErrorDeEntrada(f"Falta un lado de la {cosa}: escribe algo a cada lado del signo {rel}.")

    (arbol_i, dec_i), (arbol_d, dec_d) = parsear(izq_t, variables=True), parsear(der_t, variables=True)
    dec = dec_i or dec_d
    nI, nD = normalizar(arbol_i), normalizar(arbol_d)
    if not dec:                        # a/b con enteros es una fracción (igual que en aritmética)
        nI, nD = normalizar(_con_fracciones(nI)), normalizar(_con_fracciones(nD))

    letras = _incognitas(nD, _incognitas(nI, set()))      # primero las letras, luego si es lineal
    if not letras:
        raise ErrorDeEntrada(f"Una {cosa} necesita una incógnita (por ejemplo x), como 2x + 3 = 11.")
    if len(letras) > 1:
        lista = ", ".join(sorted(letras))
        raise ErrorDeEntrada(
            f"Hay varias letras ({lista}). Para despejar una de ellas escribe, por ejemplo: "
            f"despejar {sorted(letras)[0]} en {texto.strip()}")
    v = next(iter(letras))
    aL, bL = _lin(nI, set())
    aR, bR = _lin(nD, set())
    rel0 = rel

    pasos: list[Paso] = []

    def agregar(regla, explicacion, operacion="", ec=None, previo=None):
        txt, tex = ec if ec else _ec(aL, bL, aR, bR, v, dec, rel)
        pasos.append(Paso(
            numero=len(pasos) + 1, regla=regla, explicacion=explicacion, motivo=_MOTIVO[regla],
            operacion=operacion, resultado_parcial="", expresion=txt, latex=tex,
            intermedio=previo[0] if previo else "", latex_intermedio=previo[1] if previo else ""))

    def terminar(resultado, resultado_latex, decimal=None, exacto=True, nota=""):
        return Solucion(
            tipo="ecuacion_lineal" if rel0 == "=" else "desigualdad_lineal", entrada=texto,
            expresion_inicial=f"{a_texto(nI, dec)} {rel0} {a_texto(nD, dec)}",
            latex_inicial=f"{a_latex(nI, dec)} {_REL_LATEX[rel0]} {a_latex(nD, dec)}",
            pasos=pasos, resultado=resultado, resultado_latex=resultado_latex,
            resultado_decimal=decimal, decimal_exacto=exacto, nota=nota)

    def clasificar():
        bI, bD = formatear(bL, dec), formatear(bR, dec)
        verdadera = _cumple(bL, rel, bR)
        if rel == "=":
            si, no = (f"que siempre es verdadero, sea cual sea el valor de {v}. La ecuación tiene infinitas "
                      f"soluciones: sirve cualquier número.",
                      f"que es falso: ningún valor de {v} puede cumplirlo. La ecuación no tiene solución.")
        else:
            si, no = (f"que es verdadero sea cual sea el valor de {v}. Todos los números son solución.",
                      f"que es falso, sea cual sea el valor de {v}. La desigualdad no tiene solución.")
        agregar("clasificar", f"Las {v} desaparecen y queda {bI} {rel} {bD}, " + (si if verdadera else no))
        if verdadera:
            texto_r = "Infinitas soluciones" if rel == "=" else "Todos los números reales"
        else:
            texto_r = "Sin solución"
        return terminar(texto_r, f"\\text{{{texto_r}}}")

    # 1a. Propiedad distributiva (sin juntar términos todavía)
    dI, hI = _distribuir(nI)
    dD, hD = _distribuir(nD)
    tI, tD = a_texto(nI, dec), a_texto(nD, dec)
    if hI or hD:
        cambios = []
        if hI:
            cambios.append(f"En el lado izquierdo: {tI} = {a_texto(dI, dec)}.")
        if hD:
            cambios.append(f"En el lado derecho: {tD} = {a_texto(dD, dec)}.")
        ec = (f"{a_texto(dI, dec)} {rel} {a_texto(dD, dec)}",
              f"{a_latex(dI, dec)} {_REL_LATEX[rel]} {a_latex(dD, dec)}")
        agregar("distribuir",
                "Aplicamos la propiedad distributiva: multiplicamos el número de afuera por cada término que "
                "está dentro del paréntesis. " + " ".join(cambios),
                operacion=tI if hI else tD, ec=ec)
        tI, tD = a_texto(dI, dec), a_texto(dD, dec)

    # 1b. Hacer las operaciones y juntar términos parecidos
    cI, cD = _lado_texto(aL, bL, v, dec), _lado_texto(aR, bR, v, dec)
    cambios = []
    if tI != cI:
        cambios.append(f"En el lado izquierdo: {tI} = {cI}.")
    if tD != cD:
        cambios.append(f"En el lado derecho: {tD} = {cD}.")
    if cambios:
        que = "hacemos las operaciones que se pueden y juntamos los términos parecidos"
        if "÷" in tI + tD:
            que += ". Dividir entre un número es lo mismo que multiplicar por su inverso"
        agregar("simplificar", f"Simplificamos cada lado: {que}. " + " ".join(cambios),
                operacion=tI if tI != cI else tD)

    if aL == 0 and aR == 0:
        return clasificar()

    # 2. Juntar las incógnitas donde su coeficiente queda positivo
    if aL != 0 and aR != 0:
        lado = "izq" if aL >= aR else "der"
        if lado == "izq":
            mover, otro = aR, "izquierdo"
        else:
            mover, otro = aL, "derecho"
        coef_t, coef_l = _coef_texto(abs(mover), v, dec), _coef_latex(abs(mover), v, dec)
        signo = "-" if mover > 0 else "+"
        frase = f"{'restamos' if mover > 0 else 'sumamos'} {coef_t} en ambos lados"
        previo = _previo_suma(aL, bL, aR, bR, v, dec, rel, signo, coef_t, coef_l)
        if lado == "izq":
            aL, aR = aL - aR, Fraction(0)
            cola = f"A la derecha desaparecen las {v}."
        else:
            aR, aL = aR - aL, Fraction(0)
            cola = f"A la izquierda desaparecen las {v}."
        if aL == 0 and aR == 0:
            cola = f"En los dos lados desaparecen las {v}."
        agregar("mover_x",
                f"Para juntar las {v} en el lado {otro}, donde su coeficiente queda positivo, {frase}. {cola}",
                operacion=frase, previo=previo)
        if aL == 0 and aR == 0:
            return clasificar()
    else:
        lado = "izq" if aL != 0 else "der"

    # 3. Pasar el número suelto al otro lado
    b_x = bL if lado == "izq" else bR
    if b_x != 0:
        num_t, num_l = formatear(abs(b_x), dec), formatear_latex(abs(b_x), dec)
        signo = "-" if b_x > 0 else "+"
        frase = f"{'restamos' if b_x > 0 else 'sumamos'} {num_t} en ambos lados"
        previo = _previo_suma(aL, bL, aR, bR, v, dec, rel, signo, num_t, num_l)
        if lado == "izq":
            bR, bL = bR - bL, Fraction(0)
            donde, otro_lado, nuevo = "izquierda", "derecha", bR
        else:
            bL, bR = bL - bR, Fraction(0)
            donde, otro_lado, nuevo = "derecha", "izquierda", bL
        agregar("mover_constante",
                f"Para dejar la parte de la {v} sola a la {donde}, {frase}. A la {donde} se cancela el número "
                f"y a la {otro_lado} queda {formatear(nuevo, dec)}.", operacion=frase, previo=previo)

    # 4. Dividir entre el coeficiente
    a = aL if lado == "izq" else aR
    if a != 1:
        a_txt = formatear(a, dec)
        invierte = a < 0 and rel != "="
        nuevo_rel = _INVERSA[rel] if invierte else rel
        if a == -1:
            frase = f"dividimos ambos lados entre {a_txt} (es cambiar el signo)"
        else:
            frase = f"dividimos ambos lados entre {a_txt}"
        if invierte:
            frase += f" y, como {a_txt} es negativo, el sentido de la desigualdad se invierte ({rel} pasa a {nuevo_rel})"
        previo = _previo_division(_lado_texto(aL, bL, v, dec), _lado_latex(aL, bL, v, dec),
                                  _lado_texto(aR, bR, v, dec), _lado_latex(aR, bR, v, dec), a, dec, nuevo_rel)
        extra = ""
        if se_ve_como_fraccion(a, dec):
            extra = (f" Dividir entre una fracción es lo mismo que multiplicar por su inverso, "
                     f"{formatear(1 / a, dec)}.")
        if lado == "izq":
            valor, aL, bR = bR / a, Fraction(1), bR / a
        else:
            valor, aR, bL = bL / a, Fraction(1), bL / a
        rel = nuevo_rel
        donde = "izquierda" if lado == "izq" else "derecha"
        otro_lado = "derecha" if lado == "izq" else "izquierda"
        agregar("despejar",
                f"La {v} está multiplicada por {a_txt}, así que {frase}: a la {donde} queda la {v} sola y a la "
                f"{otro_lado} {formatear(valor, dec)}.{extra}", operacion=frase, previo=previo)

    # 5. Si la incógnita quedó a la derecha, se lee al revés
    valor = bR if lado == "izq" else bL
    if lado == "der":
        nuevo_rel = _INVERSA[rel]
        v_txt = formatear(valor, dec)
        frase = "leemos la igualdad al revés" if rel == "=" else "leemos la desigualdad al revés"
        extra = f" (el símbolo {rel} se da vuelta y pasa a {nuevo_rel})" if rel != "=" else ""
        anterior = rel
        aL, bL, aR, bR = Fraction(1), Fraction(0), Fraction(0), valor
        rel = nuevo_rel
        agregar("intercambiar",
                f"Tenemos {v_txt} {anterior} {v}, con la {v} a la derecha: {frase} para tenerla a la "
                f"izquierda{extra}. Queda {v} {rel} {v_txt}.", operacion=frase)

    # 6. Comprobación con el motor de aritmética (otro camino de cálculo)
    val_txt = formatear(valor, dec)

    def lado_sub(n, x):
        sub = a_texto(normalizar(_sustituir(n, x)), dec)
        return sub, _evaluar(sub)

    def mostrar(sub, res):                      # "11" en vez de "11 = 11"
        r = formatear(res, dec)
        return sub if sub == r else f"{sub} = {r}"

    sub_i, res_i = lado_sub(nI, valor)
    sub_d, res_d = lado_sub(nD, valor)
    if res_i != res_d:  # pragma: no cover - sería un error del motor, nunca del estudiante
        raise ErrorMotor(f"La comprobación falló: {sub_i} = {res_i} pero {sub_d} = {res_d}")

    decimal, exacto = (None, True)
    if se_ve_como_fraccion(valor, dec):
        decimal, exacto = decimal_aproximado(valor)

    if rel0 == "=":
        agregar("comprobar",
                f"Comprobamos reemplazando {v} por {val_txt} en la ecuación original. Izquierda: "
                f"{mostrar(sub_i, res_i)}. Derecha: {mostrar(sub_d, res_d)}. Los dos lados valen lo mismo "
                f"({formatear(res_i, dec)}), así que la solución es correcta.", operacion=val_txt)
        return terminar(f"{v} = {val_txt}", f"{v} = {formatear_latex(valor, dec)}", decimal, exacto)

    # Desigualdad: se prueba el valor frontera y un número de la solución
    prueba = valor + 1 if rel in (">", "≥") else valor - 1
    p_txt = formatear(prueba, dec)
    sub_pi, res_pi = lado_sub(nI, prueba)
    sub_pd, res_pd = lado_sub(nD, prueba)
    if not _cumple(res_pi, rel0, res_pd):  # pragma: no cover
        raise ErrorMotor(f"La comprobación falló: {res_pi} {rel0} {res_pd} no se cumple")
    fuera = valor - 1 if rel in (">", "≥") else valor + 1
    if _cumple(lado_sub(nI, fuera)[1], rel0, lado_sub(nD, fuera)[1]):  # pragma: no cover
        raise ErrorMotor("La comprobación falló: un número fuera de la solución también cumple")
    estricta = rel in ("<", ">")
    en_frontera = (f"con {v} = {val_txt} los dos lados valen {formatear(res_i, dec)}, "
                   + (f"son iguales, y como la desigualdad es estricta el {val_txt} NO es solución"
                      if estricta else f"son iguales, y como la desigualdad incluye el igual, el {val_txt} SÍ es solución"))
    agregar("comprobar",
            f"Comprobamos: {en_frontera}. Ahora probamos con un número de la solución, {v} = {p_txt}: izquierda "
            f"{mostrar(sub_pi, res_pi)}; derecha {mostrar(sub_pd, res_pd)}; y {formatear(res_pi, dec)} {rel0} "
            f"{formatear(res_pd, dec)} es verdadero, así que la solución es correcta.", operacion=f"{v} = {p_txt}")
    nota = f"En intervalo: {_intervalo(rel, val_txt)}. Son solución {_conjunto(rel, val_txt)}."
    return terminar(f"{v} {rel} {val_txt}", f"{v} {_REL_LATEX[rel]} {formatear_latex(valor, dec)}",
                    decimal, exacto, nota)
