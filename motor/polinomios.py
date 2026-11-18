"""Polinomios: quitar paréntesis, propiedad distributiva, productos notables y términos semejantes.

    (x + 3)²              →  es el cuadrado de un binomio: (a + b)² = a² + 2ab + b²  →  x² + 6x + 9
    (2x + 3)(2x − 3)      →  suma por diferencia: (a + b)(a − b) = a² − b²            →  4x² − 9
    (x + 2)(x + 5)        →  binomios con un término común                            →  x² + 7x + 10
    (3x² + 2x) − (x² − 5x) →  quitamos paréntesis (el − cambia los signos) y juntamos términos semejantes

El estudiante ve: la fórmula del producto notable (en gris), la fórmula ya puesta con sus valores,
y luego las operaciones hasta el resultado ordenado de mayor a menor grado.
"""

from fractions import Fraction
from math import comb

from .algebra import Libreta, leer, solucion, verificar
from .errores import ErrorMatematico
from .expr import E, EFrac, ENeg, ENum, EPot, EProd, ERad, ESum, a_sympy, desde_sympy, neg, txt
from .pasos import Solucion

_MOTIVO = {
    "producto_notable": "Los productos notables tienen una fórmula que da el resultado directo, sin multiplicar término "
                        "por término. Reconocerlos ahorra tiempo y evita errores.",
    "distribuir": "Cada término de un paréntesis se multiplica por cada término del otro; ningún término se queda sin "
                  "multiplicar.",
    "quitar_parentesis": "Con un signo + delante, los términos de adentro no cambian; con un signo − delante, todos "
                         "cambian de signo.",
    "reducir": "Los términos semejantes (los que tienen las mismas letras con los mismos exponentes) se suman o se "
               "restan sumando sus coeficientes; los demás no se pueden juntar.",
    "ya_reducida": "Si no hay paréntesis ni términos semejantes, la expresión ya está lista; solo se ordena de mayor "
                   "a menor grado.",
}


# ---------------------------------------------------------------------------
# Ayudas
# ---------------------------------------------------------------------------

def _sp():
    import sympy
    return sympy


def _firmados(e: E) -> list:
    """Los términos de una suma como (signo, magnitud)."""
    terminos = e.terminos if isinstance(e, ESum) else (e,)
    return [(-1, t.x) if isinstance(t, ENeg) else (1, t) for t in terminos]


def _fir(s: int, m: E) -> E:
    return m if s > 0 else ENeg(m)


def _igual(a: E, b: E) -> bool:
    sp = _sp()
    return sp.expand(a_sympy(a, {}) - a_sympy(b, {})) == 0


def _opuestos(a: E, b: E) -> bool:
    sp = _sp()
    return sp.expand(a_sympy(a, {}) + a_sympy(b, {})) == 0


def _letras(e: E) -> bool:
    return bool(a_sympy(e, {}).free_symbols)


def _es_binomio(e: E) -> bool:
    return isinstance(e, ESum) and len(e.terminos) == 2


# ---------------------------------------------------------------------------
# Productos notables
# ---------------------------------------------------------------------------

def _notable(e: E):
    """Si toda la expresión es un producto notable:
    (nombre, fórmula, explicación, a, b, forma con valores, etiqueta de valores)."""
    if isinstance(e, EPot) and isinstance(e.base, ESum):
        n = len(e.base.terminos)
        if n == 2 and e.exp in (2, 3):
            return _binomio_a_la(e.base, e.exp)
        if n == 2 and 4 <= e.exp <= 20:
            return _newton(e.base, e.exp)
        if n == 3 and e.exp == 2:
            return _trinomio_al_cuadrado(e.base)
        return None
    if isinstance(e, EProd) and len(e.factores) == 2 and all(_es_binomio(f) for f in e.factores):
        f1, f2 = e.factores
        if _igual(f1, f2):
            r = _binomio_a_la(f1, 2)
            return (r[0], r[1], "Los dos paréntesis son iguales: (a + b)(a + b) = (a + b)². " + r[2], *r[3:])
        return _suma_por_diferencia(f1, f2) or _termino_comun(f1, f2)
    return None


def _binomio_a_la(base: ESum, n: int):
    (s1, m1), (s2, m2) = _firmados(base)
    A, B = _fir(s1, m1), m2
    resta = s2 < 0
    etiqueta = f"a = {txt(A)} y b = {txt(B)}"
    if n == 2:
        t2 = EProd((ENum(Fraction(2)), A, B))
        valores = ESum((EPot(A, 2), neg(t2) if resta else t2, EPot(B, 2)))
        formula = "(a − b)² = a² − 2ab + b²" if resta else "(a + b)² = a² + 2ab + b²"
        explica = (f"El resultado es el cuadrado del primero, {'menos' if resta else 'más'} el doble del primero por "
                   f"el segundo, más el cuadrado del segundo.")
        return ("el cuadrado de un binomio", formula, explica, A, B, valores, etiqueta)
    t2 = EProd((ENum(Fraction(3)), EPot(A, 2), B))
    t3 = EProd((ENum(Fraction(3)), A, EPot(B, 2)))
    valores = ESum((EPot(A, 3), neg(t2) if resta else t2, t3, neg(EPot(B, 3)) if resta else EPot(B, 3)))
    formula = "(a − b)³ = a³ − 3a²b + 3ab² − b³" if resta else "(a + b)³ = a³ + 3a²b + 3ab² + b³"
    explica = ("El resultado es el cubo del primero, más (o menos) el triple del cuadrado del primero por el segundo, "
               "más el triple del primero por el cuadrado del segundo, más (o menos) el cubo del segundo.")
    return ("el cubo de un binomio", formula, explica, A, B, valores, etiqueta)


def _newton(base: ESum, n: int):
    (s1, m1), (s2, m2) = _firmados(base)
    A, B = _fir(s1, m1), m2
    resta = s2 < 0
    terminos = []
    for k in range(n + 1):
        piezas = []
        c = comb(n, k)
        if c != 1:
            piezas.append(ENum(Fraction(c)))
        if n - k >= 1:
            piezas.append(A if n - k == 1 else EPot(A, n - k))
        if k >= 1:
            piezas.append(B if k == 1 else EPot(B, k))
        t = piezas[0] if len(piezas) == 1 else EProd(tuple(piezas))
        terminos.append(neg(t) if (resta and k % 2 == 1) else t)
    fila = ", ".join(str(comb(n, k)) for k in range(n + 1))
    formula = f"(a {'−' if resta else '+'} b)^{n} se desarrolla con el binomio de Newton"
    explica = (f"Se desarrolla con el binomio de Newton. Los coeficientes salen del triángulo de "
               f"Pascal: {fila}. Los exponentes del primero bajan de {n} a 0 y los del segundo suben de 0 a {n}"
               f"{', y los signos se alternan' if resta else ''}.")
    return ("un binomio elevado a una potencia", formula, explica, A, B, ESum(tuple(terminos)),
            f"a = {txt(A)} y b = {txt(B)}")


def _trinomio_al_cuadrado(base: ESum):
    a, b, c = [_fir(s, m) for s, m in _firmados(base)]
    valores = ESum((EPot(a, 2), EPot(b, 2), EPot(c, 2), EProd((ENum(Fraction(2)), a, b)),
                    EProd((ENum(Fraction(2)), a, c)), EProd((ENum(Fraction(2)), b, c))))
    explica = ("El resultado es el cuadrado de cada término, más el doble de cada producto de dos términos "
               "distintos.")
    return ("el cuadrado de un trinomio", "(a + b + c)² = a² + b² + c² + 2ab + 2ac + 2bc", explica, a, b, valores,
            f"a = {txt(a)}, b = {txt(b)} y c = {txt(c)}")


def _suma_por_diferencia(f1: ESum, f2: ESum):
    t1, t2 = _firmados(f1), _firmados(f2)
    for i in (0, 1):
        for j in (0, 1):
            a1, a2 = _fir(*t1[i]), _fir(*t2[j])
            b1, b2 = _fir(*t1[1 - i]), _fir(*t2[1 - j])
            if _igual(a1, a2) and _opuestos(b1, b2):
                B = t1[1 - i][1]
                valores = ESum((EPot(a1, 2), neg(EPot(B, 2))))
                explica = ("Los dos paréntesis tienen los mismos términos, pero uno suma el segundo y el otro lo resta. "
                           "El resultado es el cuadrado del primero menos el cuadrado del segundo.")
                return ("la suma por la diferencia", "(a + b)(a − b) = a² − b²", explica, a1, B, valores,
                        f"a = {txt(a1)} y b = {txt(B)}")
    return None


def _termino_comun(f1: ESum, f2: ESum):
    t1, t2 = _firmados(f1), _firmados(f2)
    for i in (0, 1):
        for j in (0, 1):
            x1, x2 = _fir(*t1[i]), _fir(*t2[j])
            if _igual(x1, x2) and _letras(x1):
                a, b = _fir(*t1[1 - i]), _fir(*t2[1 - j])
                valores = ESum((EPot(x1, 2), EProd((ESum((a, b)), x1)), EProd((a, b))))
                explica = ("Los dos paréntesis tienen un término común. El resultado es el cuadrado del término común, más "
                           "la suma de los términos distintos por el común, más el producto de los términos distintos.")
                return ("el producto de binomios con un término común", "(x + a)(x + b) = x² + (a + b)x + ab",
                        explica, x1, ESum((a, b)), valores,
                        f"el término común es {txt(x1)}, a = {txt(a)} y b = {txt(b)}")
    return None


# ---------------------------------------------------------------------------
# Distribuir sin reducir
# ---------------------------------------------------------------------------

def _hay_producto(e: E) -> bool:
    if isinstance(e, EProd):
        suma = any(isinstance(f, ESum) or (isinstance(f, EPot) and isinstance(f.base, ESum)) for f in e.factores)
        return (suma and len(e.factores) >= 2) or any(_hay_producto(f) for f in e.factores)
    if isinstance(e, EPot):
        return isinstance(e.base, ESum) or _hay_producto(e.base)
    if isinstance(e, ESum):
        return any(_hay_producto(t) for t in e.terminos)
    if isinstance(e, ENeg):
        return _hay_producto(e.x)
    return False


def _hay_signos(e: E) -> bool:
    if isinstance(e, ENeg):
        return isinstance(e.x, ESum) or _hay_signos(e.x)
    if isinstance(e, ESum):
        return any(isinstance(t, ESum) or _hay_signos(t) for t in e.terminos)
    if isinstance(e, EProd):
        return any(_hay_signos(f) for f in e.factores)
    if isinstance(e, EPot):
        return _hay_signos(e.base)
    return False


def _terminos_dist(e: E) -> list:
    """Cada término que resulta de quitar paréntesis y distribuir, como (signo, término), SIN reducir."""
    if isinstance(e, ESum):
        return [x for t in e.terminos for x in _terminos_dist(t)]
    if isinstance(e, ENeg):
        return [(-s, t) for s, t in _terminos_dist(e.x)]
    if isinstance(e, EPot) and isinstance(e.base, ESum):
        return _terminos_dist(EProd(tuple([e.base] * e.exp)))
    if isinstance(e, EProd):
        combos = [(1, [])]
        for f in e.factores:
            tf = _terminos_dist(f)
            nuevo = []
            for s1, p1 in combos:
                for s2, t2 in tf:
                    pieza = list(t2.factores) if isinstance(t2, EProd) else [t2]
                    nuevo.append((s1 * s2, p1 + pieza))
            combos = nuevo
            if len(combos) > 400:
                raise ErrorMatematico("La expresión es demasiado grande para mostrarla paso a paso: prueba con exponentes o "
                                      "paréntesis más pequeños.")
        salida = []
        for s, piezas in combos:
            utiles = [p for p in piezas if not (isinstance(p, ENum) and p.v == 1)] or [ENum(Fraction(1))]
            salida.append((s, utiles[0] if len(utiles) == 1 else EProd(tuple(utiles))))
        return salida
    return [(1, e)]


def _distribuida(e: E) -> E:
    return ESum(tuple(t if s > 0 else neg(t) for s, t in _terminos_dist(e)))


# ---------------------------------------------------------------------------
# Resolver
# ---------------------------------------------------------------------------

def resolver_polinomio(texto: str, entrada: str | None = None) -> Solucion:
    """Desarrolla y reduce un polinomio (o un producto notable) explicando cada paso."""
    sp = _sp()
    arbol, e0, orden = leer(texto)
    if _con_division_por_letras(e0) or _con_radicales(e0):
        raise ErrorMatematico("Por ahora desarrollo y reduzco polinomios: sin letras en un denominador ni dentro de "
                              "una raíz. Para fracciones con letras escribe «simplificar …».")
    canon = desde_sympy(sp.expand(a_sympy(e0, {})), orden)
    libreta = Libreta(_MOTIVO)
    nota = ""

    nb = _notable(e0)
    if nb:
        nombre, formula, explica, A, B, valores, etiqueta = nb
        libreta.agregar(
            "producto_notable",
            f"Esto es un producto notable: {nombre}. {explica} Aquí {etiqueta}: ponemos esos valores en la "
            f"fórmula.",
            valores, operacion=txt(A), previo=(formula, formula.replace("²", "^{2}").replace("³", "^{3}")))
        if txt(valores) != txt(canon):
            libreta.agregar("reducir", "Hacemos las operaciones (potencias y productos), juntamos los términos "
                                       f"semejantes y ordenamos de mayor a menor grado: {txt(valores)} = {txt(canon)}.",
                            canon, operacion=txt(valores))
        nota = f"Fórmula usada: {formula}."
    else:
        actual = e0
        if _hay_producto(e0) or _hay_signos(e0):
            dist = _distribuida(e0)
            if _hay_producto(e0):
                msg = ("Aplicamos la propiedad distributiva: multiplicamos cada término de un paréntesis por cada "
                       "término del otro, y quitamos los paréntesis.")
                regla = "distribuir"
            else:
                msg = ("Quitamos los paréntesis: con un signo + delante los términos no cambian; con un signo − "
                       "delante, cambian todos de signo.")
                regla = "quitar_parentesis"
            libreta.agregar(regla, f"{msg} {txt(e0)} = {txt(dist)}.", dist, operacion=txt(e0))
            actual = dist
        if txt(actual) != txt(canon):
            libreta.agregar("reducir", "Juntamos los términos semejantes (sumamos sus coeficientes) y ordenamos de "
                                       f"mayor a menor grado: {txt(actual)} = {txt(canon)}.", canon, operacion=txt(actual))
        if not libreta.pasos:
            libreta.agregar("ya_reducida", "Ya está reducida: no hay paréntesis ni términos semejantes que juntar.",
                            canon)
    verificar(arbol, canon)
    return solucion("polinomio", entrada or texto, e0, libreta, canon, nota=nota)


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


def _con_division_por_letras(e: E) -> bool:
    if isinstance(e, EFrac) and _letras(e.den):
        return True
    return any(_con_division_por_letras(h) for h in _hijos(e))


def _con_radicales(e: E) -> bool:
    if isinstance(e, ERad):
        return True
    return any(_con_radicales(h) for h in _hijos(e))
