"""Fracciones algebraicas, como en el Álgebra de Baldor.

    (x² − 9)/(x − 3)                    →  factorizamos y cancelamos            →  x + 3
    1/(x − 1) + 1/(x + 1)               →  denominador común y suma             →  2x/((x − 1)(x + 1))
    (x + 1)/(x − 1) − 2/(x + 1)         →  denominador común y resta            →  (x² + 3)/((x − 1)(x + 1))
    (x² − 4)/(x + 1) · (x + 1)/(x − 2)  →  factorizamos, multiplicamos, cancelamos →  x + 2
    ((x+1)/(x−1)) ÷ ((x+2)/(x−1))       →  dividir es multiplicar por la inversa →  (x + 1)/(x + 2)

Siempre se factoriza (con la misma factorización por casos del libro) y se cancelan los factores comunes.
Al final se avisa de los valores que la expresión original no permite (donde un denominador valdría 0):
«se supone que x ≠ 3 y x ≠ 1». El resultado se verifica evaluando lo que escribió el estudiante con números.

Atención con las divisiones escritas sin paréntesis: «a/b ÷ c/d» se lee de izquierda a derecha, como en toda la
calculadora, es decir ((a/b) ÷ c)/d. Para dividir entre una fracción hay que ponerla entre paréntesis.
"""

from fractions import Fraction

from .algebra import Libreta, leer, solucion, verificar
from .errores import ErrorMatematico, ErrorMotor
from .expr import E, EFrac, ENeg, ENum, EPot, EProd, ESum, a_sympy, desde_sympy, neg, txt
from .factorizacion import _descomponer, _irreducible, _producto_E
from .pasos import Solucion
from .polinomios import _con_radicales

_MOTIVO = {
    "factorizar_num": "Para poder cancelar hay que ver los factores: solo se cancela lo que multiplica a TODO el "
                      "numerador y a TODO el denominador, nunca términos sueltos de una suma.",
    "factorizar_den": "Para poder cancelar hay que ver los factores del denominador también.",
    "cancelar": "Un factor que está en el numerador y en el denominador se puede cancelar porque su cociente es 1.",
    "ya_simplificada": "Si el numerador y el denominador no tienen factores en común, la fracción ya está simplificada.",
    "factorizar_denominadores": "Para encontrar el denominador común hay que ver los factores de cada denominador.",
    "denominador_comun": "El denominador común es el mínimo común múltiplo: cada factor con su mayor exponente. A cada "
                         "fracción se le multiplica arriba y abajo por lo que le falta, y así no cambia su valor.",
    "sumar_numeradores": "Con el mismo denominador, las fracciones se suman (o se restan) sumando (o restando) sus "
                         "numeradores y dejando el denominador igual. Cuidado: el signo − afecta a TODO el numerador "
                         "que resta.",
    "operar_numerador": "Se hacen las operaciones del numerador (productos y términos semejantes) para ver si se puede "
                        "simplificar después.",
    "multiplicar": "Para multiplicar fracciones se multiplican los numeradores entre sí y los denominadores entre sí; "
                   "dividir entre una fracción es multiplicar por su inversa.",
    "una_fraccion": "Para operar con fracciones dentro de fracciones, primero se escribe todo como una sola fracción.",
}


def _sp():
    import sympy
    return sympy


# ---------------------------------------------------------------------------
# Ayudas
# ---------------------------------------------------------------------------

def _poli(e: E):
    sp = _sp()
    return sp.expand(a_sympy(e, {}))


def _letras(e: E) -> bool:
    return bool(a_sympy(e, {}).free_symbols)


def _prod_fl(cont, factores, orden) -> E:
    """Un E con la factorización dada por `sympy.factor_list`: 2(x − 3)(x + 3)."""
    lista = [cont] if cont != 1 else []
    for base, mult in factores:
        lista += [base] * int(mult)
    return _producto_E(lista or [_sp().Integer(1)], orden)


def _factorizado(P, orden) -> E:
    sp = _sp()
    cont, fl = sp.factor_list(P)
    return _prod_fl(cont, fl, orden)


def _ya_factorizado(e: E) -> bool:
    """¿Lo que escribió el estudiante ya es un producto de factores que no se pueden factorizar más?"""
    if isinstance(e, ENum) or not _letras(e):
        return True
    if isinstance(e, EProd):
        return all(_ya_factorizado(f) for f in e.factores)
    if isinstance(e, EPot):
        return _ya_factorizado(e.base)
    if isinstance(e, ENeg):
        return _ya_factorizado(e.x)
    return _irreducible(_poli(e))


def _frac(n: E, d: E) -> E:
    return n if (isinstance(d, ENum) and d.v == 1) else EFrac(n, d)


def _fir(s: int, e: E) -> E:
    return e if s > 0 else neg(e)


def _restricciones(polys: list, orden) -> str:
    """«x ≠ 3 y x ≠ 1»: los valores donde alguno de esos denominadores valdría 0."""
    sp = _sp()
    vistos, textos = [], []
    for P in polys:
        if not P.free_symbols:
            continue
        _cont, fl = sp.factor_list(P)
        for f, _m in fl:
            if not f.free_symbols or any(sp.expand(f - g) == 0 for g in vistos):
                continue
            vistos.append(f)
            if len(f.free_symbols) == 1 and sp.Poly(f).degree() == 1:
                v = next(iter(f.free_symbols))
                valor = sp.solve(f, v)[0]
                textos.append(f"{v} ≠ {txt(desde_sympy(valor, orden))}")
            else:
                textos.append(f"{txt(desde_sympy(f, orden))} ≠ 0")
    if not textos:
        return ""
    lista = textos[0] if len(textos) == 1 else ", ".join(textos[:-1]) + " y " + textos[-1]
    return (f"Se supone que {lista}: con ese valor, un denominador de la expresión original valdría 0 y no se "
            f"podría calcular.")


def _hijos_e(e: E):
    if isinstance(e, ESum):
        return e.terminos
    if isinstance(e, EProd):
        return e.factores
    if isinstance(e, ENeg):
        return (e.x,)
    if isinstance(e, EFrac):
        return (e.num, e.den)
    if hasattr(e, "base"):
        return (e.base,)
    return ()


def _denominadores(e: E) -> list:
    """Todos los denominadores (y numeradores de los divisores) que aparecen en la expresión original."""
    salida = []
    if isinstance(e, EFrac):
        if isinstance(e.den, EFrac):             # a/(b/c): no pueden valer 0 ni b ni c
            salida += [_poli(e.den.num), _poli(e.den.den)]
        else:
            salida.append(_poli(e.den))
    for h in _hijos_e(e):
        salida += _denominadores(h)
    return salida


# ---------------------------------------------------------------------------
# Simplificar un cociente N/D (factorizar y cancelar)
# ---------------------------------------------------------------------------

def _simplificar_cociente(N, D, orden, libreta: Libreta, num_E: E, den_E: E) -> E:
    """Factoriza N y D explicando los casos, cancela lo común y devuelve la fracción final.
    `num_E` y `den_E` son como se están mostrando ahora."""
    sp = _sp()
    lista_n, casos_n = _descomponer(N, orden)
    lista_d, casos_d = _descomponer(D, orden)
    fn, fd = _producto_E(lista_n, orden), _producto_E(lista_d, orden)

    if not _ya_factorizado(num_E):
        casos = f" ({', '.join(casos_n)})" if casos_n else ""
        libreta.agregar("factorizar_num", f"Factorizamos el numerador{casos}: {txt(num_E)} = {txt(fn)}.",
                        _frac(fn, den_E), operacion=txt(num_E))
    num_E = fn
    if not _ya_factorizado(den_E):
        casos = f" ({', '.join(casos_d)})" if casos_d else ""
        libreta.agregar("factorizar_den", f"Factorizamos el denominador{casos}: {txt(den_E)} = {txt(fd)}.",
                        _frac(num_E, fd), operacion=txt(den_E))
    den_E = fd

    cn, fln = sp.factor_list(N)
    cd, fld = sp.factor_list(D)
    comunes, nuevo_n, nuevo_d = [], [], []
    por_base_d = {b: m for b, m in fld}
    for base, m in fln:
        k = por_base_d.get(base)
        if k is None:
            nuevo_n += [base] * int(m)
            continue
        c = min(int(m), int(k))
        comunes += [base] * c
        nuevo_n += [base] * (int(m) - c)
        nuevo_d += [base] * (int(k) - c)
        por_base_d[base] = 0
    for base, k in por_base_d.items():
        if k:
            nuevo_d += [base] * int(k)
    razon = sp.Rational(cn) / sp.Rational(cd)
    num_c, den_c = sp.Integer(razon.p), sp.Integer(razon.q)
    g = sp.gcd(abs(sp.Integer(cn)) if cn.is_Integer else 1, abs(sp.Integer(cd)) if cd.is_Integer else 1)
    comun_num = g if (cn.is_Integer and cd.is_Integer and g != 1) else None

    final_n = _producto_E(([num_c] if num_c != 1 else []) + nuevo_n or [sp.Integer(1)], orden)
    final_d = _producto_E(([den_c] if den_c != 1 else []) + nuevo_d or [sp.Integer(1)], orden)
    final = _frac(final_n, final_d)

    if not comunes and comun_num is None and txt(final) == txt(_frac(num_E, den_E)):
        libreta.agregar("ya_simplificada", "No hay factores comunes en el numerador y el denominador: la fracción ya "
                                           "está simplificada.", final)
        return final
    comun_E = _producto_E(comunes, orden) if comunes else None
    comun_t = "" if comun_E is None else (f"({txt(comun_E)})" if isinstance(comun_E, ESum) else txt(comun_E))
    partes = []
    if comunes:
        partes.append(("el factor " if len(comunes) == 1 else "los factores ") + comun_t)
    if comun_num is not None:
        partes.append(f"el número {comun_num}")
    texto = " y ".join(partes)
    libreta.agregar("cancelar", f"Cancelamos {texto}, que aparece en el numerador y en el denominador. Queda: "
                                f"{txt(final)}.", final, operacion=comun_t if comunes else f"{comun_num}")
    return final


# ---------------------------------------------------------------------------
# Los tipos de expresión
# ---------------------------------------------------------------------------

def _operando(t: E):
    """(signo, numerador, denominador) de un término de una suma."""
    s, x = (-1, t.x) if isinstance(t, ENeg) else (1, t)
    return (s, x.num, x.den) if isinstance(x, EFrac) else (s, x, ENum(Fraction(1)))


def _sumar(e0: ESum, orden, libreta: Libreta) -> E:
    sp = _sp()
    ops = [_operando(t) for t in e0.terminos]
    ns = [_poli(n) for _, n, _ in ops]
    ds = [_poli(d) for _, _, d in ops]
    L = sp.lcm(*ds)
    ms = [sp.cancel(L / d) for d in ds]
    cL, flL = sp.factor_list(L)
    L_E = _prod_fl(cL, flL, orden)

    dfs = [_factorizado(d, orden) for d in ds]
    if any(txt(a) != txt(b) for a, b in zip(dfs, [d for _, _, d in ops])):
        estado = ESum(tuple(_fir(s, _frac(n, df)) for (s, n, _), df in zip(ops, dfs)))
        libreta.agregar("factorizar_denominadores", "Factorizamos los denominadores para encontrar el denominador "
                                                    "común.", estado)
    mult_E = [None if m == 1 else _factorizado(m, orden) for m in ms]

    def producto(n: E, m):
        if m is None:
            return n
        if isinstance(n, ENum) and n.v == 1:
            return m
        piezas = list(m.factores) if isinstance(m, EProd) else [m]
        return EProd((n, *piezas))

    nums = [producto(n, m) for (_, n, _), m in zip(ops, mult_E)]
    estado = ESum(tuple(_fir(s, _frac(num, L_E)) for (s, _, _), num in zip(ops, nums)))
    libreta.agregar("denominador_comun",
                    f"El denominador común es {txt(L_E)} (el mínimo común múltiplo de los denominadores: cada factor "
                    f"con su mayor exponente). A cada fracción le multiplicamos el numerador y el denominador por lo "
                    f"que le falta.", estado, operacion=txt(L_E))
    suma_n = ESum(tuple(_fir(s, num) for (s, _, _), num in zip(ops, nums)))
    resta = any(s < 0 for s, _, _ in ops)
    libreta.agregar("sumar_numeradores",
                    "Como ya tienen el mismo denominador, " + ("sumamos y restamos" if resta else "sumamos")
                    + f" los numeradores y dejamos el denominador igual: {txt(_frac(suma_n, L_E))}"
                    + (" (el signo − afecta a todo el numerador que resta)." if resta else "."),
                    _frac(suma_n, L_E))
    total = sp.expand(sum(s * n * m for (s, _, _), n, m in zip(ops, ns, ms)))
    n_canon = desde_sympy(total, orden)
    if txt(n_canon) != txt(suma_n):
        libreta.agregar("operar_numerador", "Hacemos las operaciones del numerador y juntamos los términos "
                                            f"semejantes: {txt(suma_n)} = {txt(n_canon)}.", _frac(n_canon, L_E))
    if total == 0:
        libreta.agregar("cancelar", "El numerador vale 0, así que toda la expresión vale 0.", ENum(Fraction(0)))
        return ENum(Fraction(0))
    return _simplificar_cociente(total, sp.expand(L), orden, libreta, n_canon, L_E)


def _aplanar(e: E) -> tuple[list, list]:
    """(numeradores, denominadores) tales que e = (producto de numeradores)/(producto de denominadores).
    Aplana productos y cocientes: A/B · C/D  →  numeradores [A, C], denominadores [B, D]."""
    if isinstance(e, EFrac):
        na, da = _aplanar(e.num)
        nb, db = _aplanar(e.den)
        return na + db, da + nb
    if isinstance(e, EProd):
        ns, ds = [], []
        for f in e.factores:
            n, d = _aplanar(f)
            ns += n
            ds += d
        return ns, ds
    return [e], []


def _junto(fs: list) -> E:
    piezas = []
    for f in fs:
        if isinstance(f, ENum) and f.v == 1:
            continue
        piezas += list(f.factores) if isinstance(f, EProd) else [f]
    if not piezas:
        return ENum(Fraction(1))
    return piezas[0] if len(piezas) == 1 else EProd(tuple(piezas))


def _una_fraccion(e0: E, orden, libreta: Libreta) -> E:
    """Productos y cocientes de fracciones: se escribe todo como UNA fracción y se simplifica."""
    sp = _sp()
    ns, ds = _aplanar(e0)
    n_junto, d_junto = _junto(ns), _junto(ds)
    una = _frac(n_junto, d_junto)
    if txt(una) != txt(e0):
        divide = isinstance(e0, EFrac) and (isinstance(e0.den, EFrac) or isinstance(e0.num, EFrac))
        msg = ("Dividir entre una fracción es multiplicar por su inversa (la fracción dada vuelta). Después se "
               "multiplican los numeradores entre sí y los denominadores entre sí" if divide else
               "Multiplicamos los numeradores entre sí y los denominadores entre sí")
        libreta.agregar("multiplicar", f"{msg}: {txt(una)}.", una)
    N = sp.expand(sp.Mul(*[_poli(n) for n in ns]))
    D = sp.expand(sp.Mul(*[_poli(d) for d in ds])) if ds else sp.Integer(1)
    return _simplificar_cociente(N, D, orden, libreta, n_junto, d_junto)


def resolver_fraccion(texto: str, entrada: str | None = None) -> Solucion:
    """Simplifica, suma, resta, multiplica o divide fracciones algebraicas explicando cada paso."""
    sp = _sp()
    arbol, e0, orden = leer(texto)
    if _con_radicales(e0):
        raise ErrorMatematico("Por ahora las fracciones algebraicas no llevan raíces. Las raíces con números se "
                              "simplifican sin letras: prueba con √12.")
    libreta = Libreta(_MOTIVO)
    restr = _restricciones(_denominadores(e0), orden)

    if isinstance(e0, ESum) and any(isinstance(t.x if isinstance(t, ENeg) else t, EFrac) for t in e0.terminos):
        final = _sumar(e0, orden, libreta)
    elif isinstance(e0, EFrac) or (isinstance(e0, EProd) and any(isinstance(f, EFrac) for f in e0.factores)):
        final = _una_fraccion(e0, orden, libreta)
    else:
        # cualquier otra forma: se escribe como una sola fracción y se simplifica
        T = sp.together(a_sympy(e0, {}))
        N, D = (sp.expand(x) for x in sp.fraction(T))
        if not D.free_symbols:
            raise ErrorMatematico("Esto no tiene letras en un denominador: para quitar paréntesis y juntar términos "
                                  "escribe «desarrollar …».")
        junta = _frac(desde_sympy(N, orden), desde_sympy(D, orden))
        libreta.agregar("una_fraccion", f"Escribimos todo como una sola fracción: {txt(junta)}.", junta)
        final = _simplificar_cociente(N, D, orden, libreta, desde_sympy(N, orden), desde_sympy(D, orden))

    # el resultado no puede cambiar el valor de lo que escribió el estudiante
    original = a_sympy(e0, {})
    if sp.cancel(sp.together(original - a_sympy(final, {}))) != 0:  # pragma: no cover
        raise ErrorMotor(f"La simplificación falló: {txt(final)}")
    verificar(arbol, final)
    return solucion("fraccion_algebraica", entrada or texto, e0, libreta, final, nota=restr, prefijo="simplificar ")
