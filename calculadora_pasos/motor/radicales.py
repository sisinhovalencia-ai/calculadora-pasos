"""Radicales con números, como en el Álgebra de Baldor.

    √12                 →  12 = 2²·3, así que √12 = 2√3
    √50 + √8            →  5√2 + 2√2 = 7√2
    √2 · √8             →  √(2·8) = √16 = 4
    1/√2                →  racionalizamos: (1·√2)/(√2·√2) = √2/2
    3/(2 + √5)          →  con el conjugado: 3(2 − √5)/((2 + √5)(2 − √5)) = −6 + 3√5
    8^(1/3), 2^(1/2)    →  un exponente fraccionario es una raíz

Es lo que la aritmética exacta rechaza con «la raíz no es exacta»: aquí se simplifica en vez de
dar un error. Raíces de índice 2, 3 y 4.

El método es una lista de transformaciones que se aplican de a una (cada una es un paso explicado):
raíz interna → raíz de una fracción → sacar lo que se puede de la raíz → multiplicar raíces → potencia de
una raíz → distribuir → racionalizar → simplificar fracciones → juntar términos semejantes.
Al final se comprueba con decimales que lo mostrado vale lo mismo que lo escrito (sin usar SymPy).
"""

import math
import re
from fractions import Fraction

from .algebra import Libreta, solucion
from .arbol import normalizar
from .aritmetica import _con_fracciones
from .errores import ErrorDeEntrada, ErrorMatematico, ErrorMotor
from .expr import E, EFrac, ENeg, ENum, EPot, EProd, ERad, ESim, ESum, a_sympy, desde_arbol, neg, num, txt
from .parser import parsear
from .pasos import Solucion
from .polinomios import _distribuida, _hay_producto

_MOTIVO = {
    "raiz_interna": "Lo que está dentro de la raíz se calcula primero.",
    "raiz_fraccion": "La raíz de una fracción es la raíz del numerador entre la raíz del denominador.",
    "simplificar_raiz": "Se descompone el número en factores primos; lo que forma un grupo del tamaño del índice sale de la "
                        "raíz, y lo demás se queda adentro.",
    "multiplicar_raices": "Las raíces del mismo índice se multiplican multiplicando los números que están dentro.",
    "potencia_raiz": "La potencia y la raíz se cancelan cuando el exponente es igual al índice: (√a)² = a.",
    "distribuir": "Cada término de un paréntesis se multiplica por lo de afuera; ninguno se queda sin multiplicar.",
    "racionalizar": "No se deja una raíz en el denominador: se multiplica arriba y abajo por algo que la elimine, y así la "
                    "fracción no cambia de valor.",
    "fraccion_numerica": "Una fracción de números se simplifica dividiendo numerador y denominador entre su divisor común.",
    "combinar": "Solo se pueden sumar los radicales semejantes (mismo índice y mismo número dentro de la raíz): se suman "
                "sus coeficientes. Los demás se dejan indicados.",
    "quitar_parentesis": "Con un signo − delante de un paréntesis, todos los términos de adentro cambian de signo.",
    "exponente_fraccionario": "Un exponente fraccionario es una raíz: el denominador es el índice y el numerador es la "
                              "potencia: a^(p/q) es la raíz q-ésima de a^p.",
    "ya_simplificada": "Si ya no hay nada que simplificar, la expresión está lista.",
}

_NOMBRE_RAIZ = {2: "cuadrada", 3: "cúbica", 4: "cuarta"}
_SUP = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")


def _sp():
    import sympy
    return sympy


# ---------------------------------------------------------------------------
# Limpieza (no cambia el valor): juntar coeficientes numéricos de los productos
# ---------------------------------------------------------------------------

def _limpiar(e: E) -> E:
    if isinstance(e, ESum):
        return ESum(tuple(_limpiar(t) for t in e.terminos))
    if isinstance(e, ENeg):
        x = _limpiar(e.x)
        if isinstance(x, ENeg):
            return x.x
        if isinstance(x, ENum) and x.v == 0:
            return x
        return ENeg(x)
    if isinstance(e, EFrac):
        return EFrac(_limpiar(e.num), _limpiar(e.den))
    if isinstance(e, EPot):
        return EPot(_limpiar(e.base), e.exp)
    if isinstance(e, ERad):
        return ERad(e.indice, _limpiar(e.rad))
    if isinstance(e, EProd):
        coef, signo, resto = Fraction(1), 1, []
        pendientes = [_limpiar(f) for f in e.factores]
        while pendientes:
            f = pendientes.pop(0)
            if isinstance(f, ENeg):
                signo, f = -signo, f.x
                pendientes.insert(0, f)
            elif isinstance(f, EProd):
                pendientes = list(f.factores) + pendientes
            elif isinstance(f, ENum) and f.v.denominator == 1:
                coef *= f.v
            else:
                resto.append(f)
        if coef == 0:
            return ENum(Fraction(0))
        piezas = ([ENum(coef)] if coef != 1 or not resto else []) + resto
        r = piezas[0] if len(piezas) == 1 else EProd(tuple(piezas))
        return ENeg(r) if signo < 0 else r
    return e


# ---------------------------------------------------------------------------
# Ayudas
# ---------------------------------------------------------------------------

def _factorizacion_texto(n: int) -> str:
    sp = _sp()
    f = sp.factorint(n)
    return "·".join(str(p) if e == 1 else f"{p}{str(e).translate(_SUP)}" for p, e in sorted(f.items()))


def _extraer(n: int, k: int) -> tuple[int, int]:
    """n = a^k · b, con b sin ningún factor que sea una potencia k-ésima: devuelve (a, b)."""
    sp = _sp()
    a = b = 1
    for p, e in sp.factorint(n).items():
        a *= p ** (e // k)
        b *= p ** (e % k)
    return a, b


def _numerico(e: E) -> bool:
    """¿Es una expresión solo con números (sin letras ni raíces)?"""
    if isinstance(e, (ESim, ERad)):
        return False
    return all(_numerico(h) for h in _hijos(e))


def _hijos(e: E):
    if isinstance(e, ESum):
        return e.terminos
    if isinstance(e, EProd):
        return e.factores
    if isinstance(e, EPot):
        return (e.base,)
    if isinstance(e, ENeg):
        return (e.x,)
    if isinstance(e, EFrac):
        return (e.num, e.den)
    if isinstance(e, ERad):
        return (e.rad,)
    return ()


def _con_hijos(e: E, nuevos: list) -> E:
    if isinstance(e, ESum):
        return ESum(tuple(nuevos))
    if isinstance(e, EProd):
        return EProd(tuple(nuevos))
    if isinstance(e, EPot):
        return EPot(nuevos[0], e.exp)
    if isinstance(e, ENeg):
        return ENeg(nuevos[0])
    if isinstance(e, EFrac):
        return EFrac(nuevos[0], nuevos[1])
    if isinstance(e, ERad):
        return ERad(e.indice, nuevos[0])
    return e


def _valor(e: E):
    return a_sympy(e, {})


def _tiene_radical(e: E) -> bool:
    return isinstance(e, ERad) or any(_tiene_radical(h) for h in _hijos(e))


def _coef_y_radical(t: E):
    """c·√n como (c, indice, n) con c fracción; (c, None, None) si es un número; None si no tiene esa forma."""
    signo, x = (-1, t.x) if isinstance(t, ENeg) else (1, t)
    if isinstance(x, ENum):
        return signo * x.v, None, None
    if isinstance(x, ERad) and isinstance(x.rad, ENum) and x.rad.v.denominator == 1:
        return Fraction(signo), x.indice, int(x.rad.v)
    if isinstance(x, EProd) and len(x.factores) == 2 and isinstance(x.factores[0], ENum) \
            and isinstance(x.factores[1], ERad) and isinstance(x.factores[1].rad, ENum) \
            and x.factores[1].rad.v.denominator == 1:
        r = x.factores[1]
        return signo * x.factores[0].v, r.indice, int(r.rad.v)
    return None


# ---------------------------------------------------------------------------
# Las transformaciones: cada una mira UN nodo y devuelve (reemplazo, explicación, operación) o None
# ---------------------------------------------------------------------------

def _t_raiz_interna(n: E):
    if isinstance(n, ERad) and not isinstance(n.rad, ENum) and _numerico(n.rad):
        v = _valor(n.rad)
        if v < 0 and n.indice % 2 == 0:
            raise ErrorMatematico("No existe la raíz de un número negativo en los números reales.")
        nuevo = ERad(n.indice, num(Fraction(int(v.p), int(v.q))))
        return nuevo, f"Primero hacemos la operación que está dentro de la raíz: {txt(n.rad)} = {txt(nuevo.rad)}.", txt(n.rad)
    return None


def _t_raiz_fraccion(n: E):
    if isinstance(n, ERad) and isinstance(n.rad, ENum) and n.rad.v.denominator != 1:
        p, q = n.rad.v.numerator, n.rad.v.denominator
        nuevo = EFrac(ERad(n.indice, ENum(Fraction(p))), ERad(n.indice, ENum(Fraction(q))))
        return nuevo, (f"La raíz de una fracción es la raíz del numerador entre la raíz del denominador: "
                       f"{txt(n)} = {txt(nuevo)}."), txt(n)
    return None


def _t_simplificar_raiz(n: E):
    if not (isinstance(n, ERad) and isinstance(n.rad, ENum) and n.rad.v.denominator == 1):
        return None
    k, N = n.indice, int(n.rad.v)
    if N == 0:
        return ENum(Fraction(0)), f"{txt(n)} = 0.", txt(n)
    if N == 1:
        return ENum(Fraction(1)), f"{txt(n)} = 1.", txt(n)
    a, b = _extraer(N, k)
    if a == 1:
        return None
    fact = _factorizacion_texto(N)
    if b == 1:
        return ENum(Fraction(a)), (f"{txt(n)} = {a}, porque {a}{str(k).translate(_SUP)} = {N} "
                                   f"({N} = {fact})."), txt(n)
    nuevo = EProd((ENum(Fraction(a)), ERad(k, ENum(Fraction(b)))))
    return nuevo, (f"Descomponemos {N} en factores primos: {N} = {fact}. Lo que forma un grupo de {k} sale de la raíz "
                   f"{_NOMBRE_RAIZ[k]}: {txt(n)} = {txt(nuevo)}."), txt(n)


def _t_multiplicar_radicales(n: E):
    if not isinstance(n, EProd):
        return None
    idx = [i for i, f in enumerate(n.factores)
           if isinstance(f, ERad) and isinstance(f.rad, ENum) and f.rad.v.denominator == 1]
    for a in range(len(idx)):
        for b in range(a + 1, len(idx)):
            fa, fb = n.factores[idx[a]], n.factores[idx[b]]
            if fa.indice != fb.indice:
                continue
            prod_ = int(fa.rad.v) * int(fb.rad.v)
            nuevo_r = ERad(fa.indice, ENum(Fraction(prod_)))
            resto = [f for i, f in enumerate(n.factores) if i not in (idx[a], idx[b])]
            nuevo = EProd(tuple(resto + [nuevo_r])) if resto else nuevo_r
            return nuevo, (f"Multiplicamos las raíces del mismo índice multiplicando los números de adentro: "
                           f"{txt(fa)}·{txt(fb)} = {txt(ERad(fa.indice, EProd((fa.rad, fb.rad))))} = "
                           f"{txt(nuevo_r)}."), f"{txt(fa)}·{txt(fb)}"
    return None


def _t_potencia_raiz(n: E):
    if isinstance(n, EPot) and isinstance(n.base, ERad) and isinstance(n.base.rad, ENum):
        k, m, N = n.base.indice, n.exp, n.base.rad.v
        if m % k == 0:
            nuevo = ENum(Fraction(N) ** (m // k))
            return nuevo, f"La potencia y la raíz se cancelan: {txt(n)} = {txt(nuevo)}.", txt(n)
        nuevo = ERad(k, ENum(Fraction(N) ** m))
        return nuevo, f"Elevamos lo de adentro: {txt(n)} = {txt(nuevo)}.", txt(n)
    return None


def _t_distribuir(n: E):
    if isinstance(n, (EProd, EPot)) and _hay_producto(n) and _tiene_radical(n):
        nuevo = _distribuida(n)
        return nuevo, (f"Aplicamos la propiedad distributiva: {txt(n)} = {txt(nuevo)}."), txt(n)
    return None


def _t_signo(n: E):
    if isinstance(n, ENeg) and isinstance(n.x, ESum):
        nuevo = ESum(tuple(neg(t) for t in n.x.terminos))
        return nuevo, (f"Quitamos el paréntesis: el signo − de adelante cambia el signo de todos los términos de "
                       f"adentro: {txt(n)} = {txt(nuevo)}."), txt(n)
    return None


def _t_racionalizar(n: E):
    if not (isinstance(n, EFrac) and _tiene_radical(n.den)):
        return None
    sp = _sp()
    den = n.den
    cr = _coef_y_radical(den)
    if cr is not None and cr[1] is not None:                      # denominador: c·√n  (o ∛n, ∜n)
        c, k, N = cr
        factor = ERad(k, ENum(Fraction(N) ** (k - 1)))
        nuevo_num = EProd((n.num, factor))
        nuevo_den = ENum(c * N)
        if c * N < 0:
            nuevo_num, nuevo_den = neg(nuevo_num), ENum(-c * N)
        nuevo = nuevo_num if (isinstance(nuevo_den, ENum) and nuevo_den.v == 1) else EFrac(nuevo_num, nuevo_den)
        rad_txt = txt(ERad(k, ENum(Fraction(N))))
        return nuevo, (f"Racionalizamos el denominador {txt(den)}: multiplicamos el numerador y el denominador por "
                       f"{txt(factor)}, que hace desaparecer la raíz ({rad_txt}·{txt(factor)} = {N}). "
                       f"Queda {txt(nuevo)}."), txt(den)
    if isinstance(den, ESum) and len(den.terminos) == 2:          # denominador: binomio con √  →  conjugado
        crs = [_coef_y_radical(t) for t in den.terminos]
        if all(cr is not None and cr[1] in (None, 2) for cr in crs):
            conj = ESum((den.terminos[0], neg(den.terminos[1])))
            producto = sp.expand(_valor(den) * _valor(conj))
            if producto.is_Rational and producto != 0:
                p_ = Fraction(int(producto.p), int(producto.q))
                nuevo_num = EProd((n.num, conj))
                nuevo_den = num(p_)
                if p_ < 0:
                    nuevo_num, nuevo_den = neg(nuevo_num), num(-p_)
                nuevo = nuevo_num if (isinstance(nuevo_den, ENum) and nuevo_den.v == 1) else EFrac(nuevo_num, nuevo_den)
                return nuevo, (f"Racionalizamos con el conjugado: el conjugado de {txt(den)} es {txt(conj)}, y "
                               f"({txt(den)})({txt(conj)}) = {txt(num(p_))} (sin raíces, porque es una suma por una "
                               f"diferencia). Multiplicamos arriba y abajo"
                               f"{' (y como el denominador es negativo, cambiamos el signo de todo)' if p_ < 0 else ''}: "
                               f"{txt(nuevo)}."), txt(den)
    return None


def _t_fraccion_numerica(n: E):
    """a/b con números, o (suma de términos con números)/d con un factor común numérico."""
    if not isinstance(n, EFrac):
        return None
    if isinstance(n.num, ENum) and isinstance(n.den, ENum):
        v = n.num.v / n.den.v
        if v.denominator == 1 or (n.num.v.denominator == 1 and n.den.v.denominator == 1 and
                                  math.gcd(int(n.num.v), int(n.den.v)) > 1):
            nuevo = num(v)
            return nuevo, f"Simplificamos la fracción: {txt(n)} = {txt(nuevo)}.", txt(n)
        return None
    if not (isinstance(n.den, ENum) and n.den.v.denominator == 1 and n.den.v > 1):
        return None
    terminos = n.num.terminos if isinstance(n.num, ESum) else (n.num,)
    coefs = []
    for t in terminos:
        cr = _coef_y_radical(t)
        if cr is None or cr[0].denominator != 1:
            return None
        coefs.append(abs(int(cr[0])))
    g = math.gcd(int(n.den.v), *coefs)
    if g <= 1:
        return None

    def dividir(t: E) -> E:
        signo, x = (-1, t.x) if isinstance(t, ENeg) else (1, t)
        if isinstance(x, ENum):
            nuevo_t = ENum(x.v / g)
        elif isinstance(x, EProd):
            nuevo_t = EProd((ENum(x.factores[0].v / g), *x.factores[1:]))
        else:
            nuevo_t = x if g == 1 else EProd((ENum(Fraction(1, g)), x))
        return ENeg(nuevo_t) if signo < 0 else nuevo_t

    nuevo_num = ESum(tuple(dividir(t) for t in terminos)) if isinstance(n.num, ESum) else dividir(n.num)
    nuevo_den = n.den.v / g
    nuevo = nuevo_num if nuevo_den == 1 else EFrac(nuevo_num, ENum(nuevo_den))
    return _limpiar(nuevo), (f"Hay un factor común, {g}, en todo el numerador y en el denominador: lo dividimos en "
                              f"cada término y simplificamos: {txt(n)} = {txt(_limpiar(nuevo))}."), txt(n)


def _t_combinar(n: E):
    if not isinstance(n, ESum):
        return None
    grupos: dict = {}
    orden_claves = []
    otros = []
    for t in n.terminos:
        cr = _coef_y_radical(t)
        if cr is None:
            otros.append(t)
            continue
        clave = None if cr[1] is None else (cr[1], cr[2])
        if clave not in grupos:
            grupos[clave] = []
            orden_claves.append(clave)
        grupos[clave].append(cr[0])
    if not any(len(v) > 1 for v in grupos.values()):
        return None
    salida, partes = [], []
    claves = sorted(orden_claves, key=lambda c: (0, 0, 0) if c is None else (1, c[0], c[1]))
    for c in claves:
        total = sum(grupos[c], Fraction(0))
        if len(grupos[c]) > 1:
            if c is None:
                partes.append(" + ".join(txt(num(v)) for v in grupos[c]) + f" = {txt(num(total))}")
            else:
                r = txt(ERad(c[0], ENum(Fraction(c[1]))))
                partes.append(" + ".join(f"{txt(num(v))}{r}" if v != 1 else r for v in grupos[c]).replace("+ −", "− ")
                              + f" = {txt(_limpiar(EProd((num(total), ERad(c[0], ENum(Fraction(c[1])))))))}")
        if total == 0:
            continue
        salida.append(num(total) if c is None else _limpiar(EProd((num(total), ERad(c[0], ENum(Fraction(c[1])))))))
    salida += otros
    nuevo = ESum(tuple(salida)) if len(salida) > 1 else (salida[0] if salida else ENum(Fraction(0)))
    return nuevo, (f"Juntamos los términos semejantes de {txt(n)}: los números con los números, y los radicales que "
                   "tienen el mismo índice y el mismo número adentro, sumando sus coeficientes. "
                   + "; ".join(partes) + "."), txt(n)


_TRANSFORMACIONES = [
    ("raiz_interna", _t_raiz_interna), ("raiz_fraccion", _t_raiz_fraccion), ("simplificar_raiz", _t_simplificar_raiz),
    ("multiplicar_raices", _t_multiplicar_radicales), ("potencia_raiz", _t_potencia_raiz),
    ("distribuir", _t_distribuir), ("quitar_parentesis", _t_signo), ("racionalizar", _t_racionalizar),
    ("fraccion_numerica", _t_fraccion_numerica), ("combinar", _t_combinar),
]


def _aplicar(e: E, f):
    """Aplica `f` al primer nodo (en orden de lectura) donde sirva; devuelve (árbol nuevo, explicación, operación)."""
    r = f(e)
    if r is not None:
        return r
    hijos = _hijos(e)
    for i, h in enumerate(hijos):
        r = _aplicar(h, f)
        if r is not None:
            nuevo_h, expl, op = r
            nuevos = list(hijos)
            nuevos[i] = nuevo_h
            return _con_hijos(e, nuevos), expl, op
    return None


# ---------------------------------------------------------------------------
# Evaluar con decimales (verificación independiente de SymPy)
# ---------------------------------------------------------------------------

def _decimal(e: E) -> float:
    if isinstance(e, ENum):
        return float(e.v)
    if isinstance(e, ENeg):
        return -_decimal(e.x)
    if isinstance(e, ESum):
        return sum(_decimal(t) for t in e.terminos)
    if isinstance(e, EProd):
        r = 1.0
        for f in e.factores:
            r *= _decimal(f)
        return r
    if isinstance(e, EPot):
        return _decimal(e.base) ** e.exp
    if isinstance(e, EFrac):
        return _decimal(e.num) / _decimal(e.den)
    if isinstance(e, ERad):
        x = _decimal(e.rad)
        if x < 0:
            if e.indice % 2 == 0:
                raise ErrorMatematico("No existe la raíz de un número negativo en los números reales.")
            return -((-x) ** (1 / e.indice))
        return x ** (1 / e.indice)
    raise ErrorMotor(f"No sé evaluar {e!r}")  # pragma: no cover


def _ordenar(e: E) -> E:
    """Forma final de una suma: primero los números, luego los radicales de menor a mayor."""
    if not isinstance(e, ESum):
        return e
    claves = []
    for t in e.terminos:
        cr = _coef_y_radical(t)
        claves.append((0, 0, 0) if cr is None or cr[1] is None else (1, cr[1], cr[2]) if cr[1] else (2, 0, 0))
    pares = sorted(zip(claves, range(len(claves))))
    return ESum(tuple(e.terminos[i] for _, i in pares))


def _tiene_radical_en_denominador(e: E) -> bool:
    if isinstance(e, EFrac) and _tiene_radical(e.den):
        return True
    return any(_tiene_radical_en_denominador(h) for h in _hijos(e))


# ---------------------------------------------------------------------------
# Resolver
# ---------------------------------------------------------------------------

def resolver_radicales(texto: str, entrada: str | None = None) -> Solucion:
    """Simplifica y opera radicales con números (índices 2, 3 y 4), explicando cada paso."""
    if texto is None or not texto.strip():
        raise ErrorDeEntrada("Escribe una expresión con raíces, por ejemplo √12 o √50 + √8.")
    arbol, _ = parsear(texto)
    arbol = normalizar(_con_fracciones(normalizar(arbol)))
    e0 = _limpiar(desde_arbol(arbol))
    if not _tiene_radical(e0):
        raise ErrorMatematico("No hay raíces que simplificar en esa expresión.")
    libreta = Libreta(_MOTIVO)
    actual = e0
    if re.search(r"\^\s*\(?\s*\d+\s*/\s*\d+", texto):
        libreta.agregar("exponente_fraccionario",
                        "Un exponente fraccionario es una raíz: el denominador es el índice de la raíz y el numerador "
                        "es la potencia. Escribimos las potencias con exponente fraccionario como raíces.", e0)
    for _ in range(80):
        for nombre, f in _TRANSFORMACIONES:
            r = _aplicar(actual, f)
            if r is None:
                continue
            nuevo, expl, op = r
            nuevo = _limpiar(nuevo)
            if txt(nuevo) == txt(actual):
                continue
            actual = nuevo
            libreta.agregar(nombre, expl, actual, operacion=op)
            break
        else:
            break
    final = _ordenar(actual)
    if txt(final) != txt(actual):
        libreta.agregar("combinar", "Ordenamos: primero los números y después los radicales.", final)
    if not libreta.pasos:
        libreta.agregar("ya_simplificada", "Ya está simplificada: no hay raíces que se puedan simplificar ni "
                                           "denominadores con raíz.", final)
    nota = ""
    if _tiene_radical_en_denominador(final):
        nota = ("Todavía queda una raíz en un denominador que no sé racionalizar (solo manejo √n, ∛n, ∜n y "
                "binomios con una raíz cuadrada).")
    a, b = _decimal(e0), _decimal(final)
    if not math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9):  # pragma: no cover
        raise ErrorMotor(f"La verificación falló: {a} ≠ {b} ({txt(final)})")
    sol = solucion("radicales", entrada or texto, e0, libreta, final, nota=nota)
    if _tiene_radical(final):
        return Solucion(**{**sol.__dict__, "resultado_decimal": f"{b:.6f}".rstrip("0").rstrip("."),
                           "decimal_exacto": False})
    return sol
