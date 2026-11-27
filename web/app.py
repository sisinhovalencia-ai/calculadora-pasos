"""Interfaz web de la calculadora paso a paso.

Ejecutar desde la carpeta raíz del proyecto:

    python main.py

y abrir http://localhost:8000  (también acepta /?q=1/2+1/3 para abrir un ejercicio).

Esta capa SOLO dibuja: toda la matemática vive en `motor/`.
Recibe una `Solucion` (ver motor/pasos.py) y la muestra, sin saber de qué tipo es.

Notas para quien retome esto:
  - `pintar()` dibuja un resultado completo. `siguiente()` en cambio solo AÑADE el paso
    nuevo: así no se pierde el foco del teclado ni se repite la animación del margen rojo.
  - Los ejemplos de las tres filas se crean con `_fila_ejemplos()`; para agregar una fila
    basta con una lista nueva y una llamada.
  - Todo texto variable pasa por `escape()` antes de llegar a `_html()`.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from html import escape

from nicegui import app, ui
from starlette.responses import PlainTextResponse

from motor import ErrorDeEntrada, ErrorMotor, Solucion, resolver_columnas
from motor.algebra import separar_comando, tiene_comando
from motor.formulario import TEMAS
from motor.formulario import calcular as calcular_formula
from motor.formulario import despejar as despejar_formula
from motor.formulario import formula as buscar_formula
from motor.formulario import latex_formula
from motor import resolver_ejercicio as resolver_auto   # (la de la página se llama igual: ver más abajo)

from .estilos import CSS, HEAD_HTML
from .formulas import mathml, resaltar

log = logging.getLogger("web")

TITULO = "MatrixOps | Tu tutor matemático paso a paso"
MAX_CARACTERES = 200   # un ejercicio escolar nunca es más largo; evita entradas enormes

EJEMPLOS = ["2 + 3 × (4 − 1)^2", "1/2 + 1/3", "4/6 + 1/3", "3 1/2 + 2 3/4",
            "20% de 150", "√(16 + 9)", "−3^2", "0.1 + 0.2"]

EJEMPLOS_ECUACIONES = ["2x + 3 = 11", "3x − 5 = 2x + 7", "2(x + 3) = 14", "x/2 + 1 = 5",
                      "x² − 5x + 6 = 0", "x² − 2 = 0"]
EJEMPLOS_DESIGUALDADES = ["2x + 3 < 11", "−2x + 1 ≥ 7", "3(x − 1) > 2x + 4", "x/2 − 1 ≤ 3"]
EJEMPLOS_FORMULAS = ["despejar t en v = d/t", "despejar h en A = b·h/2", "despejar w en P = 2l + 2w",
                     "despejar C en F = 9C/5 + 32", "despejar a en F = ma"]
EJEMPLOS_ALGEBRA = ["(x + 3)²", "(2x + 3)(2x − 3)", "(x + 2)(x + 5)", "(3x² + 2x) − (x² − 5x)"]
EJEMPLOS_FACTORIZAR = ["factorizar x² − 9", "factorizar x² + 5x + 6", "factorizar 2x² + 7x + 3",
                       "factorizar ax + ay + bx + by", "factorizar x³ − 8"]
EJEMPLOS_FRACCIONES = ["(x² − 9)/(x − 3)", "1/(x − 1) + 1/(x + 1)", "(x² − 4)/(x + 1) · (x + 1)/(x − 2)"]
EJEMPLOS_RAICES = ["√12", "√50 + √8", "1/√2", "3/(2 + √5)", "8^(1/3)"]
COMANDOS = ("factorizar", "desarrollar", "simplificar")
# Nivel de la calculadora: qué teclas y ejemplos se ven. «Todo» muestra todo (es lo normal).
NIVELES = {"Todo": 9, "Básica": 1, "Ecuaciones": 2, "Álgebra": 3}
NIVEL_DE_TECLA = {"x": 2, "=": 2, "<": 2, ">": 2, "≤": 2, "≥": 2, "despejar": 2,
                  "²": 3, "³": 3, "simplificar": 3, "factorizar": 3, "desarrollar": 3}
TIEMPO_MAXIMO = 20        # segundos que se espera una solución antes de decir «tarda demasiado»
EJEMPLOS_COLUMNAS = ["4567 + 289", "905 − 267", "123 × 45", "7845 ÷ 12"]

# (texto, es_operador)
TECLAS = [
    ("7", 0), ("8", 0), ("9", 0), ("÷", 1),
    ("4", 0), ("5", 0), ("6", 0), ("×", 1),
    ("1", 0), ("2", 0), ("3", 0), ("−", 1),
    ("0", 0), (".", 0), ("(", 1), (")", 1),
    ("^", 1), ("+", 1), ("⌫", 1), ("C", 1),
    ("√", 1), ("∛", 1), ("∜", 1), ("%", 1),
    ("/", 1), ("de", 1), ("x", 1), ("=", 1),
    ("<", 1), (">", 1), ("≤", 1), ("≥", 1),
    ("²", 1), ("³", 1),
]

# Los lectores de pantalla leen mal los símbolos sueltos: les damos un nombre claro.
ETIQUETAS_TECLAS = {
    "÷": "Dividir", "×": "Multiplicar", "−": "Restar", "+": "Sumar",
    "^": "Elevar a una potencia", "√": "Raíz cuadrada", "∛": "Raíz cúbica", "∜": "Raíz cuarta",
    "%": "Por ciento", "/": "Fracción", "de": "De", "x": "La incógnita x", "=": "Igual",
    "<": "Menor que", ">": "Mayor que", "≤": "Menor o igual que", "≥": "Mayor o igual que",
    "²": "Al cuadrado", "³": "Al cubo",
    "(": "Abrir paréntesis", ")": "Cerrar paréntesis", ".": "Punto decimal",
    "⌫": "Borrar el último símbolo", "C": "Borrar todo",
}


@dataclass
class Estado:
    """Lo que la página recuerda entre un clic y otro (uno por pestaña del navegador)."""
    sol: Solucion | None = None
    error: str | None = None
    visibles: int = 0          # cuántos pasos se muestran ahora
    uno_a_uno: bool = False
    columnas: bool = False
    tipo_error: str | None = None
    historial: list[dict[str, str]] = field(default_factory=list)
    resolviendo: bool = False


def _html(contenido: str, *, tag: str = "div"):
    # sanitize=False es seguro aquí: todo texto variable pasa por escape() (ver formulas.py)
    # y las fórmulas las genera latex2mathml a partir de lo que produce el motor.
    return ui.html(contenido, sanitize=False, tag=tag)


def _js(codigo: str) -> None:
    """Ejecuta JavaScript en el navegador; sin navegador conectado (pruebas) no pasa nada."""
    try:
        ui.run_javascript(codigo)
    except Exception:  # noqa: BLE001
        pass


def _tipo_motor(sol: Solucion) -> tuple[str, str]:
    """Nombres comprensibles para el panel técnico, derivados del tipo real del motor."""
    tipos = {
        "aritmetica": ("Aritmética", "Python · fracciones exactas"),
        "ecuacion_lineal": ("Ecuación lineal", "Python · solucionador lineal"),
        "desigualdad_lineal": ("Desigualdad lineal", "Python · solucionador lineal"),
        "factorizacion": ("Factorización", "SymPy · verificación algebraica"),
        "fraccion_algebraica": ("Fracción algebraica", "SymPy · verificación algebraica"),
        "radicales": ("Radicales", "Motor de radicales · comprobación numérica"),
        "polinomio": ("Expresión algebraica", "SymPy · verificación algebraica"),
        "formula": ("Despeje de fórmula", "SymPy · comprobación de la fórmula"),
        "formula_numerica": ("Cálculo con fórmula", "SymPy · comprobación de la fórmula"),
    }
    return tipos.get(sol.tipo, (sol.tipo.replace("_", " ").capitalize(), "Motor Python"))


_MOVIMIENTO = "matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'"


def _pizarra_html(pz: dict) -> str:
    """La pizarra de una operación en columnas: texto monoespaciado con lo resaltado entre <mark>."""
    marcas: dict[int, list[tuple[int, int]]] = {}
    for linea, a, b in pz["marcas"]:
        marcas.setdefault(linea, []).append((a, b))
    filas = []
    for i, texto in enumerate(pz["lineas"]):
        rangos = marcas.get(i, [])
        html, dentro = [], False
        for col, ch in enumerate(texto):
            marcado = any(a <= col < b for a, b in rangos)
            if marcado and not dentro:
                html.append("<mark>")
            elif dentro and not marcado:
                html.append("</mark>")
            dentro = marcado
            html.append(escape(ch))
        if dentro:
            html.append("</mark>")
        filas.append("".join(html))
    return '<pre class="pizarra" role="img" aria-label="Operación en columnas">' + "\n".join(filas) + "</pre>"


def _mensaje_columnas(texto: str, error: ErrorMotor) -> str:
    """En modo columnas, si el ejercicio sí se puede resolver normal, se lo decimos."""
    try:
        resolver_auto(texto)
    except ErrorMotor:
        return str(error)
    return ("Este ejercicio no es una sola operación entre números positivos, así que no se puede hacer en "
            "columnas. Apaga «En columnas (a mano)» y se resuelve paso a paso.")


def _paso_html(p) -> str:
    # Ecuaciones: encima del resultado se ve la operación escrita en los DOS lados (antes de simplificar)
    previa = (f'<div class="paso-expr paso-previa">{mathml(p.latex_intermedio, p.intermedio)}</div>'
              if p.latex_intermedio else "")
    cuerpo = previa + (_pizarra_html(p.pizarra) if p.pizarra
                       else f'<div class="paso-expr">{mathml(p.latex, p.expresion)}</div>')
    return (
        f'<span class="paso-num">{p.numero}</span>'
        f'<div class="paso-cuerpo">'
        f'<p class="paso-texto">{resaltar(p.explicacion, p.operacion)}</p>'
        f'{cuerpo}'
        f'<details class="porque"><summary>¿Por qué ahora?</summary>'
        f'<p>{escape(p.motivo)}</p></details>'
        f'</div>'
    )


def _final_html(sol: Solucion) -> str:
    decimal = ""
    if sol.resultado_decimal:
        signo = "=" if sol.decimal_exacto else "≈"
        decimal = f'<p class="final-decimal">En decimales: {signo} {escape(sol.resultado_decimal)}</p>'
    if sol.nota:
        decimal += f'<p class="final-decimal">{escape(sol.nota)}</p>'
    return (
        '<span class="final-marca" aria-hidden="true">✓</span>'
        '<div>'
        '<p class="final-etq">Resultado</p>'
        f'<span class="final-valor">{mathml(sol.resultado_latex, sol.resultado)}</span>'
        f'{decimal}'
        '</div>'
    )


def _fila_ejemplos(etiqueta: str, ejemplos: list[str], al_pulsar):
    """Una fila de botones de ejemplo con su rótulo («Prueba con:», «Ecuaciones:»...). Devuelve la fila."""
    with ui.element("div").classes("ejemplos") as fila:
        ui.label(etiqueta)
        for ej in ejemplos:
            ui.button(ej, on_click=lambda t=ej: al_pulsar(t), color=None).classes("ejemplo").props("flat no-caps")
    return fila


def _solucion_en_pantalla(sol: Solucion) -> None:
    """Dibuja un ejercicio resuelto completo (enunciado, todos los pasos y resultado) en el contenedor actual."""
    _html(mathml(sol.latex_inicial, sol.expresion_inicial)).classes("ejercicio")
    with ui.element("ol").classes("pasos"):
        for p in sol.pasos:
            _html(_paso_html(p), tag="li").classes("paso")
    _html(_final_html(sol)).classes("final").props('tabindex="-1"')


def _formulario() -> None:
    """La pestaña «Fórmulas»: elegir tema y fórmula, ver qué significa cada letra, despejar y calcular con números."""
    est: dict = {"tema": TEMAS[0].id, "formula": None, "objetivo": None, "valores": {}}
    cont: dict = {"res": None}

    def poner_tema(id_tema: str) -> None:
        est.update(tema=id_tema, formula=None, objetivo=None, valores={})
        dibujar.refresh()

    def poner_formula(id_formula: str) -> None:
        est.update(formula=id_formula, objetivo=buscar_formula(id_formula).variables[0].letra, valores={})
        dibujar.refresh()

    def poner_objetivo(letra: str) -> None:
        est["objetivo"] = letra               # los números que ya escribió se conservan
        dibujar.refresh()

    async def resolver(modo: str) -> None:
        res = cont["res"]
        if res is None or est["formula"] is None:
            return
        res.clear()
        id_f, obj = est["formula"], est["objetivo"]
        valores = dict(est["valores"])
        try:
            funcion = (lambda: despejar_formula(id_f, obj)) if modo == "despejar" else (lambda: calcular_formula(id_f, obj, valores))
            sol = await asyncio.wait_for(asyncio.to_thread(funcion), timeout=TIEMPO_MAXIMO)
        except asyncio.TimeoutError:
            with res:
                _html("<strong>No se pudo resolver</strong><p>Esto tarda demasiado en resolverse. Prueba de nuevo.</p>"
                      ).classes("error").props('role="alert"')
            return
        except ErrorMotor as e:
            with res:
                _html(f"<strong>No se pudo resolver</strong><p>{escape(str(e))}</p>").classes("error").props('role="alert"')
            return
        with res:
            _solucion_en_pantalla(sol)
        _js("setTimeout(() => { const z = document.querySelector('.zona-formula'); if (z) z.scrollIntoView({"
            f"behavior: {_MOVIMIENTO}, block: 'start'}}); }}, 80);")

    @ui.refreshable
    def dibujar() -> None:
        tema = next(t for t in TEMAS if t.id == est["tema"])
        with ui.element("div").classes("temas"):
            for t in TEMAS:
                (ui.button(f"{t.icono} {t.nombre}", on_click=lambda i=t.id: poner_tema(i), color=None)
                 .classes("tema" + (" activo" if t.id == est["tema"] else "")).props("flat no-caps").mark(f"tema-{t.id}"))
        with ui.element("div").classes("lista-formulas"):
            for f in tema.formulas:
                with (ui.button(on_click=lambda i=f.id: poner_formula(i), color=None)
                      .classes("tarjeta-formula" + (" activa" if f.id == est["formula"] else ""))
                      .props("flat no-caps").mark(f"formula-{f.id}")):
                    ui.label(f.nombre).classes("tarjeta-nombre")
                    ui.label(f.expresion).classes("tarjeta-expr")
        if est["formula"] is None:
            _html('<p class="formulas-intro">Elige una fórmula: verás qué significa cada letra, podrás despejar la que '
                  'necesites y calcular con tus propios números.</p>')
            cont["res"] = None
            return
        f = buscar_formula(est["formula"])
        obj = est["objetivo"]
        with ui.element("section").classes("detalle-formula"):
            _html(f"<h2>{escape(f.nombre)}</h2>")
            _html(mathml(latex_formula(f.id), f.expresion)).classes("formula-grande")
            filas = "".join(
                f'<tr><td class="letra-v">{escape(v.letra)}</td><td>{escape(v.nombre)}</td>'
                f'<td class="unidad-v">{escape(v.unidad)}</td></tr>' for v in f.variables)
            _html(f'<table class="variables" aria-label="Qué significa cada letra">{filas}</table>')
            if f.nota:
                _html(f'<p class="nota-formula">{escape(f.nota)}</p>')
            _html('<p class="pregunta">¿Qué letra quieres hallar?</p>')
            with ui.element("div").classes("letras"):
                for v in f.variables:
                    (ui.button(v.letra, on_click=lambda l=v.letra: poner_objetivo(l), color=None)
                     .classes("letra" + (" activa" if v.letra == obj else "")).props(f'flat no-caps aria-label="Hallar {escape(v.nombre)}"')
                     .mark(f"objetivo-{v.letra}"))
            _html('<p class="pregunta">¿Conoces los valores de las otras letras? Escríbelos y calcula '
                  '(si no, solo despeja).</p>')
            with ui.element("div").classes("datos"):
                for v in [w for w in f.variables if w.letra != obj]:
                    campo = ui.input(label=f"{v.letra} — {v.nombre} ({v.unidad})", value=est["valores"].get(v.letra, ""))
                    campo.props('outlined dense autocomplete="off" inputmode="text" maxlength="24"').mark(f"valor-{v.letra}")
                    campo.on_value_change(lambda e, l=v.letra: est["valores"].__setitem__(l, e.value or ""))
                    campo.on("keydown.enter", lambda: resolver("calcular"))
            with ui.element("div").classes("acciones-formula"):
                (ui.button(f"Despejar {obj}", on_click=lambda: resolver("despejar"), color=None)
                 .classes("boton-resolver").props("unelevated no-caps").mark("btn-despejar"))
                (ui.button(f"Calcular {obj}", on_click=lambda: resolver("calcular"), color=None)
                 .classes("boton-resolver boton-secundario").props("unelevated no-caps").mark("btn-calcular"))
        cont["res"] = ui.element("div").classes("zona-formula").props('aria-live="polite"')

    dibujar()


async def inicio(q: str = "") -> None:
    """La página principal. Se registra en `registrar()`."""
    ui.dark_mode(None)  # sigue el modo claro/oscuro del dispositivo
    ui.add_head_html(HEAD_HTML)
    ui.add_css(CSS)

    est = Estado()
    vista: dict = {"lista": None, "siguiente": None}   # elementos que `siguiente()` necesita tocar

    # ----- dibujo ---------------------------------------------------------
    def mostrar_final(sol: Solucion) -> None:
        # tabindex=-1: se puede enfocar por código, para que el lector de pantalla lo anuncie
        _html(_final_html(sol)).classes("final").props('tabindex="-1"')

    def pintar() -> None:
        """Dibuja todo el resultado desde cero (resultado nuevo o cambio de modo)."""
        zona.clear()
        vista["lista"] = vista["siguiente"] = None
        with zona:
            if est.error:
                _html(
                    '<strong>No se pudo resolver</strong>'
                    f'<p>{escape(est.error)}</p>'
                ).classes("error").props('role="alert"')
                return
            sol = est.sol
            if sol is None:
                return
            _html(mathml(sol.latex_inicial, sol.expresion_inicial)).classes("ejercicio")
            if sol.pasos:
                with ui.element("ol").classes("pasos") as lista:
                    for p in sol.pasos[:est.visibles]:
                        _html(_paso_html(p), tag="li").classes("paso")
                vista["lista"] = lista
            else:
                _html('<p class="paso-texto">Ya es un número: no hay nada que resolver.</p>').classes("ejercicio")
            if est.visibles < len(sol.pasos):
                vista["siguiente"] = (
                    ui.button("Siguiente paso", on_click=siguiente, color=None)
                    .classes("siguiente boton-resolver").props("unelevated no-caps")
                )
            else:
                mostrar_final(sol)

    @ui.refreshable
    def motor_live() -> None:
        sol = est.sol
        if est.resolviendo:
            estado = '<div class="motor-espera"><strong>Resolviendo ejercicio…</strong><small>El despachador está seleccionando el solucionador.</small></div>'
            caja = '<div class="motor-resumen"><span class="motor-tipo">Análisis en curso</span><small>Esperando el resultado del motor.</small></div>'
            linea = escape((entrada.value or "").strip())
        elif sol is not None:
            tipo, motor = _tipo_motor(sol)
            pasos = f"{len(sol.pasos)} paso{'s' if len(sol.pasos) != 1 else ''}"
            etapa = "Resultado listo"
            if est.visibles < len(sol.pasos):
                etapa = f"Mostrando {est.visibles} de {len(sol.pasos)} pasos"
            detalle = []
            if sol.nota:
                detalle.append(sol.nota)
            if sol.resultado_decimal:
                signo = "=" if sol.decimal_exacto else "≈"
                detalle.append(f"Decimal {signo} {sol.resultado_decimal}")
            detalles = "".join(f'<small class="motor-detalle">{escape(item)}</small>' for item in detalle)
            estado = (
                '<div class="verificado"><span>✓</span><div><strong>Comprobación completada</strong>'
                f'<small>{escape(etapa)} · {escape(pasos)}</small>{detalles}</div></div>'
            )
            caja = (f'<div class="motor-resumen"><span class="motor-tipo">{escape(tipo)}</span>'
                    f'<span class="motor-pasos">{escape(pasos)}</span><small>{escape(motor)}</small></div>')
            linea = f"{escape(sol.entrada)} → {escape(sol.expresion_inicial)}"
        elif est.error:
            warning = est.tipo_error == "entrada"
            color = "warning" if warning else "error"
            estado = (f'<div class="motor-estado {color}"><strong>{"Revisa la entrada" if warning else "Error al resolver"}</strong>'
                      f'<small>{escape(est.error)}</small></div>')
            caja = '<div class="motor-resumen"><span class="motor-tipo">Sin solución</span><small>Corrige el ejercicio e inténtalo de nuevo.</small></div>'
            linea = "Entrada no interpretada" if warning else "Ejercicio no resuelto"
        else:
            estado = ('<div class="motor-espera"><strong>En espera de un ejercicio</strong>'
                      '<small>Al resolver, aquí verás el tipo, los pasos y el motor.</small></div>')
            caja = '<div class="motor-resumen"><span class="motor-tipo">Listo para resolver</span><small>Python · motor simbólico según el ejercicio</small></div>'
            linea = "ejercicio → expresión → procedimiento → verificación"
        _html(
            '<div class="codigo-card motor-live-card"><div class="codigo-cabecera"><span></span><span></span><span></span><small>actividad del motor</small></div>'
            f'<div class="motor-cadena">{linea}</div>{caja}{estado}</div>'
        )

    @ui.refreshable
    def guia_live() -> None:
        tiene_sol = est.sol is not None
        final_visible = tiene_sol and est.visibles >= len(est.sol.pasos)
        fase = "1" if not tiene_sol else ("3" if final_visible else "2")
        with ui.row().classes("guia-paso guia-tarjeta items-start no-wrap w-full cursor-pointer" +
                              (" activa" if fase == "1" else "")).on("click", enfocar_planteamiento):
            ui.label("01").classes("guia-num shrink-0")
            with ui.column().classes("guia-texto gap-0"):
                ui.label("Plantea").classes("guia-titulo")
                ui.label("Escribe o elige un ejercicio.").classes("guia-descripcion")
        with ui.row().classes("guia-paso guia-tarjeta items-start no-wrap w-full" +
                              (" deshabilitada cursor-default" if not tiene_sol else " cursor-pointer") +
                              (" activa" if fase == "2" else "")).on("click", ir_a_observar):
            ui.label("02").classes("guia-num shrink-0")
            with ui.column().classes("guia-texto gap-0"):
                ui.label("Observa").classes("guia-titulo")
                ui.label("Sigue cada operación explicada.").classes("guia-descripcion")
        with ui.row().classes("guia-paso guia-tarjeta items-start no-wrap w-full" +
                              (" deshabilitada cursor-default" if not tiene_sol else " cursor-pointer") +
                              (" completada" if final_visible else "")).on("click", ir_a_comprobar):
            ui.label("03").classes("guia-num shrink-0")
            with ui.column().classes("guia-texto gap-0"):
                ui.label("Comprueba").classes("guia-titulo")
                ui.label("Ve al resultado verificado.").classes("guia-descripcion")
        with ui.element("div").classes("historial-rapido"):
            _html('<div class="historial-titulo">HISTORIAL DE ESTA SESIÓN</div>')
            if est.historial:
                for item in est.historial[:4]:
                    ui.button(f'{item["entrada"]}  →  {item["resultado"]}',
                              on_click=lambda t=item["entrada"]: usar_ejemplo(t), color=None) \
                        .classes("historial-item").props("flat no-caps").tooltip("Volver a resolver este ejercicio")
            else:
                ui.button("Probar este ejemplo · x + 3 = 8", on_click=lambda: usar_ejemplo("x + 3 = 8"), color=None) \
                    .classes("historial-demo").props("flat no-caps")
                _html('<small class="historial-ayuda">Resuelve un ejercicio y aparecerá aquí para repetirlo.</small>')

    def bajar_al_resultado() -> None:
        """En el celular el resultado queda más abajo que la pantalla: bajamos hasta él."""
        _js("setTimeout(() => { const z = document.querySelector('.zona'); if (z) z.scrollIntoView({"
            f"behavior: {_MOVIMIENTO}, block: 'start'}}); }}, 80);")

    # ----- acciones -------------------------------------------------------
    async def resolver_ejercicio() -> None:
        texto = (entrada.value or "").strip()[:MAX_CARACTERES]
        if not texto:
            est.sol, est.error, est.tipo_error = None, "Escribe un ejercicio para empezar, por ejemplo 1/2 + 1/3.", "entrada"
            est.resolviendo = False
            pintar()
            motor_live.refresh()
            guia_live.refresh()
            return
        est.error = est.tipo_error = None
        est.sol = None
        est.resolviendo = True
        pintar()
        motor_live.refresh()
        guia_live.refresh()
        try:
            # En un hilo y con tiempo máximo: un ejercicio pesado no congela la página de los demás usuarios.
            funcion = resolver_columnas if est.columnas else resolver_auto
            sol = await asyncio.wait_for(asyncio.to_thread(funcion, texto), timeout=TIEMPO_MAXIMO)
        except asyncio.TimeoutError:
            log.warning("Tardó más de %s s: %r", TIEMPO_MAXIMO, texto)
            est.sol = None
            est.tipo_error = "motor"
            est.error = ("Este ejercicio tarda demasiado en resolverse. Prueba con uno más sencillo "
                         "(menos términos o exponentes más pequeños).")
        except ErrorDeEntrada as e:
            est.sol = None
            est.tipo_error = "entrada"
            est.error = _mensaje_columnas(texto, e) if est.columnas else str(e)
        except ErrorMotor as e:
            est.sol = None
            est.tipo_error = "motor"
            est.error = _mensaje_columnas(texto, e) if est.columnas else str(e)
        except Exception:  # noqa: BLE001 - nunca mostrar trazas técnicas al estudiante
            log.exception("Error inesperado al resolver %r", texto)
            est.sol = None
            est.tipo_error = "motor"
            est.error = "Algo salió mal con esta expresión. Revísala e inténtalo de nuevo."
        else:
            est.sol, est.error = sol, None
            est.tipo_error = None
            est.visibles = 1 if est.uno_a_uno and sol.pasos else len(sol.pasos)
            est.historial = [item for item in est.historial if item["entrada"] != texto]
            est.historial.insert(0, {"entrada": texto, "resultado": sol.resultado})
            del est.historial[4:]
        est.resolviendo = False
        pintar()
        motor_live.refresh()
        guia_live.refresh()
        bajar_al_resultado()

    def siguiente() -> None:
        """Muestra un paso más SIN redibujar todo: el foco y la animación se quedan donde están."""
        sol = est.sol
        if sol is None or vista["lista"] is None or est.visibles >= len(sol.pasos):
            return
        paso = sol.pasos[est.visibles]
        est.visibles += 1
        with vista["lista"]:
            _html(_paso_html(paso), tag="li").classes("paso")
        if est.visibles >= len(sol.pasos):
            vista["siguiente"].delete()
            vista["siguiente"] = None
            with zona:
                mostrar_final(sol)
            _js(f"const f = document.querySelector('.final'); if (f) {{ f.focus({{preventScroll: true}}); "
                f"f.scrollIntoView({{behavior: {_MOVIMIENTO}, block: 'nearest'}}); }}")
        else:
            _js("const p = document.querySelector('.pasos > li:last-child'); if (p) "
                f"p.scrollIntoView({{behavior: {_MOVIMIENTO}, block: 'nearest'}});")
        motor_live.refresh()
        guia_live.refresh()

    def cambiar_modo(e) -> None:
        est.uno_a_uno = bool(e.value)
        if est.sol is not None:
            est.visibles = 1 if e.value and est.sol.pasos else len(est.sol.pasos)
            pintar()
            motor_live.refresh()
            guia_live.refresh()

    async def cambiar_columnas(e) -> None:
        nuevo = bool(e.value)
        if nuevo == est.columnas:      # lo cambió `usar_ejemplo`, que ya resuelve por su cuenta
            return
        est.columnas = nuevo
        if (entrada.value or "").strip():
            await resolver_ejercicio()

    async def usar_ejemplo(texto: str, *, columnas: bool = False) -> None:
        """Pone el ejemplo en el campo, ajusta el modo (normal o columnas) y resuelve UNA sola vez."""
        entrada.value = texto
        est.columnas = columnas
        modo_columnas.value = columnas   # `cambiar_columnas` ve que ya coincide y no vuelve a resolver
        await resolver_ejercicio()

    def al_editar(e) -> None:
        """Al cambiar el campo, invalida la solución anterior y vuelve a la fase Plantea."""
        if est.sol is not None or est.error is not None:
            est.sol = est.error = est.tipo_error = None
            est.visibles = 0
            est.resolviendo = False
            pintar()
            motor_live.refresh()
            guia_live.refresh()

    def enfocar_planteamiento() -> None:
        _js("const i = document.querySelector('.entrada input'); if (i) { i.focus(); i.scrollIntoView({behavior: 'smooth', block: 'center'}); }")

    async def ir_a_observar() -> None:
        if est.sol is None:
            if (entrada.value or "").strip():
                est.uno_a_uno = True
                modo_uno.value = True
                await resolver_ejercicio()
            else:
                enfocar_planteamiento()
            return
        if est.sol.pasos and est.visibles >= len(est.sol.pasos):
            est.uno_a_uno = True
            modo_uno.value = True
            est.visibles = 1
            pintar()
            motor_live.refresh()
            guia_live.refresh()
        _js("const p = document.querySelector('.pasos'); if (p) p.scrollIntoView({behavior: 'smooth', block: 'start'});")

    def ir_a_comprobar() -> None:
        if est.sol is None:
            enfocar_planteamiento()
            ui.notify("Resuelve un ejercicio para ver su comprobación.", type="info")
            return
        if est.visibles < len(est.sol.pasos):
            est.visibles = len(est.sol.pasos)
            pintar()
            motor_live.refresh()
            guia_live.refresh()
        _js("const f = document.querySelector('.final'); if (f) f.scrollIntoView({behavior: 'smooth', block: 'center'});")

    def ir_a_algebra() -> None:
        pestanas.value = pestana_calculadora
        elegir_nivel("Álgebra")

    def ir_a_formulas() -> None:
        pestanas.value = pestana_formulas

    def avisar_calculo() -> None:
        ui.notify("En una próxima etapa llegarán los módulos de derivadas e integrales.", type="info", timeout=3500)

    def pulsar(tecla: str) -> None:
        actual = entrada.value or ""
        if tecla == "C":
            entrada.value = ""
        elif tecla == "⌫":
            entrada.value = actual[:-1]
        elif tecla == "de":
            entrada.value = actual.rstrip() + " de "
        elif tecla == "espacio":
            entrada.value = actual + " "
        elif tecla in COMANDOS:
            # «factorizar x² − 9»: el comando va al principio; si ya había otro, se cambia
            resto = separar_comando(actual)[1] if tiene_comando(actual) else actual.strip()
            entrada.value = f"{tecla} {resto}" if resto else f"{tecla} "
        elif tecla == "despejar":
            # «despejar t en v = d/t»; si ya escribió la fórmula, queda «v = d/t, despejar »
            entrada.value = (actual.rstrip() + ", " if actual.strip() else "") + "despejar "
        else:
            entrada.value = actual + tecla

    # ----- pantalla -------------------------------------------------------
    teclas_nivel: list = []     # (tecla, nivel mínimo): se ocultan según el nivel elegido
    filas_nivel: list = []      # (fila de ejemplos, nivel mínimo)

    botones_nivel: dict = {}

    def elegir_nivel(nombre: str) -> None:
        tope = NIVELES[nombre]
        for elemento, nivel in teclas_nivel + filas_nivel:
            elemento.set_visibility(nivel <= tope)
        for n, boton in botones_nivel.items():
            if n == nombre:
                boton.classes(add="activo")
            else:
                boton.classes(remove="activo")

    with ui.element("main").classes("hoja"):
        _html(
            '<header class="marca-cabecera">'
            '<div class="marca-simbolo" aria-hidden="true"><span>∑</span><i>✓</i></div>'
            '<div class="marca-texto"><h1 class="titulo"><span>MATRIX</span><b>OPS</b></h1>'
            '<p class="subtitulo">Tu tutor matemático paso a paso</p>'
            '<p class="lema">COMPRENDE <i>•</i> APRENDE <i>•</i> RESUELVE</p></div>'
            '<div class="marca-sello"><span class="sello-punto"></span>MATEMÁTICAS CON PROCEDIMIENTO</div>'
            '</header>'
        )

        with ui.element("div").classes("workspace-grid"):
            with ui.element("aside").classes("panel-lateral panel-motor"):
                _html(
                    '<div class="panel-kicker">MOTOR MATEMÁTICO</div>'
                    '<h2>Del ejercicio a la comprensión</h2>'
                    '<p class="panel-copy">Actividad real del despachador y los solucionadores.</p>'
                    '<div class="motor-badges"><span>Python</span><span>SymPy</span></div>'
                )
                motor_live()
                _html('<h3>Módulos</h3>')
                with ui.row().classes("modulos modulos-botones flex-wrap gap-2"):
                    (ui.label("Álgebra").classes("modulo-chip cursor-pointer")
                     .props('role="button" tabindex="0"').on("click", ir_a_algebra)
                     .on("keydown.enter", ir_a_algebra).on("keydown.space", ir_a_algebra))
                    (ui.label("Física · fórmulas").classes("modulo-chip cursor-pointer")
                     .props('role="button" tabindex="0"').on("click", ir_a_formulas)
                     .on("keydown.enter", ir_a_formulas).on("keydown.space", ir_a_formulas))
                    (ui.label("Cálculo · próximamente").classes("modulo-chip futuro cursor-pointer")
                     .props('role="button" tabindex="0"').on("click", avisar_calculo)
                     .on("keydown.enter", avisar_calculo).on("keydown.space", avisar_calculo))
                _html('<h3>Estructura de una expresión</h3>')
                with ui.element("div").classes("arbol arbol-clickable cursor-pointer").props(
                        'role="button" tabindex="0" aria-label="Ejemplo interactivo de la expresión (2 + 3) por 4"') \
                        .on("click", lambda: usar_ejemplo("(2 + 3) * 4")):
                    _html(
                        '<span class="arbol-prompt">Pulsa para probar</span>'
                        '<svg class="arbol-svg" viewBox="0 0 220 94" role="img" aria-label="Árbol de la expresión (2 + 3) por 4">'
                        '<g class="arbol-lineas"><path d="M110 26 V34 M55 34 H165 M55 34 V43 M165 34 V43 M55 64 V72 M40 72 H70 M40 72 V80 M70 72 V80 M165 64 V80"/></g>'
                        '<rect class="arbol-caja raiz" x="98" y="3" width="24" height="23" rx="5"/><text class="arbol-operador" x="110" y="20" text-anchor="middle">×</text>'
                        '<rect class="arbol-caja" x="18" y="43" width="74" height="21" rx="5"/><text class="arbol-expresion" x="55" y="57" text-anchor="middle">(2 + 3)</text>'
                        '<rect class="arbol-caja" x="128" y="43" width="74" height="21" rx="5"/><text class="arbol-expresion" x="165" y="57" text-anchor="middle">4</text>'
                        '<text class="arbol-hoja" x="40" y="91" text-anchor="middle">2</text><text class="arbol-hoja" x="70" y="91" text-anchor="middle">3</text><text class="arbol-hoja" x="165" y="91" text-anchor="middle">4</text></svg>'
                        '<span class="arbol-cta">Probar: (2 + 3) × 4</span>'
                    ).classes("arbol-content")

            with ui.element("section").classes("panel-central"):
                _html('<div class="centro-encabezado"><div><div class="panel-kicker">ÁREA DE RESOLUCIÓN</div>'
                      '<h2>Aprende resolviendo</h2></div><span class="estado-en-linea"><i></i> Motor listo</span></div>')

                with ui.tabs().classes("pestanas").props("align=left no-caps") as pestanas:
                    pestana_calculadora = ui.tab("Calculadora").mark("pestana-calculadora")
                    pestana_formulas = ui.tab("Fórmulas").mark("pestana-formulas")
                with ui.tab_panels(pestanas, value=pestana_calculadora).classes("paneles"):
                    with ui.tab_panel(pestana_calculadora):

                        entrada = ui.input(label="Tu ejercicio", placeholder="Ej.: 2 + 3 × (4 − 1)^2").classes("entrada")
                        entrada.props(f'borderless stack-label autocomplete="off" inputmode="text" maxlength="{MAX_CARACTERES}"')
                        entrada.on("keydown.enter", resolver_ejercicio)
                        entrada.on_value_change(al_editar)

                        with ui.element("div").classes("fila-accion"):
                            ui.button("Resolver", on_click=resolver_ejercicio, color=None).classes("boton-resolver").props("unelevated no-caps")
                            modo_uno = ui.switch("Un paso a la vez", on_change=cambiar_modo).mark("un-paso")
                            modo_columnas = ui.switch("En columnas (a mano)", on_change=cambiar_columnas)
                            modo_columnas.mark("modo-columnas")

                        with ui.element("div").classes("fila-nivel"):
                            ui.label("Nivel:")
                            with ui.element("div").classes("niveles"):
                                for nombre in NIVELES:
                                    botones_nivel[nombre] = (
                                        ui.button(nombre, on_click=lambda n=nombre: elegir_nivel(n), color=None)
                                        .classes("nivel" + (" activo" if nombre == "Todo" else "")).props("flat no-caps")
                                        .mark(f"nivel-{nombre}"))

                        with ui.element("div").classes("teclado"):
                            for texto, es_op in TECLAS:
                                boton = ui.button(texto, on_click=lambda t=texto: pulsar(t), color=None).props("flat no-caps")
                                boton.classes("tecla op" if es_op else "tecla").mark(f"tecla-{texto}")
                                teclas_nivel.append((boton, NIVEL_DE_TECLA.get(texto, 1)))
                                if texto in ETIQUETAS_TECLAS:
                                    boton.props(f'aria-label="{ETIQUETAS_TECLAS[texto]}"')
                            for comando in ("simplificar",):
                                b = ui.button(comando, on_click=lambda c=comando: pulsar(c), color=None).props("flat no-caps")
                                b.classes("tecla tecla-ancha op").mark(f"tecla-{comando}")
                                teclas_nivel.append((b, NIVEL_DE_TECLA[comando]))
                            ancho = ui.button("espacio", on_click=lambda: pulsar("espacio"), color=None).props("flat no-caps")
                            ancho.classes("tecla tecla-ancha").mark("tecla-espacio")
                            teclas_nivel.append((ancho, 1))
                            despejar = ui.button("despejar", on_click=lambda: pulsar("despejar"), color=None).props("flat no-caps")
                            despejar.classes("tecla tecla-ancha op").mark("tecla-despejar")
                            teclas_nivel.append((despejar, 2))
                            for comando in ("factorizar", "desarrollar"):
                                b = ui.button(comando, on_click=lambda c=comando: pulsar(c), color=None).props("flat no-caps")
                                b.classes("tecla tecla-ancha op").mark(f"tecla-{comando}")
                                teclas_nivel.append((b, NIVEL_DE_TECLA[comando]))

                        filas_nivel.append((_fila_ejemplos("Prueba con:", EJEMPLOS, usar_ejemplo), 1))
                        filas_nivel.append((_fila_ejemplos("Ecuaciones:", EJEMPLOS_ECUACIONES, usar_ejemplo), 2))
                        filas_nivel.append((_fila_ejemplos("Desigualdades:", EJEMPLOS_DESIGUALDADES, usar_ejemplo), 2))
                        filas_nivel.append((_fila_ejemplos("Fórmulas:", EJEMPLOS_FORMULAS, usar_ejemplo), 2))
                        filas_nivel.append((_fila_ejemplos("Álgebra:", EJEMPLOS_ALGEBRA, usar_ejemplo), 3))
                        filas_nivel.append((_fila_ejemplos("Factorizar:", EJEMPLOS_FACTORIZAR, usar_ejemplo), 3))
                        filas_nivel.append((_fila_ejemplos("Fracciones:", EJEMPLOS_FRACCIONES, usar_ejemplo), 3))
                        filas_nivel.append((_fila_ejemplos("Raíces:", EJEMPLOS_RAICES, usar_ejemplo), 3))
                        filas_nivel.append((_fila_ejemplos("A mano:", EJEMPLOS_COLUMNAS, lambda t: usar_ejemplo(t, columnas=True)), 1))

                        # aria-live: el lector de pantalla anuncia el resultado cuando aparece
                        zona = ui.element("div").classes("zona").props('aria-live="polite"')
                    with ui.tab_panel(pestana_formulas):
                        _formulario()

            with ui.element("aside").classes("panel-lateral panel-guia"):
                _html(
                    '<div class="panel-kicker">GUÍA DE APRENDIZAJE</div><h2>Entiende cada paso</h2>'
                    '<p class="panel-copy">Avanza con el ejercicio: plantea, observa y comprueba.</p>'
                )
                guia_live()

        with ui.element("section").classes("recursos-estudio"):
            _html('<div class="recursos-titulo"><div class="panel-kicker">RINCÓN DE ESTUDIO</div>'
                  '<h2>Aprender también es practicar</h2></div>'
                  '<div class="recurso"><span class="recurso-icono">▤</span><div><strong>Álgebra de Baldor</strong><small>Una referencia clásica para practicar álgebra.</small></div></div>'
                  '<div class="recurso"><span class="recurso-icono">✎</span><div><strong>Cuaderno de fórmulas</strong><small>Escribe, compara y conserva tus procedimientos.</small></div></div>'
                  '<div class="recurso"><span class="recurso-icono">⌁</span><div><strong>Física básica</strong><small>Explora fórmulas y despeja sus variables.</small></div></div>'
                  '<div class="frase-estudio">“Estudia, aprende, logra más.”</div>')

    if q:
        entrada.value = q[:MAX_CARACTERES]
        await resolver_ejercicio()


async def _calentar() -> None:
    """Carga SymPy y el motor al arrancar, para que la primera persona no espere ~0,5 s de más."""
    try:
        for ejemplo in ("despejar t en v = d/t", "(x + 1)²", "√12"):
            await asyncio.to_thread(resolver_auto, ejemplo)
    except Exception:  # noqa: BLE001 - calentar es opcional: si falla, el primer ejercicio simplemente tarda más
        log.exception("No se pudo calentar el motor")


def registrar() -> None:
    """Conecta las páginas con sus direcciones. Lo llama main.py (y las pruebas)."""
    ui.page("/", title=TITULO)(inicio)
    app.on_startup(_calentar)

    @app.get("/salud")
    def salud() -> PlainTextResponse:
        """Dirección que consulta Render (o cualquier servicio) para saber si la aplicación está viva."""
        return PlainTextResponse("ok")
