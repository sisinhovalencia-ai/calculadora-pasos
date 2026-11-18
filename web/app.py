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
from dataclasses import dataclass
from html import escape

from nicegui import app, ui
from starlette.responses import PlainTextResponse

from motor import ErrorMotor, Solucion, resolver_columnas
from motor.algebra import separar_comando, tiene_comando
from motor import resolver_ejercicio as resolver_auto   # (la de la página se llama igual: ver más abajo)

from .estilos import CSS, HEAD_HTML
from .formulas import mathml, resaltar

log = logging.getLogger("web")

TITULO = "Calculadora paso a paso"
MAX_CARACTERES = 200   # un ejercicio escolar nunca es más largo; evita entradas enormes

EJEMPLOS = ["2 + 3 × (4 − 1)^2", "1/2 + 1/3", "4/6 + 1/3", "3 1/2 + 2 3/4",
            "20% de 150", "√(16 + 9)", "−3^2", "0.1 + 0.2"]

EJEMPLOS_ECUACIONES = ["2x + 3 = 11", "3x − 5 = 2x + 7", "2(x + 3) = 14", "x/2 + 1 = 5"]
EJEMPLOS_DESIGUALDADES = ["2x + 3 < 11", "−2x + 1 ≥ 7", "3(x − 1) > 2x + 4", "x/2 − 1 ≤ 3"]
EJEMPLOS_FORMULAS = ["despejar t en v = d/t", "despejar h en A = b·h/2", "despejar w en P = 2l + 2w",
                     "despejar C en F = 9C/5 + 32", "despejar a en F = ma"]
EJEMPLOS_ALGEBRA = ["(x + 3)²", "(2x + 3)(2x − 3)", "(x + 2)(x + 5)", "(3x² + 2x) − (x² − 5x)"]
EJEMPLOS_FACTORIZAR = ["factorizar x² − 9", "factorizar x² + 5x + 6", "factorizar 2x² + 7x + 3",
                       "factorizar ax + ay + bx + by", "factorizar x³ − 8"]
EJEMPLOS_FRACCIONES = ["(x² − 9)/(x − 3)", "1/(x − 1) + 1/(x + 1)", "(x² − 4)/(x + 1) · (x + 1)/(x − 2)"]
EJEMPLOS_RAICES = ["√12", "√50 + √8", "1/√2", "3/(2 + √5)", "8^(1/3)"]
COMANDOS = ("factorizar", "desarrollar", "simplificar")
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


def _fila_ejemplos(etiqueta: str, ejemplos: list[str], al_pulsar) -> None:
    """Una fila de botones de ejemplo con su rótulo («Prueba con:», «Ecuaciones:»...)."""
    with ui.element("div").classes("ejemplos"):
        ui.label(etiqueta)
        for ej in ejemplos:
            ui.button(ej, on_click=lambda t=ej: al_pulsar(t), color=None).classes("ejemplo").props("flat no-caps")


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

    def bajar_al_resultado() -> None:
        """En el celular el resultado queda más abajo que la pantalla: bajamos hasta él."""
        _js("setTimeout(() => { const z = document.querySelector('.zona'); if (z) z.scrollIntoView({"
            f"behavior: {_MOVIMIENTO}, block: 'start'}}); }}, 80);")

    # ----- acciones -------------------------------------------------------
    async def resolver_ejercicio() -> None:
        texto = (entrada.value or "").strip()[:MAX_CARACTERES]
        if not texto:
            est.sol, est.error = None, "Escribe un ejercicio para empezar, por ejemplo 1/2 + 1/3."
            pintar()
            return
        try:
            # En un hilo y con tiempo máximo: un ejercicio pesado no congela la página de los demás usuarios.
            funcion = resolver_columnas if est.columnas else resolver_auto
            sol = await asyncio.wait_for(asyncio.to_thread(funcion, texto), timeout=TIEMPO_MAXIMO)
        except asyncio.TimeoutError:
            log.warning("Tardó más de %s s: %r", TIEMPO_MAXIMO, texto)
            est.sol = None
            est.error = ("Este ejercicio tarda demasiado en resolverse. Prueba con uno más sencillo "
                         "(menos términos o exponentes más pequeños).")
        except ErrorMotor as e:
            est.sol = None
            est.error = _mensaje_columnas(texto, e) if est.columnas else str(e)
        except Exception:  # noqa: BLE001 - nunca mostrar trazas técnicas al estudiante
            log.exception("Error inesperado al resolver %r", texto)
            est.sol = None
            est.error = "Algo salió mal con esta expresión. Revísala e inténtalo de nuevo."
        else:
            est.sol, est.error = sol, None
            est.visibles = 1 if est.uno_a_uno and sol.pasos else len(sol.pasos)
        pintar()
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

    def cambiar_modo(e) -> None:
        est.uno_a_uno = bool(e.value)
        if est.sol is not None:
            est.visibles = 1 if e.value and est.sol.pasos else len(est.sol.pasos)
            pintar()

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
    with ui.element("main").classes("hoja"):
        _html(
            f'<h1 class="titulo">{TITULO}</h1>'
            '<p class="subtitulo">Escribe una operación y mira cómo se resuelve, un paso a la vez.</p>'
        )

        entrada = ui.input(label="Tu ejercicio", placeholder="Ej.: 2 + 3 × (4 − 1)^2").classes("entrada")
        entrada.props(f'borderless stack-label autocomplete="off" inputmode="text" maxlength="{MAX_CARACTERES}"')
        entrada.on("keydown.enter", resolver_ejercicio)

        with ui.element("div").classes("fila-accion"):
            ui.button("Resolver", on_click=resolver_ejercicio, color=None).classes("boton-resolver").props("unelevated no-caps")
            ui.switch("Un paso a la vez", on_change=cambiar_modo).mark("un-paso")
            modo_columnas = ui.switch("En columnas (a mano)", on_change=cambiar_columnas)
            modo_columnas.mark("modo-columnas")

        with ui.element("div").classes("teclado"):
            for texto, es_op in TECLAS:
                boton = ui.button(texto, on_click=lambda t=texto: pulsar(t), color=None).props("flat no-caps")
                boton.classes("tecla op" if es_op else "tecla").mark(f"tecla-{texto}")
                if texto in ETIQUETAS_TECLAS:
                    boton.props(f'aria-label="{ETIQUETAS_TECLAS[texto]}"')
            for comando in ("simplificar",):
                b = ui.button(comando, on_click=lambda c=comando: pulsar(c), color=None).props("flat no-caps")
                b.classes("tecla tecla-ancha op").mark(f"tecla-{comando}")
            ancho = ui.button("espacio", on_click=lambda: pulsar("espacio"), color=None).props("flat no-caps")
            ancho.classes("tecla tecla-ancha").mark("tecla-espacio")
            despejar = ui.button("despejar", on_click=lambda: pulsar("despejar"), color=None).props("flat no-caps")
            despejar.classes("tecla tecla-ancha op").mark("tecla-despejar")
            for comando in ("factorizar", "desarrollar"):
                b = ui.button(comando, on_click=lambda c=comando: pulsar(c), color=None).props("flat no-caps")
                b.classes("tecla tecla-ancha op").mark(f"tecla-{comando}")

        _fila_ejemplos("Prueba con:", EJEMPLOS, usar_ejemplo)
        _fila_ejemplos("Ecuaciones:", EJEMPLOS_ECUACIONES, usar_ejemplo)
        _fila_ejemplos("Desigualdades:", EJEMPLOS_DESIGUALDADES, usar_ejemplo)
        _fila_ejemplos("Fórmulas:", EJEMPLOS_FORMULAS, usar_ejemplo)
        _fila_ejemplos("Álgebra:", EJEMPLOS_ALGEBRA, usar_ejemplo)
        _fila_ejemplos("Factorizar:", EJEMPLOS_FACTORIZAR, usar_ejemplo)
        _fila_ejemplos("Fracciones:", EJEMPLOS_FRACCIONES, usar_ejemplo)
        _fila_ejemplos("Raíces:", EJEMPLOS_RAICES, usar_ejemplo)
        _fila_ejemplos("A mano:", EJEMPLOS_COLUMNAS, lambda t: usar_ejemplo(t, columnas=True))

        # aria-live: el lector de pantalla anuncia el resultado cuando aparece
        zona = ui.element("div").classes("zona").props('aria-live="polite"')

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