"""Ecuaciones cuadráticas de una incógnita, paso a paso.

El análisis y la comprobación usan expresiones exactas de SymPy, mientras que
la solución conserva el contrato común ``Solucion`` / ``Paso``. Si el
discriminante tiene raíz racional, se aprovecha el factorizador del proyecto.
"""

from fractions import Fraction
from math import isqrt

from .arbol import BinOp, Cociente, Frac, Mixto, Neg, Num, Paren, Porc, Raiz, Var
from .errores import ErrorDeEntrada, ErrorMatematico, ErrorMotor
from .numeros import formatear, formatear_latex
from .parser import parsear
from .pasos import Paso, Solucion


def _a_sympy(n, sp):
    """Convierte un nodo del parser a una expresión simbólica exacta."""
    if isinstance(n, Num):
        return sp.Rational(n.valor.numerator, n.valor.denominator)
    if isinstance(n, Frac):
        return sp.Rational(n.num, n.den)
    if isinstance(n, Mixto):
        return sp.Rational(n.ent * n.den + n.num, n.den)
    if isinstance(n, Porc):
        return sp.Rational(n.valor.numerator, n.valor.denominator * 100)
    if isinstance(n, Var):
        return sp.Symbol(n.nombre)
    if isinstance(n, (Paren,)):
        return _a_sympy(n.hijo, sp)
    if isinstance(n, Neg):
        return -_a_sympy(n.hijo, sp)
    if isinstance(n, Raiz):
        return sp.Pow(_a_sympy(n.hijo, sp), sp.Rational(1, n.indice))
    if isinstance(n, Cociente):
        return _a_sympy(n.num, sp) / _a_sympy(n.den, sp)
    if isinstance(n, BinOp):
        a, b = _a_sympy(n.izq, sp), _a_sympy(n.der, sp)
        return {"+": lambda: a + b, "-": lambda: a - b, "*": lambda: a * b,
                "/": lambda: a / b, "^": lambda: a ** b}[n.op]()
    raise ErrorMotor(f"Nodo no compatible con ecuaciones cuadráticas: {type(n).__name__}")  # pragma: no cover


def _incognitas(n, sp, encontradas=None):
    if encontradas is None:
        encontradas = set()
    if isinstance(n, Var):
        encontradas.add(n.nombre)
    if isinstance(n, (Paren, Neg, Raiz)):
        _incognitas(n.hijo, sp, encontradas)
    elif isinstance(n, (BinOp,)):
        _incognitas(n.izq, sp, encontradas)
        _incognitas(n.der, sp, encontradas)
    elif isinstance(n, Cociente):
        _incognitas(n.num, sp, encontradas)
        _incognitas(n.den, sp, encontradas)
    return encontradas


def _analizar(texto: str):
    """Retorna (variable, coeficientes, expresión original y SymPy) si es cuadrática."""
    from .ecuaciones import _separar
    import sympy as sp

    if not texto or "=" not in texto:
        return None
    rel, izq_t, der_t = _separar(texto)
    if rel != "=":
        return None
    if not izq_t.strip() or not der_t.strip():
        raise ErrorDeEntrada("Falta un lado de la ecuación: escribe una expresión a cada lado del signo =.")
    n_izq, _ = parsear(izq_t, variables=True)
    n_der, _ = parsear(der_t, variables=True)
    letras = _incognitas(n_izq, sp) | _incognitas(n_der, sp)
    if len(letras) != 1:
        return None
    nombre = next(iter(letras))
    variable = sp.Symbol(nombre)
    diferencia = sp.expand(_a_sympy(n_izq, sp) - _a_sympy(n_der, sp))
    try:
        polinomio = sp.Poly(diferencia, variable)
    except sp.PolynomialError:
        return None
    if polinomio.degree() != 2:
        return None
    coef = {}
    for grado in range(3):
        valor = sp.cancel(polinomio.nth(grado))
        if not valor.is_Rational:
            return None
        coef[grado] = Fraction(int(valor.p), int(valor.q))
    return nombre, coef, n_izq, n_der, variable, sp


def es_cuadratica(texto: str) -> bool:
    """Indica si una igualdad válida se reduce a un polinomio cuadrático."""
    try:
        return _analizar(texto) is not None
    except ErrorMatematico:
        return False


def _polinomio_texto(coef: dict[int, Fraction], variable: str) -> str:
    partes = []
    for grado in (2, 1, 0):
        c = coef.get(grado, Fraction(0))
        if not c:
            continue
        magnitud = abs(c)
        if grado == 0:
            termino = formatear(magnitud)
        else:
            letra = variable if grado == 1 else f"{variable}²"
            termino = letra if magnitud == 1 else f"{formatear(magnitud)}{letra}"
        if not partes:
            partes.append(("− " if c < 0 else "") + termino)
        else:
            partes.append((" − " if c < 0 else " + ") + termino)
    return "".join(partes) or "0"


def _polinomio_latex(coef: dict[int, Fraction], variable: str) -> str:
    partes = []
    for grado in (2, 1, 0):
        c = coef.get(grado, Fraction(0))
        if not c:
            continue
        magnitud = abs(c)
        if grado == 0:
            termino = formatear_latex(magnitud)
        else:
            letra = variable if grado == 1 else f"{variable}^2"
            termino = letra if magnitud == 1 else f"{formatear_latex(magnitud)}{letra}"
        if not partes:
            partes.append(("-" if c < 0 else "") + termino)
        else:
            partes.append((" - " if c < 0 else " + ") + termino)
    return "".join(partes) or "0"


def _texto_raiz(valor, sp) -> str:
    return sp.sstr(sp.simplify(valor)).replace("**", "^ ")


def _latex_raiz(valor, sp) -> str:
    return sp.latex(sp.simplify(valor))


def _raiz_racional(valor: Fraction) -> Fraction | None:
    if valor < 0:
        return None
    n, d = isqrt(valor.numerator), isqrt(valor.denominator)
    if n * n == valor.numerator and d * d == valor.denominator:
        return Fraction(n, d)
    return None


def _factor_lineal(variable: str, raiz: Fraction) -> tuple[str, str]:
    signo = "+" if raiz < 0 else "−"
    magnitud = abs(raiz)
    return (f"{variable} {signo} {formatear(magnitud)}",
            f"{variable} {'+' if raiz < 0 else '-'} {formatear_latex(magnitud)}")


def _paso(numero: int, regla: str, explicacion: str, motivo: str, expresion: str, latex: str,
          operacion: str = "") -> Paso:
    return Paso(numero=numero, regla=regla, explicacion=explicacion, motivo=motivo,
                operacion=operacion, resultado_parcial="", expresion=expresion, latex=latex)


def resolver_cuadratica(texto: str) -> Solucion:
    """Resuelve ``ax² + bx + c = 0`` y ecuaciones equivalentes con una incógnita."""
    analisis = _analizar(texto)
    if analisis is None:
        raise ErrorDeEntrada("Escribe una ecuación cuadrática con una incógnita, por ejemplo x² − 5x + 6 = 0.")
    variable, coef, n_izq, n_der, x, sp = analisis
    a, b, c = coef[2], coef[1], coef[0]
    if a == 0:  # protegido por Poly.degree(), queda como resguardo
        raise ErrorDeEntrada("La ecuación no es de segundo grado.")

    pol_texto = _polinomio_texto(coef, variable)
    pol_latex = _polinomio_latex(coef, variable)
    ec_texto, ec_latex = f"{pol_texto} = 0", f"{pol_latex} = 0"
    pasos = [_paso(
        1, "normalizar",
        "Llevamos todos los términos al lado izquierdo, reducimos los semejantes y ordenamos por grado.",
        "Una ecuación cuadrática se reconoce cuando, después de simplificar, queda ax² + bx + c = 0.",
        ec_texto, ec_latex, texto,
    )]

    a_t, b_t, c_t = formatear(a), formatear(b), formatear(c)
    coef_texto = f"a = {a_t}, b = {b_t}, c = {c_t}"
    coef_latex = (f"a = {formatear_latex(a)},\\quad b = {formatear_latex(b)},"
                  f"\\quad c = {formatear_latex(c)}")
    pasos.append(_paso(
        2, "coeficientes", f"Identificamos los coeficientes: {coef_texto}.",
        "Los coeficientes se leen en la forma ax² + bx + c = 0 y se usan en el discriminante y la fórmula general.",
        coef_texto, coef_latex,
    ))

    discriminante = b * b - 4 * a * c
    delta_t = formatear(discriminante)
    delta_l = formatear_latex(discriminante)
    delta_expr_t = f"Δ = b² − 4ac = {delta_t}"
    delta_expr_l = f"\\Delta = b^2 - 4ac = {delta_l}"
    pasos.append(_paso(
        3, "discriminante", f"Calculamos el discriminante: Δ = b² − 4ac = {delta_t}.",
        "El signo de Δ indica cuántas soluciones reales tiene la ecuación.", delta_expr_t, delta_expr_l,
    ))

    original_izq, original_der = _a_sympy(n_izq, sp), _a_sympy(n_der, sp)
    if discriminante < 0:
        pasos.append(_paso(
            4, "sin_reales",
            f"Como Δ = {delta_t} < 0, la raíz cuadrada del discriminante no es real; la ecuación no tiene soluciones reales.",
            "En los números reales no existe la raíz cuadrada de un número negativo.",
            "Sin soluciones reales", r"\text{Sin soluciones reales}",
        ))
        return Solucion(tipo="ecuacion_cuadratica", entrada=texto,
                        expresion_inicial=texto.strip(), latex_inicial=ec_latex,
                        pasos=pasos, resultado="Sin soluciones reales",
                        resultado_latex=r"\text{Sin soluciones reales}",
                        nota="No hay raíces reales que sustituir en la ecuación.")

    raiz_delta = _raiz_racional(discriminante)
    if raiz_delta is not None:
        # Reutilizamos el factorizador didáctico existente para los trinomios racionales.
        from .factorizacion import resolver_factorizacion
        try:
            factorizacion = resolver_factorizacion(pol_texto)
        except ErrorMotor:
            factorizacion = None
        if factorizacion is not None:
            for p in factorizacion.pasos:
                pasos.append(_paso(
                    len(pasos) + 1, f"factor_{p.regla}", p.explicacion, p.motivo,
                    f"{p.expresion} = 0", f"{p.latex} = 0", p.operacion,
                ))

        r1 = Fraction(-b - raiz_delta, 2 * a)
        r2 = Fraction(-b + raiz_delta, 2 * a)
        fact_t = factorizacion.resultado if factorizacion is not None else f"{a_t}({variable} − {formatear(r1)})({variable} − {formatear(r2)})"
        fact_l = factorizacion.resultado_latex if factorizacion is not None else (
            f"{formatear_latex(a)}({variable} - {formatear_latex(r1)})({variable} - {formatear_latex(r2)})")
        if not factorizacion or not factorizacion.pasos:
            pasos.append(_paso(
                len(pasos) + 1, "factorizar", f"Escribimos el trinomio como producto: {fact_t} = 0.",
                "La factorización convierte el trinomio en un producto que vale cero.",
                f"{fact_t} = 0", f"{fact_l} = 0",
            ))
        if r1 == r2:
            factor_t, factor_l = _factor_lineal(variable, r1)
            pasos.append(_paso(
                len(pasos) + 1, "producto_cero",
                "El factor repetido debe ser cero, así que igualamos ese factor a cero.",
                "Un producto solo vale cero cuando al menos uno de sus factores vale cero.",
                f"{factor_t} = 0", f"{factor_l} = 0",
            ))
            raices = [sp.Rational(r1.numerator, r1.denominator)]
        else:
            factor1_t, factor1_l = _factor_lineal(variable, r1)
            factor2_t, factor2_l = _factor_lineal(variable, r2)
            pasos.append(_paso(
                len(pasos) + 1, "producto_cero",
                "Igualamos cada factor a cero y obtenemos dos ecuaciones sencillas.",
                "Si un producto vale cero, uno de sus factores debe valer cero.",
                f"{factor1_t} = 0  o  {factor2_t} = 0",
                f"{factor1_l} = 0\\quad\\text{{o}}\\quad {factor2_l} = 0",
            ))
            raices = [sp.Rational(r1.numerator, r1.denominator), sp.Rational(r2.numerator, r2.denominator)]
        doble = len(raices) == 1
        if doble:
            resultado = f"{variable} = {formatear(r1)} (raíz doble)"
            resultado_latex = f"{variable} = {formatear_latex(r1)}\\quad\\text{{(raíz doble)}}"
        else:
            resultado = f"{variable}₁ = {formatear(r1)}, {variable}₂ = {formatear(r2)}"
            resultado_latex = (f"{variable}_1 = {formatear_latex(r1)},\\quad"
                               f"{variable}_2 = {formatear_latex(r2)}")
        metodo = "factorización"
    else:
        # La raíz exacta se mantiene como radical simplificado por SymPy.
        aa = sp.Rational(a.numerator, a.denominator)
        bb = sp.Rational(b.numerator, b.denominator)
        dd = sp.Rational(discriminante.numerator, discriminante.denominator)
        raiz_simbolica = sp.sqrt(dd)
        denominador = 2 * aa
        raiz_menos = sp.simplify((-bb - raiz_simbolica) / denominador)
        raiz_mas = sp.simplify((-bb + raiz_simbolica) / denominador)
        sust_t = (f"x = (−({b_t}) − √({delta_t})) / (2 × {a_t})  o  "
                  f"x = (−({b_t}) + √({delta_t})) / (2 × {a_t})")
        sust_l = (f"x = \\frac{{-({formatear_latex(b)}) - \\sqrt{{{delta_l}}}}}"
                  f"{{2\\cdot {formatear_latex(a)}}}\\quad\\text{{o}}\\quad"
                  f"x = \\frac{{-({formatear_latex(b)}) + \\sqrt{{{delta_l}}}}}"
                  f"{{2\\cdot {formatear_latex(a)}}}")
        pasos.append(_paso(
            len(pasos) + 1, "formula_general",
            "Como Δ no es un cuadrado racional, usamos la fórmula general y sustituimos a, b y Δ.",
            "La fórmula general permite obtener las raíces exactas cuando no se factoriza con números racionales.",
            sust_t, sust_l,
        ))
        doble = sp.simplify(raiz_menos - raiz_mas) == 0
        raices = [raiz_menos] if doble else [raiz_menos, raiz_mas]
        if doble:
            resultado = f"{variable} = {_texto_raiz(raiz_menos, sp)} (raíz doble)"
            resultado_latex = f"{variable} = {_latex_raiz(raiz_menos, sp)}\\quad\\text{{(raíz doble)}}"
        else:
            resultado = f"{variable}₁ = {_texto_raiz(raiz_menos, sp)}, {variable}₂ = {_texto_raiz(raiz_mas, sp)}"
            resultado_latex = (f"{variable}_1 = {_latex_raiz(raiz_menos, sp)},\\quad"
                               f"{variable}_2 = {_latex_raiz(raiz_mas, sp)}")
        metodo = "fórmula general"

    # La sustitución se evalúa en los dos miembros originales, no solo en el trinomio reducido.
    comprobaciones = []
    for i, raiz in enumerate(raices, 1):
        diferencia = sp.simplify(original_izq.subs(x, raiz) - original_der.subs(x, raiz))
        if diferencia != 0:
            raise ErrorMotor(f"La comprobación de la raíz {sp.sstr(raiz)} falló: la diferencia es {sp.sstr(diferencia)}.")
        comprobaciones.append(f"{variable}{i} sustituida en la igualdad original da ambos lados iguales")
    pasos.append(_paso(
        len(pasos) + 1, "comprobar",
        "Comprobamos por sustitución: " + "; ".join(comprobaciones) + ".",
        "Reemplazar cada raíz en la ecuación original confirma que satisface la igualdad.",
        "Comprobación: ambas raíces satisfacen la ecuación original" if len(raices) > 1 else
        "Comprobación: la raíz satisface la ecuación original",
        r"\text{Sustitución verificada en la ecuación original}",
    ))
    return Solucion(tipo="ecuacion_cuadratica", entrada=texto,
                    expresion_inicial=texto.strip(), latex_inicial=ec_latex,
                    pasos=pasos, resultado=resultado, resultado_latex=resultado_latex,
                    nota=f"Método: {metodo}. Sustitución verificada en la ecuación original.")
