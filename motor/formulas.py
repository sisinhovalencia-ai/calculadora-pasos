"""Despejar una letra de una fórmula, paso a paso.

    despejar t en v = d/t            →  t = d/v
    despejar h en A = b·h/2          →  h = 2A/b
    despejar w en P = 2l + 2w        →  w = (P − 2l)/2
    despejar C en F = 9C/5 + 32      →  C = (5F − 160)/9
    v = d/t, despejar d              (el orden da igual; también «despejar d: v = d/t»)

Las demás letras se tratan como números que no conocemos (como si fueran constantes). La letra
a despejar tiene que ser de primer grado (después de quitar los denominadores). Se aceptan
letras pegadas (`ma` = m·a) y la constante π.

El álgebra la hace SymPy; los pasos se escriben como en el cuaderno:
  1. propiedad distributiva (sobre lo que escribió el estudiante, sin juntar términos);
  2. quitar denominadores multiplicando los dos lados;
  3. juntar en un lado los términos que tienen la letra y pasar los demás al otro;
  4. sacar la letra como factor común y dividir entre su coeficiente;
  5. simplificar la fracción, y leer al revés si la letra quedó a la derecha.
Cada operación se muestra escrita en los DOS lados antes de simplificarla.
Al final se COMPRUEBA con otro camino: se reemplaza la respuesta en la fórmula original y se
compara con lo que da el resolvedor de SymPy. Si algo no cuadrara, el motor lo detecta en vez
de mostrarlo. SymPy solo se carga cuando se despeja una fórmula (no al arrancar la app).
"""

import re
from fractions import Fraction

from .arbol import BinOp, Cociente, Frac, Mixto, Neg, Nodo, Num, Paren, Porc, Raiz, Var, con_hijos, hijos, normalizar
from .aritmetica import _calcular_raiz
from .ecuaciones import _NO_SOPORTADO, _distribuir, _incognitas, _separar
from .errores import ErrorDeEntrada, ErrorMatematico, ErrorMotor
from .numeros import MENOS
from .parser import parsear
from .pasos import Paso, Solucion
from .render import a_latex, a_texto

_MOTIVO = {
    "distribuir": "El factor de afuera multiplica a TODO lo que está dentro del paréntesis, no solo al primer término.",
    "simplificar": "Antes de despejar conviene dejar cada lado lo más sencillo posible.",
    "quitar_denominadores": "Multiplicar los dos lados por lo que divide quita las fracciones; así la letra no queda "
                            "atrapada en un denominador y todo se vuelve más fácil de mover.",
    "mover_letra": "Para despejar una letra hay que dejarla sola. Primero se juntan, en un solo lado, todos los "
                   "términos que la tienen. Lo que se hace a un lado se hace al otro, y la igualdad se mantiene.",
    "mover_resto": "Los términos que no tienen la letra se pasan al otro lado con la operación contraria "
                   "(y se hace también en el otro lado).",
    "factor_comun": "Si la letra aparece en varios términos, se saca como factor común para que quede multiplicada "
                    "una sola vez; así se puede dividir entre todo su coeficiente de una vez.",
    "despejar": "La letra está multiplicada por una expresión; la operación contraria es dividir entre esa "
                "expresión, y se hace en los dos lados.",
    "aislar_potencia": "Primero dejamos sola la potencia de la letra; así podemos aplicar la operación inversa.",
    "extraer_raiz": "La operación inversa de elevar a una potencia par es sacar la raíz correspondiente. Una potencia "
                    "par puede venir de una base positiva o negativa, por eso aparecen las dos ramas.",
    "simplificar_final": "Si el numerador y el denominador tienen algo en común, se puede simplificar; así la "
                         "respuesta queda lo más sencilla posible.",
    "intercambiar": "Leer una igualdad al revés no la cambia: si X = t, entonces t = X.",
    "comprobar": "Reemplazar la respuesta en la fórmula original comprueba que no nos equivocamos.",
}


def _sp():
    import sympy
    return sympy


# ---------------------------------------------------------------------------
# Del árbol a SymPy
# ---------------------------------------------------------------------------

def _a_sympy(n: Nodo, S: dict):
    sp = _sp()
    if isinstance(n, Num):
        return sp.Rational(n.valor.numerator, n.valor.denominator)
    if isinstance(n, Frac):
        return sp.Rational(n.num, n.den)
    if isinstance(n, Porc):
        return sp.Rational(n.valor.numerator, n.valor.denominator) / 100
    if isinstance(n, Mixto):
        if n.den == 0:
            raise ErrorMatematico("No se puede dividir entre cero.")
        return n.ent + sp.Rational(n.num, n.den)
    if isinstance(n, Var):
        if n.nombre == "π":
            return sp.pi
        return S.setdefault(n.nombre, sp.Symbol(n.nombre))
    if isinstance(n, Neg):
        return -_a_sympy(n.hijo, S)
    if isinstance(n, (Paren,)):
        return _a_sympy(n.hijo, S)
    if isinstance(n, Raiz):
        x = _a_sympy(n.hijo, S)
        if x.free_symbols:
            raise ErrorMatematico(_NO_SOPORTADO)
        f = _calcular_raiz(n.indice, Fraction(int(x.p), int(x.q)))
        return sp.Rational(f.numerator, f.denominator)
    if isinstance(n, Cociente):
        return _a_sympy(n.num, S) / _a_sympy(n.den, S)
    izq, der = _a_sympy(n.izq, S), _a_sympy(n.der, S)
    if n.op == "+":
        return izq + der
    if n.op == "-":
        return izq - der
    if n.op == "*":
        return izq * der
    if n.op == "/":
        if der == 0:
            raise ErrorMatematico("No se puede dividir entre cero.")
        return izq / der
    if n.op == "^":
        if not der.is_Integer:
            raise ErrorMatematico("Por ahora solo despejo con potencias de exponente entero.")
        if abs(der) > 20:
            raise ErrorMatematico("Al despejar fórmulas el exponente máximo es 20.")
        if izq == 0 and der <= 0:
            raise ErrorMatematico("0 elevado a un exponente que no es positivo no está definido.")
        return izq ** der
    raise ErrorMotor(f"Operador desconocido: {n.op}")  # pragma: no cover


def _a_cocientes(n: Nodo) -> Nodo:
    """Solo para DIBUJAR: cada división con letras se escribe como fracción (d/t)."""
    hs = [_a_cocientes(h) for h in hijos(n)]
    nuevo = con_hijos(n, hs) if hs else n
    if isinstance(nuevo, BinOp) and nuevo.op == "/" and _incognitas(nuevo, set()):
        return Cociente(nuevo.izq, nuevo.der)
    return nuevo


# ---------------------------------------------------------------------------
# Dibujo de expresiones de SymPy (texto plano que nuestro parser vuelve a leer, y LaTeX)
# ---------------------------------------------------------------------------

class _Fr:
    """Una fracción que se muestra tal cual (numerador/denominador), sin que SymPy la reparta."""
    __slots__ = ("num", "den")

    def __init__(self, num, den):
        self.num, self.den = num, den

    def valor(self):
        return self.num / self.den


_ORDEN: dict = {}      # letra -> posición en la que aparece en lo que escribió el estudiante


def _pos(e) -> tuple:
    return tuple(sorted(_ORDEN.get(str(s), 99) for s in e.free_symbols))


def _clave(t):
    """Orden de los términos de una suma: primero los positivos (u − f, 3 − y), las letras antes que los
    números sueltos, y las letras en el orden en que las escribió el estudiante."""
    negativo = 1 if t.as_coeff_Mul()[0] < 0 else 0
    return (negativo, 0 if t.free_symbols else 1, _pos(t), str(t))


def _atomo(txt: str) -> bool:
    """Una letra o un número solos (con exponente). '2π' NO es un átomo: C/2π se leería (C/2)·π."""
    return re.fullmatch(r"(?:[A-Za-zπ]|\d+)(?:\^\d+)?", txt) is not None


def _par(txt: str) -> str:
    return txt if _atomo(txt) else f"({txt})"


def _fmt(e) -> tuple[str, str]:
    """(texto, latex) de una expresión de SymPy o de una `_Fr`."""
    sp = _sp()
    if isinstance(e, _Fr):
        nt, nl = _fmt(e.num)
        dt, dl = _fmt(e.den)
        nt = f"({nt})" if e.num.is_Add else nt
        dt = f"({dt})" if (e.den.is_Add or e.den.is_Mul or e.den.is_Pow or e.den.could_extract_minus_sign()) else dt
        return f"{nt}/{dt}", f"\\frac{{{nl}}}{{{dl}}}"
    if e == sp.pi:
        return "π", "\\pi"
    if e.is_Integer:
        v = int(e)
        return (f"{MENOS}{abs(v)}" if v < 0 else str(v)), str(v)
    if e.is_Rational:
        p, q = int(e.p), int(e.q)
        return (f"{MENOS if p < 0 else ''}{abs(p)}/{q}", f"{'-' if p < 0 else ''}\\frac{{{abs(p)}}}{{{q}}}")
    if e.is_Symbol:
        return str(e), str(e)
    if e.is_Add:
        terminos = sorted(sp.Add.make_args(e), key=_clave)
        # una sola fracción cuando todos los términos comparten el mismo denominador numérico
        coefs = [t.as_coeff_Mul()[0] for t in terminos]
        dens = {int(c.q) for c in coefs}
        if len(dens) == 1 and next(iter(dens)) > 1 and all(sp.fraction(t.as_coeff_Mul()[1])[1] == 1 for t in terminos):
            q = next(iter(dens))
            num = sp.Add(*[t * q for t in terminos])
            nt, nl = _fmt(num)
            return f"({nt})/{q}", f"\\frac{{{nl}}}{{{q}}}"
        txt, tex = "", ""
        for i, t in enumerate(terminos):
            negativo = t.as_coeff_Mul()[0] < 0
            tt, tl = _fmt(-t if negativo else t)
            if i == 0:
                txt, tex = (MENOS + tt, "-" + tl) if negativo else (tt, tl)
            else:
                txt += (f" {MENOS} " if negativo else " + ") + tt
                tex += (" - " if negativo else " + ") + tl
        return txt, tex
    if e.is_Mul:
        if e.could_extract_minus_sign():
            tt, tl = _fmt(-e)
            return MENOS + tt, "-" + tl
        n, d = sp.fraction(e)
        if d != 1:
            return _fmt(_Fr(n, d))
        coef, resto = e.as_coeff_Mul()
        factores = sorted(sp.Mul.make_args(resto), key=lambda f: (_pos(f), str(f)))
        piezas = [_fmt_factor(f) for f in factores]
        txt = "·".join(p[0] for p in piezas)
        tex = " \\cdot ".join(p[1] for p in piezas)
        if coef != 1:
            return str(int(coef)) + txt, str(int(coef)) + tex
        return txt, tex
    if e.is_Pow:
        n, d = sp.fraction(e)
        if d != 1:
            return _fmt(_Fr(n, d))
        base, exp = e.as_base_exp()
        if exp.is_Rational and int(exp.q) > 1 and int(exp.p) == 1:
            indice = int(exp.q)
            bt, bl = _fmt(base)
            if base.is_Add or base.is_Mul:
                bt, bl = f"({bt})", f"\\left({bl}\\right)"
            signo = "√" if indice == 2 else ("∛" if indice == 3 else f"raiz{indice}")
            tex = f"\\sqrt{{{bl}}}" if indice == 2 else f"\\sqrt[{indice}]{{{bl}}}"
            return f"{signo}({bt})", tex
        return _fmt_factor(e)
    raise ErrorMotor(f"No sé dibujar {e!r}")  # pragma: no cover


def _fmt_factor(f) -> tuple[str, str]:
    sp = _sp()
    if f.is_Pow:
        base, exp = f.as_base_exp()
        if exp.is_Rational and int(exp.q) > 1:
            return _fmt(f)
        bt, bl = _fmt(base)
        if base.is_Add or base.is_Mul:
            bt, bl = f"({bt})", f"({bl})"
        return f"{bt}^{int(exp)}", f"{bl}^{{{int(exp)}}}"
    if f.is_Add:
        t, l = _fmt(f)
        return f"({t})", (f"\\left({l}\\right)" if "\\frac" in l else f"({l})")
    return _fmt(f)


def _simplificar_fraccion(num, den):
    """(numerador, denominador) simplificados, o None si no hay nada que simplificar.
    Simplifica un factor común (número o letras) y un denominador negativo."""
    sp = _sp()
    g = sp.gcd(sp.expand(num), sp.expand(den))
    n2, d2, cambio = num, den, False
    if g != 1 and g != 0:
        n2, d2, cambio = sp.expand(sp.cancel(num / g)), sp.expand(sp.cancel(den / g)), True
    if not d2.is_Add and d2.as_coeff_Mul()[0] < 0:        # denominador negativo: se pasa el signo arriba
        n2, d2, cambio = sp.expand(-n2), -d2, True
    return (n2, d2) if cambio else None


def _ec(L, R):
    lt, ll = _fmt(L)
    rt, rl = _fmt(R)
    return f"{lt} = {rt}", f"{ll} = {rl}"


def _signo_y_oper(m):
    """('restamos', 'sumamos'...) según el signo del término que se mueve: devuelve (verbo, signo, M positivo)."""
    if m.could_extract_minus_sign():
        return "sumamos", "+", -m
    return "restamos", "-", m


def _previo(L, R, signo, m):
    mt, ml = _fmt(m)
    if m.is_Add:
        mt, ml = f"({mt})", f"({ml})"
    s_t = "+" if signo == "+" else MENOS
    lt, ll = _fmt(L)
    rt, rl = _fmt(R)
    return (f"{lt} {s_t} {mt} = {rt} {s_t} {mt}", f"{ll} {signo} {ml} = {rl} {signo} {ml}")


def _previo_producto(L, R, D):
    lt, ll = _fmt(L)
    rt, rl = _fmt(R)
    dt, dl = _fmt(D)
    def pl(e, t):                                  # paréntesis solo si hacen falta; altos si hay una fracción
        if e.is_Symbol:
            return t
        return f"\\left({t}\\right)" if "\\frac" in t else f"({t})"
    return (f"{_par(lt)}·{_par(dt)} = {_par(rt)}·{_par(dt)}",
            f"{pl(L, ll)} \\cdot {dl} = {pl(R, rl)} \\cdot {dl}")


def _previo_division(L, R, c):
    lt, ll = _fmt(L)
    rt, rl = _fmt(R)
    ct, cl = _fmt(c)
    return (f"{_par(lt)}/{_par(ct)} = {_par(rt)}/{_par(ct)}", f"\\frac{{{ll}}}{{{cl}}} = \\frac{{{rl}}}{{{cl}}}")


def _atomos(txt: str):
    letras = re.findall(r"[A-Za-zπ]", txt)
    todos = re.findall(r"[A-Za-zπ]|\d+(?:\.\d+)?", txt)
    return len(letras), len(todos)


# ---------------------------------------------------------------------------
# Resolver
# ---------------------------------------------------------------------------

def resolver_formula(texto: str) -> Solucion:
    """Despeja una letra de una fórmula y explica cada paso."""
    sp = _sp()
    if texto is None or not texto.strip():
        raise ErrorDeEntrada("Escribe la fórmula y la letra a despejar, por ejemplo: despejar t en v = d/t")
    m = re.search(r"\bdespejar\s+([A-Za-z])(?![A-Za-z])", texto, re.IGNORECASE)
    if not m:
        raise ErrorDeEntrada("Indica qué letra despejar, por ejemplo: despejar t en v = d/t")
    T_nombre = m.group(1)
    resto = (texto[:m.start()] + " " + texto[m.end():]).strip()
    resto = re.sub(r"^(?:\s|[:,;]|(?:en|de)\b)+", "", resto, flags=re.IGNORECASE)
    resto = re.sub(r"(?:\s|[:,;])+$", "", resto)
    if not resto:
        raise ErrorDeEntrada("Falta la fórmula: escribe, por ejemplo, despejar t en v = d/t")
    rel, izq_t, der_t = _separar(resto)
    if rel != "=":
        raise ErrorDeEntrada("Para despejar una letra usa una igualdad (=), por ejemplo: despejar t en v = d/t")
    if not izq_t.strip() or not der_t.strip():
        raise ErrorDeEntrada("Falta un lado de la fórmula: escribe algo a cada lado del signo =.")

    (arbol_i, _), (arbol_d, _) = parsear(izq_t, variables=True), parsear(der_t, variables=True)
    nI, nD = normalizar(arbol_i), normalizar(arbol_d)
    letras = _incognitas(nD, _incognitas(nI, set())) - {"π"}
    if T_nombre not in letras:
        raise ErrorDeEntrada(f"La letra {T_nombre} no aparece en la fórmula (las letras son: "
                             f"{', '.join(sorted(letras)) or 'ninguna'}).")
    if len(letras) == 1:                  # las lineales van al solucionador de ecuaciones habitual
        unica: dict = {}
        simbolo = unica.setdefault(T_nombre, sp.Symbol(T_nombre))
        polinomio = sp.Poly(sp.expand(_a_sympy(nI, unica) - _a_sympy(nD, unica)), simbolo)
        if polinomio.degree() <= 1:
            from .ecuaciones import resolver_ecuacion
            return resolver_ecuacion(resto)

    _ORDEN.clear()
    for ch in resto:
        if ch.isalpha() and ch != "π" and ch not in _ORDEN:
            _ORDEN[ch] = len(_ORDEN)
    S: dict = {}
    T = S.setdefault(T_nombre, sp.Symbol(T_nombre))
    pasos: list[Paso] = []
    supuestos: list = []

    def agregar(regla, explicacion, operacion="", ec=None, previo=None):
        txt, tex = ec
        pasos.append(Paso(
            numero=len(pasos) + 1, regla=regla, explicacion=explicacion, motivo=_MOTIVO[regla],
            operacion=operacion, resultado_parcial="", expresion=txt, latex=tex,
            intermedio=previo[0] if previo else "", latex_intermedio=previo[1] if previo else ""))

    # 1. Propiedad distributiva sobre lo escrito (sin juntar términos)
    dI, hI = _distribuir(nI, True)
    dD, hD = _distribuir(nD, True)
    tI0, tD0 = a_texto(_a_cocientes(nI)), a_texto(_a_cocientes(nD))
    if hI or hD:
        cambios = []
        if hI:
            cambios.append(f"En el lado izquierdo: {tI0} = {a_texto(_a_cocientes(dI))}.")
        if hD:
            cambios.append(f"En el lado derecho: {tD0} = {a_texto(_a_cocientes(dD))}.")
        ec = (f"{a_texto(_a_cocientes(dI))} = {a_texto(_a_cocientes(dD))}",
              f"{a_latex(_a_cocientes(dI))} = {a_latex(_a_cocientes(dD))}")
        agregar("distribuir", "Aplicamos la propiedad distributiva: multiplicamos el factor de afuera por cada "
                              "término que está dentro del paréntesis. " + " ".join(cambios),
                operacion=tI0 if hI else tD0, ec=ec)
    tI1 = a_texto(_a_cocientes(dI))
    tD1 = a_texto(_a_cocientes(dD))

    L0 = _a_sympy(dI, S)
    R0 = _a_sympy(dD, S)
    L, R = L0, R0

    # 2. Simplificar si realmente se puede (menos letras o menos números)
    cambios, primero_antes = [], ""
    for nombre, antes, ahora in (("izquierdo", tI1, _fmt(L)[0]), ("derecho", tD1, _fmt(R)[0])):
        la, ta = _atomos(antes)
        lb, tb = _atomos(ahora)
        if lb < la or tb < ta:
            cambios.append(f"En el lado {nombre}: {antes} = {ahora}.")
            primero_antes = primero_antes or antes
    if cambios:
        agregar("simplificar", "Simplificamos cada lado: hacemos las operaciones que se pueden y juntamos los "
                               "términos parecidos. " + " ".join(cambios), operacion=primero_antes, ec=_ec(L, R))

    ya_despejada = (L == T and T not in R.free_symbols) or (R == T and T not in L.free_symbols)

    # 3. Quitar denominadores (multiplicando los dos lados por su mínimo común múltiplo)
    dL = sp.fraction(sp.together(L))[1]
    dR = sp.fraction(sp.together(R))[1]
    D = sp.lcm(dL, dR)
    if D != 1 and not ya_despejada:
        dt, dl = _fmt(D)
        frase = f"multiplicamos ambos lados por {dt}"
        previo = _previo_producto(L, R, D)
        L2 = sp.expand(sp.cancel(sp.together(L * D)))
        R2 = sp.expand(sp.cancel(sp.together(R * D)))
        if D.free_symbols:
            supuestos.append(D)
        L, R = L2, R2
        agregar("quitar_denominadores",
                f"Para quitar los denominadores, {frase}: así las fracciones desaparecen.", operacion=frase,
                ec=_ec(L, R), previo=previo)
    L, R = sp.expand(L), sp.expand(R)

    if ya_despejada:
        lado, solucion = ("izq", R) if L == T else ("der", L)
        return _final(texto, T_nombre, T, nI, nD, L0, R0, L, R, lado, solucion, pasos, supuestos, agregar)

    # 4. La letra debe ser de primer grado
    P = sp.Poly(sp.expand(L - R), T)
    if P.degree() > 1:
        # Potencia pura: a·T^n + c = 0. Es el patrón de fórmulas como A = πr²
        # y Ec = ½mv², y permite explicar el despeje sin esconder pasos en solve().
        terminos = [(mon, c) for mon, c in P.terms() if c != 0]
        grado = P.degree()
        if (grado == 2 and len(terminos) == 2
                and any(mon == (grado,) for mon, _ in terminos)
                and any(mon == (0,) for mon, _ in terminos)):
            coef = P.coeff_monomial(T ** grado)
            constante = P.coeff_monomial(1)
            derecha = sp.cancel(-constante / coef)
            raiz = sp.sqrt(derecha)
            # Para grado par, la igualdad tiene dos ramas reales (si el radicando no es negativo).
            dos = grado % 2 == 0
            positivo = sp.simplify(raiz)
            soluciones = [positivo, -positivo] if dos else [positivo]
            if sp.ask(sp.Q.negative(derecha)):
                raise ErrorMatematico("No hay soluciones reales: el valor bajo la raíz es negativo.")

            exp_pot = _fmt(T ** grado)
            rhs = _fmt(derecha)
            agregar("aislar_potencia", f"Reunimos los términos y aislamos la potencia: {T_nombre}^{grado} = "
                                      f"{rhs[0]}.", operacion=f"{T_nombre}^{grado}",
                    ec=(f"{T_nombre}^{grado} = {rhs[0]}", f"{T_nombre}^{{{grado}}} = {rhs[1]}"))
            rt, rtl = f"√({rhs[0]})", f"\\sqrt{{{rhs[1]}}}"
            signo = "±" if dos else ""
            signo_tex = "\\pm " if dos else ""
            result_txt, result_tex = f"{T_nombre} = {signo}{rt}", f"{T_nombre} = {signo_tex}{rtl}"
            condicion = " Si se buscan soluciones reales, el valor bajo la raíz debe ser mayor o igual que 0." if dos else ""
            agregar("extraer_raiz", f"Aplicamos la raíz de índice {grado} a ambos lados.{condicion} "
                                    f"Como el exponente es par, consideramos las dos posibilidades: positiva y negativa."
                                    if dos else f"Aplicamos la raíz de índice {grado} a ambos lados.",
                    operacion=f"raíz {grado}", ec=(result_txt, result_tex))
            # Verificación independiente en la fórmula de partida para todas las ramas.
            for raiz_sol in soluciones:
                if sp.simplify((L0 - R0).subs(T, raiz_sol)) != 0:
                    raise ErrorMotor("La comprobación de la potencia falló.")
            oficial = sp.solve(L0 - R0, T)
            if len(oficial) != len(soluciones) or any(not any(sp.simplify(x - y) == 0 for y in oficial)
                                                       for x in soluciones):
                raise ErrorMotor(f"La comprobación falló: SymPy da {oficial} y aquí salió {soluciones}")
            st, sl = result_txt.split(" = ", 1)[1], result_tex.split(" = ", 1)[1]
            ec_orig = f"{a_texto(_a_cocientes(nI))} = {a_texto(_a_cocientes(nD))}"
            agregar("comprobar", f"Comprobamos sustituyendo las soluciones en la fórmula original: ambas ramas "
                                  "hacen iguales los dos lados. El despeje es correcto.", operacion=st,
                    ec=(result_txt, result_tex))
            supuestos.append(coef)
            coef_txt = _fmt(-coef if coef.could_extract_minus_sign() else coef)[0]
            nota = (f"Se supone que {coef_txt} no vale 0. "
                    if coef.free_symbols else "") + ("Se muestran las dos soluciones reales; para que existan, "
                    "el radicando debe ser mayor o igual que 0." if dos else "")
            inicial_t = f"{a_texto(_a_cocientes(nI))} = {a_texto(_a_cocientes(nD))}"
            return Solucion(tipo="formula", entrada=texto,
                            expresion_inicial=f"despejar {T_nombre} en {inicial_t}",
                            latex_inicial=f"{a_latex(_a_cocientes(nI))} = {a_latex(_a_cocientes(nD))}",
                            pasos=pasos, resultado=result_txt, resultado_latex=result_tex, nota=nota)
        raise ErrorMatematico(f"La letra {T_nombre} aparece en una potencia que no puedo aislar paso a paso todavía.")
    if P.degree() < 1 or sp.cancel(P.coeff_monomial(T)) == 0:
        raise ErrorMatematico(f"La letra {T_nombre} se cancela: no se puede despejar.")

    iL, dLt = L.as_independent(T, as_Add=True)
    iR, dRt = R.as_independent(T, as_Add=True)

    # 5. Juntar los términos con la letra en un lado y los demás en el otro
    if dLt != 0 and dRt != 0:
        verbo, signo, m = _signo_y_oper(dRt)
        mt = _fmt(m)[0]
        frase = f"{verbo} {mt} en ambos lados"
        previo = _previo(L, R, signo, m)
        L, R = sp.expand(L - dRt), sp.expand(R - dRt)
        agregar("mover_letra", f"Para juntar los términos con {T_nombre} en el lado izquierdo, {frase}. "
                               f"A la derecha desaparecen.", operacion=frase, ec=_ec(L, R), previo=previo)
        lado = "izq"
    else:
        lado = "izq" if dLt != 0 else "der"
    iL, dLt = L.as_independent(T, as_Add=True)
    iR, dRt = R.as_independent(T, as_Add=True)
    if lado == "izq" and iL != 0:
        verbo, signo, m = _signo_y_oper(iL)
        mt = _fmt(m)[0]
        frase = f"{verbo} {mt} en ambos lados"
        previo = _previo(L, R, signo, m)
        L, R = sp.expand(L - iL), sp.expand(R - iL)
        agregar("mover_resto", f"Para dejar solo los términos con {T_nombre} a la izquierda, {frase}. A la izquierda "
                               f"se cancela lo que no tiene {T_nombre}.", operacion=frase, ec=_ec(L, R), previo=previo)
    elif lado == "der" and iR != 0:
        verbo, signo, m = _signo_y_oper(iR)
        mt = _fmt(m)[0]
        frase = f"{verbo} {mt} en ambos lados"
        previo = _previo(L, R, signo, m)
        L, R = sp.expand(L - iR), sp.expand(R - iR)
        agregar("mover_resto", f"Para dejar solo los términos con {T_nombre} a la derecha, {frase}. A la derecha "
                               f"se cancela lo que no tiene {T_nombre}.", operacion=frase, ec=_ec(L, R), previo=previo)

    # 6. Factor común y coeficiente
    lado_T = L if lado == "izq" else R
    otro = R if lado == "izq" else L
    coef = sp.Poly(lado_T, T).coeff_monomial(T)
    if len(sp.Add.make_args(lado_T)) > 1:
        nuevo_lado = sp.Mul(coef, T, evaluate=False)
        ct = _fmt(coef)[0]
        if lado == "izq":
            L = nuevo_lado
        else:
            R = nuevo_lado
        lado_T = nuevo_lado
        agregar("factor_comun", f"Como {T_nombre} aparece en varios términos, la sacamos como factor común: queda "
                                f"multiplicada por ({ct}).", operacion=ct, ec=_ec(L, R))

    # 7. Dividir entre el coeficiente
    if coef != 1:
        ct = _fmt(coef)[0]
        frase = f"dividimos ambos lados entre {ct}"
        previo = _previo_division(L, R, coef)
        if coef.free_symbols:
            supuestos.append(coef)
        if lado == "izq":
            R = _Fr(otro, coef)
            L = T
        else:
            L = _Fr(otro, coef)
            R = T
        agregar("despejar", f"La letra {T_nombre} está multiplicada por {ct}, así que {frase}: a la "
                            f"{'izquierda' if lado == 'izq' else 'derecha'} queda {T_nombre} sola.",
                operacion=frase, ec=_ec(L, R), previo=previo)
        # 8. Simplificar la fracción si se puede
        fr = R if lado == "izq" else L
        simple = _simplificar_fraccion(fr.num, fr.den)
        if simple is not None:
            n2, d2 = simple
            nuevo = n2 if d2 == 1 else _Fr(n2, d2)
            antes_t = _fmt(fr)[0]
            ahora_t = _fmt(nuevo)[0]
            if lado == "izq":
                R = nuevo
            else:
                L = nuevo
            agregar("simplificar_final", f"Simplificamos la fracción: {antes_t} = {ahora_t}.", operacion=antes_t,
                    ec=_ec(L, R))
    else:
        if lado == "izq":
            R = otro
        else:
            L = otro

    solucion = R if lado == "izq" else L
    return _final(texto, T_nombre, T, nI, nD, L0, R0, L, R, lado, solucion, pasos, supuestos, agregar)


def _final(texto, T_nombre, T, nI, nD, L0, R0, L, R, lado, solucion, pasos, supuestos, agregar) -> Solucion:
    """Leer al revés si hace falta, comprobar por otro camino y armar la solución."""
    sp = _sp()
    tI0, tD0 = a_texto(_a_cocientes(nI)), a_texto(_a_cocientes(nD))
    # 9. Si la letra quedó a la derecha, se lee al revés
    if lado == "der":
        st = _fmt(solucion)[0]
        frase = "leemos la igualdad al revés"
        antes = _ec(L, R)[0]
        L, R = T, solucion
        agregar("intercambiar", f"Tenemos {antes}, con {T_nombre} a la derecha: {frase}. Queda {T_nombre} = {st}.",
                operacion=frase, ec=_ec(L, R))

    # 10. Comprobación por otro camino: reemplazar en la fórmula original y comparar con el resolvedor de SymPy
    sol = solucion.valor() if isinstance(solucion, _Fr) else solucion
    izq_s = sp.cancel(sp.together(L0.subs(T, sol)))
    der_s = sp.cancel(sp.together(R0.subs(T, sol)))
    if sp.cancel(sp.together(izq_s - der_s)) != 0:  # pragma: no cover - sería un error del motor, nunca del estudiante
        raise ErrorMotor(f"La comprobación falló: {izq_s} no es igual a {der_s}")
    oficial = sp.solve(L0 - R0, T)
    if len(oficial) != 1 or sp.cancel(sp.together(oficial[0] - sol)) != 0:  # pragma: no cover
        raise ErrorMotor(f"La comprobación falló: SymPy da {oficial} y aquí salió {sol}")
    st, sl = _fmt(solucion)
    it, _il = _fmt(izq_s)
    dt, _dl = _fmt(der_s)
    if it == dt:
        cuerpo = f"los dos lados quedan iguales a {it}"
    else:
        cuerpo = f"izquierda: {it}; derecha: {dt}; son lo mismo"
    agregar("comprobar", f"Comprobamos reemplazando {T_nombre} por {st} en la fórmula original: {cuerpo}. "
                         f"El despeje es correcto.", operacion=st, ec=_ec(T, solucion))

    nota = ""
    if supuestos:
        distintos = list(dict.fromkeys(_fmt(x)[0] for x in supuestos))
        nota = (f"Se supone que {', '.join(distintos)} {'no vale' if len(distintos) == 1 else 'no valen'} 0, "
                f"porque no se puede dividir entre 0.")
    inicial_t = f"{tI0} = {tD0}"
    inicial_l = f"{a_latex(_a_cocientes(nI))} = {a_latex(_a_cocientes(nD))}"
    return Solucion(
        tipo="formula", entrada=texto, expresion_inicial=f"despejar {T_nombre} en {inicial_t}",
        latex_inicial=inicial_l, pasos=pasos, resultado=f"{T_nombre} = {st}",
        resultado_latex=f"{T_nombre} = {sl}", nota=nota)
