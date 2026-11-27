"""Factorización por casos, como en el Álgebra de Baldor.

    x² − 9             →  diferencia de cuadrados            →  (x − 3)(x + 3)
    x² + 5x + 6        →  trinomio de la forma x² + bx + c    →  (x + 2)(x + 3)
    2x² + 7x + 3       →  trinomio ax² + bx + c               →  (x + 3)(2x + 1)
    x² + 6x + 9        →  trinomio cuadrado perfecto          →  (x + 3)²
    2x² − 18           →  factor común y diferencia de cuadrados  →  2(x − 3)(x + 3)
    ax + ay + bx + by  →  agrupación de términos              →  (a + b)(x + y)
    x³ − 8             →  diferencia de cubos                 →  (x − 2)(x² + 2x + 4)

Se prueba, en orden: factor común → (según el número de términos) diferencia de cuadrados / suma o diferencia de
cubos / trinomio cuadrado perfecto / x² + bx + c / ax² + bx + c / cubo perfecto / agrupación. Cada factor que
resulta se vuelve a revisar hasta que ya no se pueda factorizar más (polinomio irreducible).
Si ningún caso del libro aplica pero SymPy sí encuentra factores (por ejemplo con raíces racionales), se muestra
como «método avanzado» en vez de dejar al estudiante sin respuesta.

Al final se comprueba que el producto, multiplicado de nuevo, da el polinomio original, y que cada factor es irreducible.
"""

from fractions import Fraction
from math import prod

from .algebra import Libreta, leer, solucion, verificar
from .aritmetica import _raiz_entera
from .errores import ErrorMatematico, ErrorMotor
from .expr import (E, ENeg, ENum, EPot, EProd, ESim, ESum, _clave_factor, _clave_termino, a_sympy, desde_sympy, neg,
                   num, txt)
from .pasos import Solucion

_MOTIVO = {
    "ordenar": "Para factorizar conviene tener el polinomio desarrollado y ordenado de mayor a menor grado.",
    "factor_comun": "Si todos los términos comparten un número o una letra, se saca primero como factor común: así lo "
                    "que queda adentro es más sencillo de factorizar.",
    "diferencia_cuadrados": "Una resta de dos cuadrados perfectos siempre se factoriza como la suma por la diferencia "
                            "de sus raíces: es el producto notable al revés.",
    "trinomio_cuadrado_perfecto": "Un trinomio cuadrado perfecto es el desarrollo de un binomio al cuadrado: factorizarlo "
                                  "es devolverlo a ese binomio.",
    "trinomio_simple": "Al multiplicar (x + m)(x + n) sale x² + (m + n)x + mn: por eso se buscan dos números cuya suma "
                       "es el coeficiente de x y cuyo producto es el término independiente.",
    "trinomio_general_1": "Se parte el término del medio en dos para poder agrupar: los dos números multiplican "
                          "a·c y suman b.",
    "trinomio_general_2": "En cada grupo se saca el factor común; si se hizo bien, el binomio que queda es el mismo "
                          "en los dos grupos.",
    "trinomio_general_3": "Cuando el mismo binomio aparece en los dos grupos, se saca como factor común de todo.",
    "suma_cubos": "La suma y la diferencia de cubos tienen fórmulas fijas: un binomio por un trinomio que no se puede "
                  "factorizar más.",
    "cubo_perfecto": "Un cubo perfecto de binomio es el desarrollo de (a ± b)³: factorizarlo es devolverlo al binomio.",
    "agrupacion_1": "Con cuatro términos se prueba agrupar de dos en dos, buscando que cada grupo tenga un factor "
                    "común y que el binomio que sobra sea el mismo.",
    "agrupacion_2": "Cuando el mismo binomio aparece en los dos grupos, se saca como factor común de todo.",
    "metodo_avanzado": "Hay polinomios que no encajan en los casos básicos pero se factorizan buscando sus raíces "
                       "racionales; el resultado se puede comprobar multiplicando.",
    "irreducible": "Un polinomio que no se puede escribir como producto de otros polinomios más sencillos "
                   "(con coeficientes racionales) se llama irreducible.",
}

_NOMBRE = {
    "factor_comun": "factor común", "diferencia_cuadrados": "diferencia de cuadrados",
    "trinomio_cuadrado_perfecto": "trinomio cuadrado perfecto", "trinomio_simple": "trinomio x² + bx + c",
    "trinomio_general_1": "trinomio ax² + bx + c", "suma_cubos": "suma o diferencia de cubos",
    "cubo_perfecto": "cubo perfecto de binomio", "agrupacion_1": "agrupación de términos",
    "metodo_avanzado": "método avanzado (raíces racionales)",
}


def _sp():
    import sympy
    return sympy


# ---------------------------------------------------------------------------
# Ayudas matemáticas
# ---------------------------------------------------------------------------

def _raiz_racional(c, n: int):
    sp = _sp()
    if c == 0:
        return None
    signo = 1
    if c < 0:
        if n % 2 == 0:
            return None
        signo, c = -1, -c
    rp, rq = _raiz_entera(int(c.p), n), _raiz_entera(int(c.q), n)
    if rp is None or rq is None:
        return None
    return signo * sp.Rational(rp, rq)


def _raiz_monomio(t, n: int):
    """Raíz n-ésima exacta de un monomio (con signo si n es impar), o None."""
    sp = _sp()
    coef, resto = t.as_coeff_Mul()
    rc = _raiz_racional(coef, n)
    if rc is None:
        return None
    salida = rc
    for g in sp.Mul.make_args(resto):
        if g == 1:
            continue
        base, ex = g.as_base_exp()
        if not base.is_Symbol or not ex.is_Integer or ex % n != 0 or ex <= 0:
            return None
        salida *= base ** (int(ex) // n)
    return salida


def _dos_numeros(suma: int, producto: int):
    """Dos enteros que suman `suma` y multiplican `producto`, o None."""
    if producto == 0:
        return None
    for m in range(1, abs(producto) + 1):
        if producto % m:
            continue
        for a in (m, -m):
            b = producto // a
            if a + b == suma:
                return (a, b) if abs(a) <= abs(b) else (b, a)
    return None


def _factor_comun(f, orden):
    """(g, resto) tales que f = g·resto, con g el mayor factor común (número, letras y signo del primer término)."""
    sp = _sp()
    gens = sorted(f.free_symbols, key=lambda s: orden.get(str(s), 99))
    poly = sp.Poly(f, *gens)
    cont, primitivo = poly.primitive()
    exps, sin_monomio = primitivo.terms_gcd()
    mono = prod(g ** e for g, e in zip(gens, exps))
    g, resto = cont * mono, sin_monomio
    if resto.LC() < 0:                      # el polinomio de adentro siempre empieza con coeficiente positivo
        g, resto = -g, -resto
    return g, resto.as_expr()


def _neg(g) -> bool:
    """¿El factor (que puede llevar letras) empieza con signo menos?"""
    return g.as_coeff_Mul()[0] < 0


def _mag(g):
    """El factor sin su signo menos (sirve con letras, a diferencia de abs)."""
    return -g if _neg(g) else g


def _term(coef, v, exp):
    """coef·v^exp como E (coef entero con signo)."""
    base = ESim(str(v))
    pieza = base if exp == 1 else (EPot(base, exp) if exp > 1 else None)
    c = abs(coef)
    if pieza is None:
        t = num(c)
    elif c == 1:
        t = pieza
    else:
        t = EProd((num(c), pieza))
    return neg(t) if coef < 0 else t


def _grupo_E(g, e_r: E, orden) -> E:
    """g(binomio) como término de una suma: con su signo, y sin escribir un 1 de más."""
    m = desde_sympy(_mag(g), orden)
    if isinstance(m, ENum) and m.v == 1:
        pieza = e_r
    else:
        pieza = EProd((*(m.factores if isinstance(m, EProd) else (m,)), e_r))
    return neg(pieza) if _neg(g) else pieza


def _producto_E(factores, orden) -> E:
    """El producto de una lista de factores (expresiones de SymPy), escrito como se escribe en un libro:
    número, letras, y después los paréntesis; los iguales se juntan en una potencia: (x + 3)²."""
    sp = _sp()
    c = sp.Integer(1)
    letras = sp.Integer(1)
    sumas: dict = {}
    for f in factores:
        coef, resto = f.as_coeff_Mul()
        c *= coef
        for g in sp.Mul.make_args(resto):
            if g == 1:
                continue
            base, ex = g.as_base_exp()
            if base.is_Add:
                sumas[base] = sumas.get(base, 0) + int(ex)
            else:
                letras *= g
    piezas = []
    if abs(c) != 1:
        piezas.append(desde_sympy(abs(c), orden))
    if letras != 1:
        el = desde_sympy(letras, orden)
        piezas += list(el.factores) if isinstance(el, EProd) else [el]
    for base in sorted(sumas, key=lambda b: _clave_factor(b, orden)):
        eb = desde_sympy(base, orden)
        piezas.append(eb if sumas[base] == 1 else EPot(eb, sumas[base]))
    if not piezas:
        piezas = [ENum(Fraction(1))]
    e = piezas[0] if len(piezas) == 1 else EProd(tuple(piezas))
    return ENeg(e) if c < 0 else e


def _componer(lista, i, local: E, orden) -> E:
    """El producto de todos los factores, con el factor número i reemplazado por `local` (una forma intermedia)."""
    otros = lista[:i] + lista[i + 1:]
    resto = _producto_E(otros, orden) if otros else None
    if resto is None or (isinstance(resto, ENum) and resto.v == 1):
        return local
    signo = isinstance(resto, ENeg)
    base = resto.x if signo else resto
    piezas = list(base.factores) if isinstance(base, EProd) else [base]
    e = EProd(tuple(piezas + [local]))
    return ENeg(e) if signo else e


# ---------------------------------------------------------------------------
# Los casos. Cada uno devuelve {"nuevos": [factores], "pasos": [{regla, explicacion, local, operacion, previo}]}
# El último paso tiene local=None: significa «el producto con los factores nuevos».
# ---------------------------------------------------------------------------

def _paso(regla, explicacion, local=None, operacion="", previo=None):
    return dict(regla=regla, explicacion=explicacion, local=local, operacion=operacion, previo=previo)


def _caso_factor_comun(f, orden, permitir_signo=True):
    g, resto = _factor_comun(f, orden)
    if g == 1:
        return None
    if g == -1:
        if not permitir_signo or _caso(resto, orden, permitir_signo=False) is None:
            return None
        gt = txt(desde_sympy(g, orden))
        expl = (f"Sacamos el signo menos ({gt}) como factor común: los términos de adentro cambian todos de signo, "
                f"y así queda un polinomio más fácil de factorizar.")
        return dict(nuevos=[g, resto], pasos=[_paso("factor_comun", expl, None, gt)])
    gt = txt(desde_sympy(g, orden))
    partes = []
    cont = g.as_coeff_Mul()[0]
    if abs(cont) != 1:
        partes.append(f"el mayor número que divide a todos los coeficientes es {abs(cont)}")
    letras = g / cont
    if letras != 1:
        partes.append(f"las letras que están en todos los términos son {txt(desde_sympy(letras, orden))} "
                      f"(con el menor exponente)")
    if cont < 0:
        partes.append("el primer término es negativo, así que el signo menos también sale")
    expl = (f"Primero buscamos un factor común: {'; '.join(partes)}. El factor común es {gt}. Dentro del paréntesis "
            f"queda cada término dividido entre {gt}.")
    return dict(nuevos=[g, resto], pasos=[_paso("factor_comun", expl, None, gt)])


def _caso_dos_terminos(f, terminos, orden):
    sp = _sp()
    pos = [t for t in terminos if t.as_coeff_Mul()[0] > 0]
    neg_ = [t for t in terminos if t.as_coeff_Mul()[0] < 0]
    if len(pos) == 1 and len(neg_) == 1:
        a, b = _raiz_monomio(pos[0], 2), _raiz_monomio(-neg_[0], 2)
        if a is not None and b is not None:
            at, bt = txt(desde_sympy(a, orden)), txt(desde_sympy(b, orden))
            expl = (f"Es una diferencia de cuadrados: los dos términos son cuadrados perfectos y se restan. "
                    f"Fórmula: a² − b² = (a − b)(a + b). Aquí a = {at} (porque {at}² = {txt(desde_sympy(pos[0], orden))}) "
                    f"y b = {bt} (porque {bt}² = {txt(desde_sympy(-neg_[0], orden))}).")
            return dict(nuevos=[a - b, a + b], pasos=[_paso("diferencia_cuadrados", expl, None, f"a = {at}",
                                                            ("a² − b² = (a − b)(a + b)", "a^{2} - b^{2} = (a - b)(a + b)"))])
    a, b = _raiz_monomio(terminos[0], 3), _raiz_monomio(terminos[1], 3)
    if a is not None and b is not None:
        resta = _neg(b)
        at, bt = txt(desde_sympy(a, orden)), txt(desde_sympy(_mag(b), orden))
        if resta:
            formula = ("a³ − b³ = (a − b)(a² + ab + b²)", "a^{3} - b^{3} = (a - b)(a^{2} + ab + b^{2})")
            nombre = "una diferencia de cubos"
        else:
            formula = ("a³ + b³ = (a + b)(a² − ab + b²)", "a^{3} + b^{3} = (a + b)(a^{2} - ab + b^{2})")
            nombre = "una suma de cubos"
        expl = (f"Es {nombre}: los dos términos son cubos perfectos. Fórmula: {formula[0]}. Aquí a = {at} y b = {bt}. "
                f"El trinomio que resulta no se puede factorizar más.")
        return dict(nuevos=[a + b, sp.expand(a ** 2 - a * b + b ** 2)],
                    pasos=[_paso("suma_cubos", expl, None, f"a = {at}", formula)])
    return None


def _sup(k: int) -> str:
    return {2: "²", 3: "³"}.get(k, f"^{k}")


def _cuadratico_en(f, v):
    """(k, a, b, c) si f = a·v^(2k) + b·v^k + c con coeficientes enteros y k >= 1; si no, None."""
    sp = _sp()
    P = sp.Poly(f, v)
    gr = {m[0]: c for m, c in P.terms()}
    if len(gr) != 3 or 0 not in gr:
        return None
    mayor = max(gr)
    k = mayor // 2
    if mayor != 2 * k or k < 1 or k not in gr or not all(c.is_Integer for c in gr.values()):
        return None
    return k, int(gr[mayor]), int(gr[k]), int(gr[0])


def _caso_tres_terminos(f, terminos, orden):
    sp = _sp()
    # trinomio cuadrado perfecto
    for i in range(3):
        for j in range(i + 1, 3):
            ti, tj = terminos[i], terminos[j]
            if ti.as_coeff_Mul()[0] <= 0 or tj.as_coeff_Mul()[0] <= 0:
                continue
            a, b = _raiz_monomio(ti, 2), _raiz_monomio(tj, 2)
            if a is None or b is None:
                continue
            medio = terminos[3 - i - j]
            for signo in (1, -1):
                if sp.expand(medio - signo * 2 * a * b) == 0:
                    at, bt = txt(desde_sympy(a, orden)), txt(desde_sympy(b, orden))
                    dos_ab = txt(desde_sympy(2 * a * b, orden))
                    expl = (f"Es un trinomio cuadrado perfecto: el primer y el último término son cuadrados perfectos "
                            f"(a = {at} y b = {bt}) y el del medio es el doble del producto de las raíces "
                            f"(2ab = {dos_ab}). Se factoriza como (a {'+' if signo > 0 else '−'} b)². "
                            f"Aquí queda ({at} {'+' if signo > 0 else '−'} {bt})².")
                    formula = (("a² + 2ab + b² = (a + b)²", "a^{2} + 2ab + b^{2} = (a + b)^{2}") if signo > 0 else
                               ("a² − 2ab + b² = (a − b)²", "a^{2} - 2ab + b^{2} = (a - b)^{2}"))
                    return dict(nuevos=[a + signo * b, a + signo * b],
                                pasos=[_paso("trinomio_cuadrado_perfecto", expl, None, f"a = {at}", formula)])
    # trinomios con dos letras: x² + bxy + cy²
    if len(f.free_symbols) == 2:
        x, y = sorted(f.free_symbols, key=lambda t: orden.get(str(t), 99))
        P2 = sp.Poly(f, x, y)
        if P2.is_homogeneous and P2.total_degree() == 2:
            d = {m: int(c) for m, c in P2.terms() if c.is_Integer}
            a2, b2, c2 = d.get((2, 0), 0), d.get((1, 1), 0), d.get((0, 2), 0)
            mn2 = _dos_numeros(b2, c2) if (a2 == 1 and len(d) == 3) else None
            if mn2:
                m, n = mn2
                xt, yt = str(x), str(y)
                expl = (f"Es un trinomio con dos letras de la forma {xt}² + b{xt}{yt} + c{yt}²: se factoriza igual que "
                        f"{xt}² + bx + c. Buscamos dos números que multiplicados den c = {c2} y sumados den b = {b2}: "
                        f"son {m} y {n}. Los ponemos acompañados de {yt}.")
                return dict(nuevos=[x + m * y, x + n * y], pasos=[_paso(
                    "trinomio_simple", expl, None, f"{m} y {n}",
                    ("x² + bxy + cy² = (x + my)(x + ny)", "x^{2} + bxy + cy^{2} = (x + my)(x + ny)"))])
        return None
    # trinomios en una sola letra: ax^(2k) + bx^k + c  (x^k hace de «letra»)
    if len(f.free_symbols) != 1:
        return None
    v = next(iter(f.free_symbols))
    cuad = _cuadratico_en(f, v)
    if cuad is None:
        return None
    k, a, b, c = cuad
    if a < 0:
        return None
    ac = a * c
    mn = _dos_numeros(b, ac)
    if mn is None:
        return None
    m, n = mn
    vt = str(v)
    base = v ** k
    bt = vt if k == 1 else f"{vt}{_sup(k)}"
    aviso = "" if k == 1 else f" Aquí {bt} hace el papel de la letra (es como si fuera una sola)."
    if a == 1:
        expl = (f"Es un trinomio de la forma x² + bx + c.{aviso} Buscamos dos números que multiplicados den c = {c} y "
                f"sumados den b = {b}: son {m} y {n}. Entonces el trinomio es ({bt} {'+' if m > 0 else '−'} {abs(m)})"
                f"({bt} {'+' if n > 0 else '−'} {abs(n)}).")
        return dict(nuevos=[base + m, base + n], pasos=[_paso(
            "trinomio_simple", expl, None, f"{m} y {n}",
            ("x² + bx + c = (x + m)(x + n)", "x^{2} + bx + c = (x + m)(x + n)"))])
    # ax² + bx + c: se parte el término del medio y se agrupa
    for primero, segundo in ((m, n), (n, m)):
        g1, r1 = _factor_comun(sp.expand(a * base ** 2 + primero * base), {str(v): 0})
        g2, r2 = _factor_comun(sp.expand(segundo * base + c), {str(v): 0})
        if sp.expand(r1 - r2) == 0:
            break
    else:
        return None
    cuatro = ESum(tuple([_term(a, vt, 2 * k), _term(primero, vt, k), _term(segundo, vt, k), _term(c, vt, 0)]))
    e_r = desde_sympy(r1, orden)
    agrupado = ESum((_grupo_E(g1, e_r, orden), _grupo_E(g2, e_r, orden)))
    expl1 = (f"Es un trinomio de la forma ax² + bx + c con a = {a}.{aviso} Buscamos dos números que multiplicados den "
             f"a·c = {ac} y sumados den b = {b}: son {primero} y {segundo}. Partimos el término del medio: "
             f"{b}{bt} = {primero}{bt} + {segundo}{bt}.")
    expl2 = (f"Agrupamos los dos primeros y los dos últimos términos, y sacamos el factor común de cada grupo: "
             f"{txt(desde_sympy(g1, orden))} en el primero y {txt(desde_sympy(g2, orden))} en el segundo. En los dos "
             f"queda el mismo binomio ({txt(e_r)}).")
    expl3 = (f"Como ({txt(e_r)}) está en los dos grupos, lo sacamos como factor común: lo que queda es "
             f"({txt(desde_sympy(g1 + g2, orden))}).")
    return dict(nuevos=[g1 + g2, r1], pasos=[
        _paso("trinomio_general_1", expl1, cuatro, f"{primero} y {segundo}"),
        _paso("trinomio_general_2", expl2, agrupado, txt(e_r)),
        _paso("trinomio_general_3", expl3, None, txt(e_r)),
    ])


def _caso_cuatro_terminos(f, terminos, orden):
    sp = _sp()
    # cubo perfecto de un binomio
    a, b = _raiz_monomio(terminos[0], 3), _raiz_monomio(terminos[-1], 3)
    if a is not None and b is not None and sp.expand((a + b) ** 3 - f) == 0:
        at, bt = txt(desde_sympy(a, orden)), txt(desde_sympy(_mag(b), orden))
        signo = "−" if _neg(b) else "+"
        expl = (f"Es el cubo perfecto de un binomio: el primer y el último término son cubos perfectos "
                f"(a = {at} y b = {bt}) y los del medio son 3a²b y 3ab². Se factoriza como (a {signo} b)³. "
                f"Aquí queda ({at} {signo} {bt})³.")
        formula = (("a³ + 3a²b + 3ab² + b³ = (a + b)³", "a^{3} + 3a^{2}b + 3ab^{2} + b^{3} = (a + b)^{3}") if not _neg(b) else
                   ("a³ − 3a²b + 3ab² − b³ = (a − b)³", "a^{3} - 3a^{2}b + 3ab^{2} - b^{3} = (a - b)^{3}"))
        return dict(nuevos=[a + b] * 3, pasos=[_paso("cubo_perfecto", expl, None, f"a = {at}", formula)])
    # agrupación de dos en dos
    for izq, der in (((0, 1), (2, 3)), ((0, 2), (1, 3)), ((0, 3), (1, 2))):
        g1_, g2_ = sp.Add(*[terminos[k] for k in izq]), sp.Add(*[terminos[k] for k in der])
        g1, r1 = _factor_comun(g1_, orden)
        g2, r2 = _factor_comun(g2_, orden)
        if g1 == 1 and g2 == 1:
            continue
        if sp.expand(r1 - r2) != 0 or len(sp.Add.make_args(r1)) < 2:
            continue
        e_r = desde_sympy(r1, orden)
        grupo1 = ESum(tuple(desde_sympy(terminos[k], orden) for k in izq))
        grupo2 = ESum(tuple(desde_sympy(terminos[k], orden) for k in der))
        ya_agrupado = ESum((_grupo_E(g1, e_r, orden), _grupo_E(g2, e_r, orden)))
        expl1 = (f"Son cuatro términos: probamos agrupar de dos en dos. Grupo 1: {txt(grupo1)}, con factor común "
                 f"{txt(desde_sympy(g1, orden))}. Grupo 2: {txt(grupo2)}, con factor común {txt(desde_sympy(g2, orden))}. "
                 f"En los dos grupos queda el mismo binomio ({txt(e_r)}), así que la agrupación sirve.")
        expl2 = (f"Como ({txt(e_r)}) está en los dos grupos, lo sacamos como factor común de todo; lo que queda es "
                 f"({txt(desde_sympy(g1 + g2, orden))}).")
        return dict(nuevos=[g1 + g2, r1], pasos=[
            _paso("agrupacion_1", expl1, ya_agrupado, txt(e_r)),
            _paso("agrupacion_2", expl2, None, txt(e_r)),
        ])
    return None


def _caso_avanzado(f, orden):
    sp = _sp()
    cont, factores = sp.factor_list(f)
    if len(factores) == 1 and factores[0][1] == 1 and cont == 1:
        return None
    nuevos = [] if cont == 1 else [cont]
    for base, mult in factores:
        nuevos += [base] * int(mult)
    if len(nuevos) < 2:
        return None
    resultado = txt(_producto_E(nuevos, orden))
    expl = (f"Ningún caso básico aplica directamente, pero el polinomio se puede factorizar buscando sus raíces "
            f"racionales (método avanzado). Resultado: {resultado}. Se comprueba multiplicando los factores.")
    return dict(nuevos=nuevos, pasos=[_paso("metodo_avanzado", expl, None, resultado)])


def _caso(f, orden, permitir_signo=True):
    """El primer caso de factorización que aplica a `f`, o None si no se puede (más)."""
    sp = _sp()
    if f.is_Number or not f.free_symbols:
        return None
    terminos = sorted(sp.Add.make_args(sp.expand(f)), key=lambda t: _clave_termino(t, orden))
    if len(terminos) == 1:
        return None
    r = _caso_factor_comun(f, orden, permitir_signo)
    if r:
        return r
    n = len(terminos)
    r = None
    if n == 2:
        r = _caso_dos_terminos(f, terminos, orden)
    elif n == 3:
        r = _caso_tres_terminos(f, terminos, orden)
    elif n == 4:
        r = _caso_cuatro_terminos(f, terminos, orden)
    return r or _caso_avanzado(f, orden)


def _irreducible(f) -> bool:
    sp = _sp()
    if f.is_Number or not f.free_symbols or len(sp.Add.make_args(sp.expand(f))) == 1:
        return True                         # números y monomios no se factorizan más
    cont, factores = sp.factor_list(f)
    return len(factores) == 1 and factores[0][1] == 1


def _descomponer(P, orden, libreta=None):
    """Factoriza P por casos. Devuelve (lista de factores irreducibles, nombres de los casos usados).
    Si se da una libreta, va escribiendo en ella cada paso."""
    lista = [P]
    usados: list = []
    seguir, vueltas = True, 0
    while seguir and vueltas < 60:
        seguir = False
        vueltas += 1
        for i, f in enumerate(lista):
            caso = _caso(f, orden)
            if caso is None:
                continue
            for paso in caso["pasos"]:
                if paso["local"] is None:
                    lista[i:i + 1] = caso["nuevos"]
                    estado = _producto_E(lista, orden)
                else:
                    estado = _componer(lista, i, paso["local"], orden)
                if libreta is not None:
                    libreta.agregar(paso["regla"], paso["explicacion"], estado, operacion=paso["operacion"],
                                    previo=paso["previo"])
                nombre = _NOMBRE.get(paso["regla"])
                if nombre and nombre not in usados:
                    usados.append(nombre)
            seguir = True
            break
    return lista, usados


# ---------------------------------------------------------------------------
# Resolver
# ---------------------------------------------------------------------------

def resolver_factorizacion(texto: str, entrada: str | None = None) -> Solucion:
    """Factoriza un polinomio por casos y explica cada paso."""
    sp = _sp()
    from .polinomios import _con_division_por_letras, _con_radicales
    arbol, e0, orden = leer(texto)
    if _con_division_por_letras(e0) or _con_radicales(e0):
        raise ErrorMatematico("Por ahora factorizo polinomios: sin letras en un denominador ni dentro de una raíz. "
                              "Para fracciones con letras escribe «simplificar …».")
    P = sp.expand(a_sympy(e0, {}))
    if not P.free_symbols:
        raise ErrorMatematico("Para factorizar necesito una expresión con letras, como x² − 9.")
    canon = desde_sympy(P, orden)
    libreta = Libreta(_MOTIVO)

    if txt(e0) != txt(canon):
        libreta.agregar("ordenar", "Primero desarrollamos y ordenamos el polinomio de mayor a menor grado, "
                                   f"juntando los términos semejantes: {txt(e0)} = {txt(canon)}.", canon,
                        operacion=txt(e0))

    lista, usados = _descomponer(P, orden, libreta)

    final = _producto_E(lista, orden)
    if sp.expand(prod(lista) - P) != 0 or not all(_irreducible(f) for f in lista):  # pragma: no cover
        raise ErrorMotor(f"La factorización falló: {txt(final)}")

    nota = ""
    if not libreta.pasos or all(p.regla == "ordenar" for p in libreta.pasos):
        terminos = sp.Add.make_args(P)
        if len(terminos) == 1:
            expl = "Es un monomio (un solo término): no hay nada que factorizar."
            nota = "Un monomio ya es un producto de números y letras."
        else:
            expl = ("No se puede factorizar: ni hay factor común, ni encaja en diferencia de cuadrados, trinomios, "
                    "agrupación o cubos, ni tiene raíces racionales. Se dice que es un polinomio irreducible.")
            nota = "Es irreducible con coeficientes racionales."
        libreta.agregar("irreducible", expl, canon)
    else:
        nota = "Casos usados: " + ", ".join(usados) + "." if usados else ""
    verificar(arbol, final)
    return solucion("factorizacion", entrada or texto, e0, libreta, final, nota=nota, prefijo="factorizar ")
