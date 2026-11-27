"""Solucionador de aritmética paso a paso.

Orden de resolución (jerarquía de operaciones):
    0. Paréntesis (el más a la izquierda; dentro de él se repite todo el orden)
    0.5 Convertir lo escrito en "forma especial" antes de operar con ello:
        fracciones simplificables (6/3), porcentajes (20%) y números mixtos (3 1/2)
    1. Potencias y raíces  (de derecha a izquierda: 2^3^2 = 2^(3^2))
    2. Multiplicar / dividir  (de izquierda a derecha)
    3. Sumar / restar         (de izquierda a derecha)

Cada vuelta del ciclo en `resolver` hace UN paso y produce un `Paso`.
Los cálculos usan `Fraction`: son exactos, sin errores de decimales.
"""

from dataclasses import dataclass
from fractions import Fraction
import re
from math import gcd, lcm

from .arbol import (BinOp, Frac, Mixto, Neg, Nodo, Num, Paren, Porc, Raiz, con_hijos, hijos,
                    normalizar, postorden, preorden, reemplazar)
from .errores import ErrorMatematico, ErrorMotor
from .numeros import MENOS, decimal_aproximado, formatear, formatear_latex, se_ve_como_fraccion
from .parser import parsear
from .pasos import Paso, Solucion
from .render import a_latex, a_texto, operacion_texto

_MAX_PASOS = 500
_MAX_BITS = 14000        # ~4200 cifras: más que eso no se puede mostrar
_MAX_EXPONENTE = 1000

_NOMBRE_REGLA = {"+": "suma", "-": "resta", "*": "multiplicacion", "/": "division", "^": "potencia"}

_MOTIVO = {
    "simplificacion": "Las fracciones se simplifican antes de operar con ellas: con números más pequeños es más fácil calcular.",
    "porcentaje": "Un porcentaje se convierte en número antes de operar con él.",
    "mixto": "Un número mixto se convierte en fracción antes de operar con él: así todas las operaciones se hacen con fracciones.",
    "raiz": "Las raíces se resuelven junto con las potencias, antes que las multiplicaciones, divisiones, sumas y restas.",
    "potencia": "Las potencias se resuelven antes que las multiplicaciones, divisiones, sumas y restas.",
    "multiplicacion": "Las multiplicaciones y divisiones van antes que las sumas y restas, y se resuelven de izquierda a derecha.",
    "division": "Las multiplicaciones y divisiones van antes que las sumas y restas, y se resuelven de izquierda a derecha.",
    "suma": "Ya solo quedan sumas y restas: se resuelven de izquierda a derecha.",
    "resta": "Ya solo quedan sumas y restas: se resuelven de izquierda a derecha.",
}


@dataclass
class _Info:
    regla: str
    op: str
    a: Fraction
    b: Fraction
    r: Fraction
    en_parentesis: bool = False
    signo_menos: bool = False   # había un '−' delante que se aplica al resultado
    texto_op: str = ""          # trozo resuelto, ya escrito (si vacío se arma con op, a y b)


# ---------------------------------------------------------------------------
# Fracciones escritas: a/b con enteros es una FRACCIÓN, no una división
# ---------------------------------------------------------------------------

def _con_fracciones(n: Nodo) -> Nodo:
    """Convierte cada `a/b` (barra entre dos enteros escritos) en fracción.

    - Si ya está en su mínima expresión (1/2, 7/2) pasa a ser un número normal.
    - Si se puede simplificar (6/3, 4/6, 0/5) queda como `Frac`, y más adelante
      el solucionador dedica un paso a simplificarla (así no se "pierde" nada
      de lo que escribió el estudiante).
    - `÷` y `:` NO se tocan: esos son siempre una división.
    Solo mira números escritos tal cual, así que 2^6/3 sigue siendo (2^6)/3.
    """
    hs = hijos(n)
    n2 = con_hijos(n, [_con_fracciones(h) for h in hs]) if hs else n
    if (isinstance(n2, BinOp) and n2.op == "/" and n2.barra
            and isinstance(n2.izq, Num) and isinstance(n2.der, Num)
            and n2.izq.valor.denominator == 1 and n2.der.valor.denominator == 1):
        num, den = n2.izq.valor.numerator, n2.der.valor.numerator
        if den == 0:
            raise ErrorMatematico("No se puede dividir entre cero.")
        if den < 0:
            return n2            # 6/-3: se queda como división
        if den != 1 and gcd(abs(num), den) == 1:
            return Num(Fraction(num, den))
        return Frac(num, den)
    return n2


# ---------------------------------------------------------------------------
# Cálculo exacto
# ---------------------------------------------------------------------------

def _demasiado_grande() -> ErrorMatematico:
    return ErrorMatematico("El resultado es un número demasiado grande para mostrarlo.")


def _bits(f: Fraction) -> int:
    return max(f.numerator.bit_length(), f.denominator.bit_length())


_NOMBRE_RAIZ = {2: "cuadrada", 3: "cúbica", 4: "cuarta"}


def _raiz_entera(n: int, k: int):
    """Raíz k-ésima exacta del entero n >= 0, o None si no es exacta (búsqueda binaria)."""
    if n < 2:
        return n
    lo, hi = 1, 1 << (n.bit_length() // k + 1)
    while lo < hi:
        mid = (lo + hi) // 2
        if mid ** k < n:
            lo = mid + 1
        else:
            hi = mid
    return lo if lo ** k == n else None


def _calcular_raiz(k: int, a: Fraction) -> Fraction:
    nombre = _NOMBRE_RAIZ[k]
    if a < 0:
        if k % 2 == 0:
            raise ErrorMatematico(
                f"No existe la raíz {nombre} de un número negativo en los números reales."
            )
        return -_calcular_raiz(k, -a)
    num, den = _raiz_entera(a.numerator, k), _raiz_entera(a.denominator, k)
    if num is None or den is None:
        raise ErrorMatematico(
            f"La raíz {nombre} de {formatear(a, False)} no es exacta: no da un número entero ni una fracción. "
            "Se puede dejar como radical (por ejemplo √12 = 2√3)."
        )
    return Fraction(num, den)


def _calcular(op: str, a: Fraction, b: Fraction) -> Fraction:
    if op == "+":
        r = a + b
    elif op == "-":
        r = a - b
    elif op == "*":
        r = a * b
    elif op == "/":
        if b == 0:
            raise ErrorMatematico("No se puede dividir entre cero.")
        r = a / b
    elif op == "^":
        if b.denominator != 1:                       # a^(p/q) = (raíz q-ésima de a)^p
            q, p_ = b.denominator, b.numerator
            if q not in _NOMBRE_RAIZ:
                raise ErrorMatematico("Por ahora solo calculo exponentes fraccionarios con denominador 2, 3 o 4 "
                                      "(son raíces cuadradas, cúbicas o cuartas).")
            r0 = _calcular_raiz(q, a)
            if r0 == 0 and p_ < 0:
                raise ErrorMatematico("0 elevado a un exponente negativo no está definido (sería dividir entre cero).")
            if abs(p_) > _MAX_EXPONENTE or _bits(r0) * abs(p_) > _MAX_BITS:
                raise _demasiado_grande()
            r = r0 ** p_
            if _bits(r) > _MAX_BITS:
                raise _demasiado_grande()
            return r
        n = b.numerator
        if a == 0 and n == 0:
            raise ErrorMatematico("0^0 es una forma indeterminada: no tiene un valor definido.")
        if a == 0 and n < 0:
            raise ErrorMatematico("No se puede elevar 0 a un exponente negativo (equivale a dividir entre cero).")
        if abs(n) > _MAX_EXPONENTE or _bits(a) * abs(n) > _MAX_BITS:
            raise _demasiado_grande()
        r = a ** n
    else:  # pragma: no cover
        raise ErrorMotor(f"Operador desconocido: {op}")
    if _bits(r) > _MAX_BITS:
        raise _demasiado_grande()
    return r


# ---------------------------------------------------------------------------
# Explicaciones en español
# ---------------------------------------------------------------------------

def _frac(n: int, d: int) -> str:
    return f"{MENOS if n < 0 else ''}{abs(n)}/{d}"


def _ent(v: int) -> str:
    """Entero con el signo menos tipográfico: −1, 5."""
    return f"{MENOS}{abs(v)}" if v < 0 else str(v)


def _frac_par(n: int, d: int) -> str:
    return f"({_frac(n, d)})" if n < 0 else _frac(n, d)


def _nota_signos(a: Fraction, b: Fraction) -> str:
    if a == 0 or b == 0:
        return ""
    if (a < 0) != (b < 0):
        return " Signos distintos: el resultado es negativo."
    if a < 0 and b < 0:
        return " Dos números negativos dan un resultado positivo."
    return ""


def _explicar_simplificacion(i: _Info) -> str:
    num, den = i.a.numerator, i.b.numerator
    fr = f"{MENOS if num < 0 else ''}{abs(num)}/{den}"
    R = formatear(i.r, False)
    if den == 1:
        return f"Una fracción con denominador 1 es el propio número: {fr} = {R}."
    if num == 0:
        return f"Cero dividido entre cualquier número distinto de cero es cero: {fr} = {R}."
    g = gcd(abs(num), den)
    return (f"Simplificamos la fracción {fr}: el máximo común divisor de {abs(num)} y {den} es {g}, "
            f"así que dividimos numerador y denominador entre {g} y queda {R}.")


def _explicar_porcentaje(i: _Info, dec: bool) -> str:
    p = formatear(i.a, dec)
    return (f"El porcentaje {p}% significa {p} de cada 100: {p}% = {p}/100 = "
            f"{formatear(i.r, dec)}.")


def _explicar_mixto(i: _Info) -> str:
    ent, num, den = int(i.a), i.b.numerator, i.b.denominator
    total = ent * den + num
    texto = (f"Convertimos el número mixto {ent} {num}/{den} en fracción: multiplicamos el entero por el "
             f"denominador y sumamos el numerador ({ent} × {den} + {num} = {total}), y el resultado va "
             f"sobre el mismo denominador: {total}/{den}")
    if formatear(i.r, False) != f"{total}/{den}":
        texto += f" = {formatear(i.r, False)}"
    return texto + "."


def _explicar_raiz(i: _Info, dec: bool) -> str:
    k = int(i.b)
    base = formatear(i.r, dec)
    if i.r < 0 or se_ve_como_fraccion(i.r, dec):
        base = f"({base})"
    producto = " × ".join([base] * k)
    radicando = formatear(i.a, dec)
    return (f"{i.texto_op} = {formatear(i.r, dec)}: la raíz {_NOMBRE_RAIZ[k]} de {radicando} es "
            f"{formatear(i.r, dec)}, porque {producto} = {radicando}.")


def _explicar(i: _Info, dec: bool) -> str:
    if i.regla == "simplificacion":
        return _explicar_simplificacion(i)
    if i.regla == "porcentaje":
        return _explicar_porcentaje(i, dec)
    if i.regla == "mixto":
        return _explicar_mixto(i)
    if i.regla == "raiz":
        return _explicar_raiz(i, dec)
    a, b, r, op = i.a, i.b, i.r, i.op
    oper = operacion_texto(op, a, b, dec)
    R = formatear(r, dec)
    fracciones = se_ve_como_fraccion(a, dec) or se_ve_como_fraccion(b, dec)

    if op in "+-":
        if fracciones:
            da, db = a.denominator, b.denominator
            m = lcm(da, db)
            na, nb = a.numerator * (m // da), b.numerator * (m // db)
            signo = "+" if op == "+" else MENOS
            total = na + nb if op == "+" else na - nb
            if da == db:
                nb_txt = f"({_ent(nb)})" if nb < 0 else str(nb)
                verbo = "sumamos" if op == "+" else "restamos"
                texto = (f"Las fracciones tienen el mismo denominador, así que {verbo} solo los numeradores "
                         f"({_ent(na)} {signo} {nb_txt} = {_ent(total)}) y el denominador se queda igual: {_frac(total, m)}")
            else:
                intro = f"Para {'sumar' if op == '+' else 'restar'} fracciones buscamos un denominador común (mcm de {da} y {db} = {m})"
                texto = f"{intro}: {oper} → {_frac(na, m)} {signo} {_frac_par(nb, m)} = {_frac(total, m)}"
            if R != _frac(total, m):
                texto += f" = {R}"
            return texto + "."
        if op == "+":
            if b < 0:
                return f"Sumar un número negativo equivale a restar su valor sin signo: {oper} = {R}."
            return f"Sumamos {oper} = {R}."
        if b < 0:
            return f"Restar un número negativo equivale a sumar su valor sin signo: {oper} = {R}."
        return f"Restamos {oper} = {R}."

    if op == "*":
        if fracciones:
            num, den = a.numerator * b.numerator, a.denominator * b.denominator
            texto = f"Multiplicamos numeradores entre sí y denominadores entre sí: {oper} → {_frac(num, den)}"
            if R != _frac(num, den):
                texto += f" = {R}"
            return texto + "." + _nota_signos(a, b)
        return f"Multiplicamos {oper} = {R}." + _nota_signos(a, b)

    if op == "/":
        if fracciones:
            inverso = Fraction(b.denominator, b.numerator)
            como_producto = operacion_texto("*", a, inverso, dec)
            return (f"Dividir entre una fracción es multiplicar por su inverso: "
                    f"{oper} = {como_producto} = {R}." + _nota_signos(a, b))
        if se_ve_como_fraccion(r, dec):
            aprox, _ = decimal_aproximado(r)
            return (f"La división {oper} no da un número entero, así que queda como la fracción "
                    f"{R} (≈ {aprox}).") + _nota_signos(a, b)
        return f"Dividimos {oper} = {R}." + _nota_signos(a, b)

    # potencia
    if b.denominator != 1:
        q, p_ = b.denominator, b.numerator
        r0 = _calcular_raiz(q, a)
        A = formatear(a, dec)
        if p_ == 1:
            return (f"Un exponente fraccionario es una raíz: el denominador {q} es el índice. {oper} es la raíz "
                    f"{_NOMBRE_RAIZ[q]} de {A}, que vale {R}.")
        return (f"Un exponente fraccionario es una raíz: el denominador {q} es el índice y el numerador {p_} es la "
                f"potencia. Primero la raíz {_NOMBRE_RAIZ[q]} de {A}, que es {formatear(r0, dec)}, y luego se eleva "
                f"a la {p_}: {R}.")
    n = b.numerator
    if n == 0:
        return f"Todo número distinto de cero elevado a 0 vale 1: {oper} = {R}."
    if n < 0:
        positiva = operacion_texto("^", a, Fraction(-n), dec)
        return (f"Un exponente negativo invierte la base: {oper} = 1 ÷ {positiva} = {R}.")
    texto = ""
    if a.denominator == 1 and n <= 5:
        base = formatear(a, dec)
        base = f"({base})" if a < 0 else base
        producto = " × ".join([base] * n)
        texto = f"Elevar a la {n} es multiplicar la base {n} veces por sí misma: {oper} = {producto} = {R}."
    else:
        texto = f"Calculamos la potencia {oper} = {R}."
    if a < 0:
        par = n % 2 == 0
        texto += (f" Con base negativa, un exponente {'par' if par else 'impar'} "
                  f"da un resultado {'positivo' if par else 'negativo'}.")
    return texto


# ---------------------------------------------------------------------------
# Un paso a la vez
# ---------------------------------------------------------------------------

def _antes(raiz_arbol: Nodo, a: Nodo, b: Nodo) -> bool:
    """¿El nodo `a` aparece antes que `b` en el recorrido de hijos a padre, de izquierda a derecha?"""
    for n in postorden(raiz_arbol):
        if n is a:
            return True
        if n is b:
            return False
    return False


def _primero(iterable, condicion):
    for x in iterable:
        if condicion(x):
            return x
    return None


def _siguiente_paso(nodo: Nodo, dec: bool) -> tuple[Nodo, _Info]:
    """Hace UN paso sobre `nodo` y devuelve (árbol nuevo, información del paso)."""
    # Etapa 0: paréntesis que aún contienen operaciones (el más a la izquierda)
    p = _primero(preorden(nodo), lambda n: isinstance(n, Paren) and not isinstance(n.hijo, Num))
    if p is not None:
        nuevo_hijo, info = _siguiente_paso(p.hijo, dec)
        info.en_parentesis = True
        papa = _primero(preorden(nodo), lambda n: isinstance(n, Neg) and n.hijo is p)
        if papa is not None and isinstance(normalizar(Paren(nuevo_hijo)), Num):
            info.signo_menos = True
        return reemplazar(nodo, p, Paren(nuevo_hijo)), info

    # Etapa 0.5: convertir lo escrito en forma especial (el más a la izquierda)
    f = _primero(preorden(nodo), lambda n: isinstance(n, (Frac, Porc, Mixto)))
    if f is not None:
        if isinstance(f, Frac):
            r = Fraction(f.num, f.den)
            info = _Info("simplificacion", "simplificar", Fraction(f.num), Fraction(f.den), r)
        elif isinstance(f, Porc):
            r = f.valor / 100
            info = _Info("porcentaje", "porcentaje", f.valor, Fraction(100), r)
        else:
            if f.den == 0:
                raise ErrorMatematico("No se puede dividir entre cero.")
            r = f.ent + Fraction(f.num, f.den)
            info = _Info("mixto", "mixto", Fraction(f.ent), Fraction(f.num, f.den), r)
        info.texto_op = a_texto(f, dec)
        return reemplazar(nodo, f, Num(r)), info

    # Etapa 1: raíces y potencias (la primera, de izquierda a derecha en el árbol)
    ra = _primero(postorden(nodo), lambda n: isinstance(n, Raiz) and isinstance(n.hijo, Num))
    po = _primero(postorden(nodo), lambda n: (isinstance(n, BinOp) and n.op == "^"
                                              and isinstance(n.izq, Num) and isinstance(n.der, Num)))
    if ra is not None and (po is None or _antes(nodo, ra, po)):
        a = ra.hijo.valor
        r = _calcular_raiz(ra.indice, a)
        info = _Info("raiz", "raiz", a, Fraction(ra.indice), r)
        info.texto_op = a_texto(ra, dec)
        if _primero(preorden(nodo), lambda n: isinstance(n, Neg) and n.hijo is ra):
            info.signo_menos = True
        return reemplazar(nodo, ra, Num(r)), info

    # Etapas 1 (potencias), 2 y 3 según la jerarquía
    for ops in (("^",), ("*", "/"), ("+", "-")):
        objetivo = _primero(
            postorden(nodo),
            lambda n, ops=ops: (isinstance(n, BinOp) and n.op in ops
                                and isinstance(n.izq, Num) and isinstance(n.der, Num)),
        )
        if objetivo is not None:
            a, b = objetivo.izq.valor, objetivo.der.valor
            r = _calcular(objetivo.op, a, b)
            info = _Info(_NOMBRE_REGLA[objetivo.op], objetivo.op, a, b, r)
            if _primero(preorden(nodo), lambda n: isinstance(n, Neg) and n.hijo is objetivo):
                info.signo_menos = True
            return reemplazar(nodo, objetivo, Num(r)), info

    raise ErrorMotor("Estado inesperado: la expresión no se puede reducir más.")  # pragma: no cover


def resolver(texto: str) -> Solucion:
    """Resuelve una expresión aritmética y devuelve todos los pasos."""
    arbol, dec = parsear(texto)
    usa_de = re.search(r"(?<![^\W\d_])de(?![^\W\d_])", texto, re.IGNORECASE) is not None
    actual = normalizar(arbol)
    if not dec:                    # con decimales, "/" se queda como división
        actual = normalizar(_con_fracciones(actual))

    sol_pasos: list[Paso] = []
    inicial = a_texto(actual, dec)
    inicial_latex = a_latex(actual, dec)

    while not isinstance(actual, Num):
        if len(sol_pasos) >= _MAX_PASOS:
            raise ErrorMatematico("La expresión necesita demasiados pasos.")
        nuevo, info = _siguiente_paso(actual, dec)
        actual = normalizar(nuevo)

        explicacion = _explicar(info, dec)
        if info.signo_menos:
            explicacion += " Como había un signo menos delante, se cambia el signo del resultado."
        motivo = _MOTIVO[info.regla]
        if info.regla == "porcentaje" and usa_de:
            motivo += " En un porcentaje, «de» significa multiplicar."
        if info.en_parentesis:
            explicacion = "Dentro del paréntesis: " + explicacion[0].lower() + explicacion[1:]
            motivo = "Los paréntesis se resuelven primero, y dentro de ellos se sigue la misma jerarquía. " + motivo

        sol_pasos.append(Paso(
            numero=len(sol_pasos) + 1,
            regla=info.regla,
            explicacion=explicacion,
            motivo=motivo,
            operacion=info.texto_op or operacion_texto(info.op, info.a, info.b, dec),
            resultado_parcial=formatear(info.r, dec),
            expresion=a_texto(actual, dec),
            latex=a_latex(actual, dec),
            en_parentesis=info.en_parentesis,
        ))

    r = actual.valor
    dec_txt, dec_exacto = (None, True)
    if se_ve_como_fraccion(r, dec):
        dec_txt, dec_exacto = decimal_aproximado(r)

    return Solucion(
        tipo="aritmetica",
        entrada=texto,
        expresion_inicial=inicial,
        latex_inicial=inicial_latex,
        pasos=sol_pasos,
        resultado=formatear(r, dec),
        resultado_latex=formatear_latex(r, dec),
        resultado_decimal=dec_txt,
        decimal_exacto=dec_exacto,
    )
