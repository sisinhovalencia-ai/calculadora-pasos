"""El Formulario: fórmulas de uso frecuente (física básica, geometría, ingeniería industrial) para despejar y calcular.

    from motor.formulario import TEMAS, despejar, calcular
    f = formula("ohm")                                     # V = I·R
    despejar("ohm", "I")                                   # I = V/R, con todos los pasos
    calcular("ohm", "I", {"V": "12", "R": "4"})            # I = 12/4 = 3  (A)

Cada fórmula dice qué significa cada letra y en qué unidad va. `despejar` usa `resolver_formula` (álgebra) y `calcular` además
sustituye los números que escribe el estudiante y los resuelve con el motor de aritmética: es decir, todos los pasos que se
ven ya están probados en sus propios módulos.

El motor admite fórmulas lineales y potencias aisladas (por ejemplo, energía cinética y área del círculo). Una prueba comprueba
que cada letra de cada fórmula se pueda despejar y que el cálculo numérico dé lo mismo que SymPy.
"""

import re
from dataclasses import dataclass, replace
from functools import lru_cache
from html import escape

from .aritmetica import resolver
from .errores import ErrorDeEntrada, ErrorMatematico
from .expr import tiene_letras
from .formulas import resolver_formula
from .pasos import Paso, Solucion


@dataclass(frozen=True)
class Variable:
    letra: str
    nombre: str
    unidad: str


@dataclass(frozen=True)
class Formula:
    id: str
    nombre: str
    expresion: str                    # lo que entiende el motor: «v = d/t»
    variables: tuple[Variable, ...]
    nota: str = ""

    def variable(self, letra: str) -> Variable:
        for v in self.variables:
            if v.letra == letra:
                return v
        raise ErrorDeEntrada(f"La fórmula «{self.nombre}» no tiene la letra {letra}.")


@dataclass(frozen=True)
class Tema:
    id: str
    nombre: str
    icono: str
    formulas: tuple[Formula, ...]


def _v(letra: str, nombre: str, unidad: str) -> Variable:
    return Variable(letra, nombre, unidad)


TEMAS: tuple[Tema, ...] = (
    Tema("movimiento", "Movimiento", "🏃", (
        Formula("velocidad", "Velocidad", "v = d/t",
                (_v("v", "velocidad", "m/s"), _v("d", "distancia", "m"), _v("t", "tiempo", "s"))),
        Formula("aceleracion", "Aceleración", "a = (v − u)/t",
                (_v("a", "aceleración", "m/s²"), _v("v", "velocidad final", "m/s"),
                 _v("u", "velocidad inicial", "m/s"), _v("t", "tiempo", "s"))),
        Formula("velocidad_final", "Velocidad final (aceleración constante)", "v = u + a·t",
                (_v("v", "velocidad final", "m/s"), _v("u", "velocidad inicial", "m/s"),
                 _v("a", "aceleración", "m/s²"), _v("t", "tiempo", "s"))),
        Formula("distancia_media", "Distancia con velocidad media", "d = (u + v)·t/2",
                (_v("d", "distancia", "m"), _v("u", "velocidad inicial", "m/s"),
                 _v("v", "velocidad final", "m/s"), _v("t", "tiempo", "s"))),
    )),
    Tema("fuerza", "Fuerza, trabajo y energía", "💪", (
        Formula("newton", "Segunda ley de Newton", "F = m·a",
                (_v("F", "fuerza", "N"), _v("m", "masa", "kg"), _v("a", "aceleración", "m/s²"))),
        Formula("peso", "Peso", "P = m·g",
                (_v("P", "peso", "N"), _v("m", "masa", "kg"), _v("g", "gravedad", "m/s²")),
                "En la Tierra, g ≈ 9,8 m/s²."),
        Formula("trabajo", "Trabajo", "W = F·d",
                (_v("W", "trabajo", "J"), _v("F", "fuerza", "N"), _v("d", "distancia", "m"))),
        Formula("potencia", "Potencia mecánica", "P = W/t",
                (_v("P", "potencia", "W"), _v("W", "trabajo", "J"), _v("t", "tiempo", "s"))),
        Formula("cantidad_movimiento", "Cantidad de movimiento", "p = m·v",
                (_v("p", "cantidad de movimiento", "kg·m/s"), _v("m", "masa", "kg"), _v("v", "velocidad", "m/s"))),
        Formula("impulso", "Impulso", "J = F·t",
                (_v("J", "impulso", "N·s"), _v("F", "fuerza", "N"), _v("t", "tiempo", "s"))),
        Formula("energia_potencial", "Energía potencial gravitatoria", "E = m·g·h",
                (_v("E", "energía potencial", "J"), _v("m", "masa", "kg"), _v("g", "gravedad", "m/s²"),
                 _v("h", "altura", "m")),
                "En la Tierra, g ≈ 9,8 m/s²."),
        Formula("energia_cinetica", "Energía cinética", "K = m·v²/2",
                (_v("K", "energía cinética", "J"), _v("m", "masa", "kg"), _v("v", "rapidez", "m/s")),
                "Al despejar v aparecen las dos raíces algebraicas; en física, la rapidez se toma no negativa."),
        Formula("presion", "Presión", "p = F/A",
                (_v("p", "presión", "Pa"), _v("F", "fuerza", "N"), _v("A", "área", "m²"))),
    )),
    Tema("electricidad", "Electricidad", "⚡", (
        Formula("ohm", "Ley de Ohm", "V = I·R",
                (_v("V", "voltaje", "V"), _v("I", "corriente", "A"), _v("R", "resistencia", "Ω"))),
        Formula("potencia_electrica", "Potencia eléctrica", "P = V·I",
                (_v("P", "potencia", "W"), _v("V", "voltaje", "V"), _v("I", "corriente", "A"))),
        Formula("carga", "Carga eléctrica", "Q = I·t",
                (_v("Q", "carga", "C"), _v("I", "corriente", "A"), _v("t", "tiempo", "s"))),
    )),
    Tema("materia", "Materia y calor", "🌡️", (
        Formula("densidad", "Densidad", "D = m/V",
                (_v("D", "densidad", "kg/m³"), _v("m", "masa", "kg"), _v("V", "volumen", "m³"))),
        Formula("presion_fluido", "Presión en un fluido", "p = D·g·h",
                (_v("p", "presión", "Pa"), _v("D", "densidad del fluido", "kg/m³"), _v("g", "gravedad", "m/s²"),
                 _v("h", "profundidad", "m")),
                "En la Tierra, g ≈ 9,8 m/s². Para el agua, D = 1000 kg/m³."),
        Formula("calor", "Calor absorbido", "Q = m·c·T",
                (_v("Q", "calor", "J"), _v("m", "masa", "kg"), _v("c", "calor específico", "J/(kg·°C)"),
                 _v("T", "cambio de temperatura", "°C")),
                "Para el agua, c ≈ 4186 J/(kg·°C)."),
        Formula("fahrenheit", "Grados Celsius y Fahrenheit", "F = 9C/5 + 32",
                (_v("F", "temperatura en Fahrenheit", "°F"), _v("C", "temperatura en Celsius", "°C"))),
    )),
    Tema("geometria", "Geometría", "📐", (
        Formula("area_rectangulo", "Área del rectángulo", "A = b·h",
                (_v("A", "área", "unidades²"), _v("b", "base", "unidades"), _v("h", "altura", "unidades"))),
        Formula("area_triangulo", "Área del triángulo", "A = b·h/2",
                (_v("A", "área", "unidades²"), _v("b", "base", "unidades"), _v("h", "altura", "unidades"))),
        Formula("perimetro_rectangulo", "Perímetro del rectángulo", "P = 2l + 2w",
                (_v("P", "perímetro", "unidades"), _v("l", "largo", "unidades"), _v("w", "ancho", "unidades"))),
        Formula("circunferencia", "Longitud de la circunferencia", "C = 2πr",
                (_v("C", "longitud", "unidades"), _v("r", "radio", "unidades")),
                "Se usa π ≈ 3,1416."),
        Formula("area_circulo", "Área del círculo", "A = πr²",
                (_v("A", "área", "unidades²"), _v("r", "radio", "unidades")),
                "Al despejar r aparecen las dos raíces algebraicas; por definición, el radio se toma no negativo."),
    )),
    Tema("industrial", "Ingeniería industrial y finanzas", "🏭", (
        Formula("interes_simple", "Interés simple", "I = C·r·t",
                (_v("I", "interés", "$"), _v("C", "capital", "$"), _v("r", "tasa por período", "ej. 0,05 = 5 %"),
                 _v("t", "períodos", "años, meses…")),
                "La tasa y el tiempo deben estar en el mismo período (tasa anual con años)."),
        Formula("monto", "Monto con interés simple", "M = C·(1 + r·t)",
                (_v("M", "monto final", "$"), _v("C", "capital", "$"), _v("r", "tasa por período", "ej. 0,05 = 5 %"),
                 _v("t", "períodos", "años, meses…"))),
        Formula("productividad", "Productividad", "P = S/E",
                (_v("P", "productividad", "unidades por recurso"), _v("S", "salida (producción)", "unidades"),
                 _v("E", "entrada (recursos usados)", "horas, $…"))),
        Formula("costo_total", "Costo total", "T = F + c·q",
                (_v("T", "costo total", "$"), _v("F", "costos fijos", "$"), _v("c", "costo por unidad", "$/unidad"),
                 _v("q", "cantidad producida", "unidades"))),
        Formula("utilidad", "Utilidad (y punto de equilibrio)", "U = (p − c)·q − F",
                (_v("U", "utilidad", "$"), _v("p", "precio de venta", "$/unidad"), _v("c", "costo por unidad", "$/unidad"),
                 _v("q", "cantidad vendida", "unidades"), _v("F", "costos fijos", "$")),
                "Con U = 0 se halla el punto de equilibrio: la cantidad q donde no se gana ni se pierde."),
    )),
)

FORMULAS: dict[str, Formula] = {f.id: f for t in TEMAS for f in t.formulas}
TEMA_DE: dict[str, Tema] = {f.id: t for t in TEMAS for f in t.formulas}

PI_APROX = "3.1416"
_NUMERO_SIMPLE = re.compile(r"\d+(?:[.,]\d+)?")
MAX_VALOR = 24


def formula(id_formula: str) -> Formula:
    try:
        return FORMULAS[id_formula]
    except KeyError:
        raise ErrorDeEntrada(f"No conozco la fórmula «{id_formula}».") from None


def despejar(id_formula: str, letra: str) -> Solucion:
    """Despeja `letra` de la fórmula, con todos los pasos (sin números)."""
    f = formula(id_formula)
    f.variable(letra)
    return resolver_formula(f"despejar {letra} en {f.expresion}")


def _valor_valido(letra: str, texto: str) -> str:
    texto = (texto or "").strip()
    if not texto:
        raise ErrorDeEntrada(f"Falta el valor de {letra}.")
    if len(texto) > MAX_VALOR:
        raise ErrorDeEntrada(f"El valor de {letra} es demasiado largo.")
    if tiene_letras(texto):
        raise ErrorDeEntrada(f"El valor de {letra} debe ser un número (por ejemplo 12, 4,5 o 1/2), no «{texto}».")
    try:
        resolver(texto)                       # también acepta 1/2, −3, 2,5...; falla si no es una expresión válida
    except ErrorDeEntrada as e:
        raise ErrorDeEntrada(f"El valor de {letra} no se entiende: {e}") from None
    except ErrorMatematico as e:
        raise ErrorMatematico(f"El valor de {letra} no es válido: {e}") from None
    return texto


def _sustituir(expresion: str, valores: dict[str, str]) -> tuple[str, bool]:
    """Pone cada letra de `expresion` (ya despejada) por su valor. Devuelve (texto, ¿se usó π?)."""
    salida: list[str] = []
    uso_pi = False
    for i, c in enumerate(expresion):
        if c == "π":
            valor, uso_pi = PI_APROX, True
        elif c in valores:
            valor = valores[c]
        else:
            salida.append(c)
            continue
        antes = salida[-1] if salida else ""
        despues = expresion[i + 1] if i + 1 < len(expresion) else ""
        pegado = antes.isalnum() or antes in ")π" or despues.isalnum() or despues in "(π"
        simple = _NUMERO_SIMPLE.fullmatch(valor) is not None
        salida.append(valor if (simple and not pegado) else f"({valor})")
    return "".join(salida), uso_pi


def calcular(id_formula: str, objetivo: str, valores: dict[str, str]) -> Solucion:
    """Despeja `objetivo` y calcula con los números dados para las demás letras.

    Los pasos son: el despeje, la sustitución y las operaciones (con el orden de operaciones de siempre)."""
    f = formula(id_formula)
    f.variable(objetivo)
    otras = [v for v in f.variables if v.letra != objetivo]
    limpios = {v.letra: _valor_valido(v.letra, valores.get(v.letra, "")) for v in otras}

    despeje = resolver_formula(f"despejar {objetivo} en {f.expresion}")
    derecha = despeje.resultado.split("=", 1)[1].strip()
    dos_ramas = derecha.startswith("±")
    expresion_positiva = derecha[1:] if dos_ramas else derecha
    sustituida, uso_pi = _sustituir(expresion_positiva, limpios)
    if any(raiz in sustituida for raiz in ("√", "∛", "∜")):
        from .radicales import resolver_radicales
        aritmetica = resolver_radicales(sustituida)
    else:
        aritmetica = resolver(sustituida)

    pasos = [p for p in despeje.pasos if p.regla != "comprobar"]          # la comprobación simbólica sobra aquí
    datos = ", ".join(f"{v.letra} = {limpios[v.letra]} {v.unidad}" for v in otras)
    pi_txt = " Para π usamos 3,1416." if uso_pi else ""
    pasos.append(Paso(
        numero=len(pasos) + 1, regla="sustituir",
        explicacion=f"Ya despejamos {objetivo}. Ahora ponemos los valores que conocemos ({datos}) en lugar de las letras.{pi_txt}",
        motivo="Con la letra despejada, solo hay que reemplazar cada letra por su número y hacer las operaciones en el "
               "orden de siempre.",
        operacion=datos, resultado_parcial="",
        expresion=f"{objetivo} = {'±' if dos_ramas else ''}{aritmetica.expresion_inicial}",
        latex=f"{objetivo} = {'\\pm ' if dos_ramas else ''}{aritmetica.latex_inicial}"))
    for p in aritmetica.pasos:                                  # «25/2» se lee mejor como «v = 25/2»
        pasos.append(replace(p, numero=len(pasos) + 1, expresion=f"{objetivo} = {'±' if dos_ramas else ''}{p.expresion}",
                             latex=f"{objetivo} = {'\\pm ' if dos_ramas else ''}{p.latex}",
                             pizarra=None))

    unidad = f.variable(objetivo).unidad
    respuesta = f"{objetivo} = {'±' if dos_ramas else ''}{aritmetica.resultado}"
    decimal = ""
    if aritmetica.resultado_decimal:
        decimal = f" {'=' if aritmetica.decimal_exacto else '≈'} {aritmetica.resultado_decimal} {unidad}"
    nota = (f"Respuesta: {respuesta} {unidad}{decimal} ({f.variable(objetivo).nombre})."
            + (" Se usó π ≈ 3,1416." if uso_pi else ""))
    return Solucion(
        tipo="formula_numerica", entrada=f"{f.expresion} | {objetivo} | {limpios}",
        expresion_inicial=f"{f.expresion}   →   {objetivo} = ?", latex_inicial=despeje.latex_inicial,
        pasos=pasos, resultado=respuesta, resultado_latex=f"{objetivo} = {'\\pm ' if dos_ramas else ''}{aritmetica.resultado_latex}",
        resultado_decimal=aritmetica.resultado_decimal, decimal_exacto=aritmetica.decimal_exacto, nota=nota)


def etiqueta_variable(v: Variable) -> str:
    """«v — velocidad (m/s)» listo para mostrar (escapado para HTML)."""
    return escape(f"{v.letra} — {v.nombre} ({v.unidad})")


@lru_cache(maxsize=None)
def latex_formula(id_formula: str) -> str:
    """La fórmula escrita en LaTeX (con fracciones de verdad), para dibujarla en pantalla."""
    f = formula(id_formula)
    return resolver_formula(f"despejar {f.variables[0].letra} en {f.expresion}").latex_inicial
