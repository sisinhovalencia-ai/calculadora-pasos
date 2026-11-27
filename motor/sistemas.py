"""Sistemas lineales 2×2 por eliminación de filas, paso a paso."""

from fractions import Fraction

from .arbol import BinOp, Cociente, Frac, Mixto, Neg, Num, Paren, Porc, Raiz, Var
from .cuadraticas import _a_sympy
from .ecuaciones import _separar
from .errores import ErrorDeEntrada, ErrorMatematico, ErrorMotor
from .numeros import formatear, formatear_latex
from .parser import parsear
from .pasos import Paso, Solucion


def _a_fraction(valor) -> Fraction:
    return Fraction(int(valor.p), int(valor.q))


def _variables(n, salida=None):
    if salida is None:
        salida = []
    if isinstance(n, Var):
        if n.nombre not in salida:
            salida.append(n.nombre)
    elif isinstance(n, (Neg, Paren, Raiz)):
        _variables(n.hijo, salida)
    elif isinstance(n, BinOp):
        _variables(n.izq, salida)
        _variables(n.der, salida)
    elif isinstance(n, Cociente):
        _variables(n.num, salida)
        _variables(n.den, salida)
    return salida


def _separar_sistema(texto: str) -> list[str]:
    ecuaciones = [parte.strip() for parte in texto.replace("\r", "").split(";")]
    if len(ecuaciones) == 1:
        ecuaciones = [linea.strip() for linea in texto.splitlines()]
    if any(not ecuacion for ecuacion in ecuaciones):
        raise ErrorDeEntrada("Separa las ecuaciones con punto y coma o escribe una ecuación por línea.")
    if len(ecuaciones) != 2:
        raise ErrorDeEntrada("Por ahora resuelvo sistemas de dos ecuaciones con dos incógnitas (2×2).")
    return ecuaciones


def _texto_termino(coef: Fraction, variable: str) -> str:
    magnitud = abs(coef)
    if magnitud == 1:
        return variable
    return f"{formatear(magnitud)}{variable}"


def _latex_termino(coef: Fraction, variable: str) -> str:
    magnitud = abs(coef)
    if magnitud == 1:
        return variable
    return f"{formatear_latex(magnitud)}{variable}"


def _fila_texto(fila, variables) -> str:
    a, b, resultado = fila
    terminos = []
    for coef, variable in zip((a, b), variables):
        if coef:
            termino = _texto_termino(coef, variable)
            terminos.append(("− " if coef < 0 else "") + termino if not terminos else
                            (" − " if coef < 0 else " + ") + termino)
    izquierda = "".join(terminos) or "0"
    return f"{izquierda} = {formatear(resultado)}"


def _fila_latex(fila, variables) -> str:
    a, b, resultado = fila
    terminos = []
    for coef, variable in zip((a, b), variables):
        if coef:
            termino = _latex_termino(coef, variable)
            terminos.append(("-" if coef < 0 else "") + termino if not terminos else
                            (" - " if coef < 0 else " + ") + termino)
    izquierda = "".join(terminos) or "0"
    return f"{izquierda} = {formatear_latex(resultado)}"


def _sistema_texto(filas, variables) -> tuple[str, str]:
    t = " ; ".join(f"{i + 1}) {_fila_texto(fila, variables)}" for i, fila in enumerate(filas))
    l = r"\quad".join(rf"{i + 1})\;{_fila_latex(fila, variables)}" for i, fila in enumerate(filas))
    return t, l


def _agregar(pasos, regla, explicacion, motivo, filas, variables, operacion=""):
    texto, latex = _sistema_texto(filas, variables)
    pasos.append(Paso(numero=len(pasos) + 1, regla=regla, explicacion=explicacion, motivo=motivo,
                      operacion=operacion, resultado_parcial="", expresion=texto, latex=latex))


def resolver_sistema(texto: str) -> Solucion:
    """Resuelve un sistema lineal 2×2 escrito con ``;`` o saltos de línea."""
    import sympy as sp

    ecuaciones = _separar_sistema(texto or "")
    nodos = []
    variables = []
    for ecuacion in ecuaciones:
        relacion, izq, der = _separar(ecuacion)
        if relacion != "=":
            raise ErrorDeEntrada("En un sistema lineal usa ecuaciones con el signo =.")
        if not izq.strip() or not der.strip():
            raise ErrorDeEntrada("Cada ecuación del sistema debe tener un lado a cada lado del signo =.")
        nodo_izq, _ = parsear(izq, variables=True)
        nodo_der, _ = parsear(der, variables=True)
        nodos.append((nodo_izq, nodo_der))
        _variables(nodo_izq, variables)
        _variables(nodo_der, variables)
    if len(variables) != 2:
        raise ErrorDeEntrada("El sistema debe tener exactamente dos incógnitas, por ejemplo x e y.")

    simbolos = [sp.Symbol(v) for v in variables]
    originales = []
    filas = []
    for nodo_izq, nodo_der in nodos:
        izq, der = _a_sympy(nodo_izq, sp), _a_sympy(nodo_der, sp)
        diferencia = sp.expand(izq - der)
        try:
            pol = sp.Poly(diferencia, *simbolos)
        except sp.PolynomialError as e:
            raise ErrorMatematico("Cada ecuación del sistema debe ser lineal y no llevar incógnitas en denominadores o raíces.") from e
        if pol.total_degree() > 1:
            raise ErrorMatematico("Cada ecuación del sistema debe ser lineal: no eleves ni multipliques incógnitas entre sí.")
        coeficientes = [_a_fraction(pol.coeff_monomial(s)) for s in simbolos]
        constante = _a_fraction(pol.coeff_monomial(1))
        filas.append([*coeficientes, -constante])
        originales.append((izq, der))

    pasos: list[Paso] = []
    normalizadas = [fila.copy() for fila in filas]
    _agregar(pasos, "normalizar_sistema",
             "Llevamos los términos con incógnitas a la izquierda y los números al otro lado; reducimos términos semejantes.",
             "La eliminación se entiende mejor cuando cada ecuación queda en la forma ax + by = c.",
             normalizadas, variables, "; ".join(ecuaciones))

    matriz = [fila.copy() for fila in normalizadas]
    pivotes: list[tuple[int, int]] = []
    fila_pivote = 0
    for columna, variable in enumerate(variables):
        candidatos = [r for r in range(fila_pivote, 2) if matriz[r][columna] != 0]
        if not candidatos:
            continue
        elegido = candidatos[0]
        if elegido != fila_pivote:
            matriz[fila_pivote], matriz[elegido] = matriz[elegido], matriz[fila_pivote]
            _agregar(pasos, "intercambiar_filas",
                     f"Intercambiamos las ecuaciones {fila_pivote + 1} y {elegido + 1} para usar una fila con coeficiente de {variable} distinto de cero.",
                     "Un pivote no puede ser cero; cambiar el orden de las ecuaciones conserva las soluciones.",
                     matriz, variables)
        pivote = matriz[fila_pivote][columna]
        if pivote != 1:
            matriz[fila_pivote] = [valor / pivote for valor in matriz[fila_pivote]]
            _agregar(pasos, "escalar_fila",
                     f"Dividimos la ecuación {fila_pivote + 1} entre {formatear(pivote)} para que el coeficiente de {variable} sea 1.",
                     "Dividir todos los términos de una ecuación por el mismo número distinto de cero no cambia sus soluciones.",
                     matriz, variables)
        for otra in range(2):
            if otra == fila_pivote:
                continue
            factor = matriz[otra][columna]
            if factor:
                matriz[otra] = [u - factor * v for u, v in zip(matriz[otra], matriz[fila_pivote])]
                _agregar(pasos, "eliminar_variable",
                         f"Combinamos las ecuaciones para eliminar {variable} de la ecuación {otra + 1}.",
                         "Al restar un múltiplo de una ecuación equivalente, se cancela una incógnita y se mantiene el mismo conjunto de soluciones.",
                         matriz, variables)
        pivotes.append((fila_pivote, columna))
        fila_pivote += 1
        if fila_pivote == 2:
            break

    inconsistente = any(fila[0] == 0 and fila[1] == 0 and fila[2] != 0 for fila in matriz)
    if inconsistente:
        pasos.append(Paso(
            numero=len(pasos) + 1, regla="sin_solucion",
            explicacion="La eliminación deja una igualdad falsa, 0 = número distinto de cero; el sistema no tiene solución.",
            motivo="Una igualdad falsa no puede cumplirse para ningún valor de las incógnitas.",
            operacion="0 = número distinto de cero", resultado_parcial="",
            expresion="Sin solución", latex=r"\text{Sin solución}"))
        resultado = "Sin solución"
        nota = "El sistema es incompatible: sus ecuaciones se contradicen."
    elif len(pivotes) < 2:
        pasos.append(Paso(
            numero=len(pasos) + 1, regla="infinitas_soluciones",
            explicacion="Una ecuación queda como múltiplo de la otra; ambas representan la misma recta y el sistema tiene infinitas soluciones.",
            motivo="Si las ecuaciones no se contradicen y solo aportan una relación independiente entre dos incógnitas, queda una variable libre.",
            operacion="Una relación independiente para dos incógnitas", resultado_parcial="",
            expresion="Infinitas soluciones", latex=r"\text{Infinitas soluciones}"))
        resultado = "Infinitas soluciones"
        nota = "Las soluciones forman una recta: una incógnita puede elegirse libremente y la otra se determina con la ecuación reducida."
    else:
        soluciones = [Fraction(0), Fraction(0)]
        for fila, columna in pivotes:
            soluciones[columna] = matriz[fila][2]
        for (izq, der) in originales:
            for simbolo, valor in zip(simbolos, soluciones):
                izq = izq.subs(simbolo, sp.Rational(valor.numerator, valor.denominator))
                der = der.subs(simbolo, sp.Rational(valor.numerator, valor.denominator))
            if sp.simplify(izq - der) != 0:
                raise ErrorMotor("La comprobación del sistema falló al sustituir la solución en una ecuación original.")
        x, y = variables
        xv, yv = map(formatear, soluciones)
        resultado = f"{x} = {xv}, {y} = {yv}"
        resultado_latex = f"{x} = {formatear_latex(soluciones[0])},\\quad {y} = {formatear_latex(soluciones[1])}"
        pasos.append(Paso(
            numero=len(pasos) + 1, regla="comprobar_sistema",
            explicacion=f"Sustituimos {x} = {xv} e {y} = {yv} en las dos ecuaciones originales; ambas igualdades se cumplen.",
            motivo="La solución del sistema debe satisfacer cada una de las ecuaciones de partida.",
            operacion="Sustituir en las ecuaciones originales", resultado_parcial="",
            expresion=resultado, latex=resultado_latex))
        nota = "La solución única quedó comprobada en ambas ecuaciones originales."

    expr_inicial, latex_inicial = _sistema_texto(normalizadas, variables)
    return Solucion(tipo="sistema_lineal", entrada=texto, expresion_inicial=expr_inicial,
                    latex_inicial=latex_inicial, pasos=pasos, resultado=resultado,
                    resultado_latex=(r"\text{Sin solución}" if resultado == "Sin solución" else
                                     r"\text{Infinitas soluciones}" if resultado == "Infinitas soluciones" else resultado_latex),
                    nota=nota)
