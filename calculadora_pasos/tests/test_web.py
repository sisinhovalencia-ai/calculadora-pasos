"""Pruebas de la interfaz web.

Simulan a una persona usando la página (escribir, pulsar botones) sin abrir un
navegador. La apariencia (colores, tamaños) se revisa a ojo con capturas; aquí
se comprueba que la pantalla FUNCIONA y que nunca muestra errores técnicos.
"""

import sympy  # noqa: F401  (se carga antes: su primera carga tarda ~0,5 s y el simulador no espera tanto)
from nicegui import ui
from nicegui.testing import User

import web.app  # noqa: F401  (al importarlo se registra la página "/")
from web.formulas import mathml, resaltar


async def test_resuelve_con_enter(user: User):
    await user.open("/")
    user.find(ui.input).type("2 + 3 × 4").trigger("keydown.enter")
    await user.should_see("Resultado")
    await user.should_see("Multiplicamos")
    await user.should_see("¿Por qué ahora?")


async def test_boton_resolver(user: User):
    await user.open("/")
    user.find(ui.input).type("10 − 4")
    user.find("Resolver").click()
    await user.should_see("Restamos")


async def test_ejemplo_se_resuelve_solo(user: User):
    await user.open("/")
    user.find("1/2 + 1/3").click()
    await user.should_see("denominador común")


async def test_error_se_muestra_en_espanol(user: User):
    await user.open("/")
    user.find(ui.input).type("5 / 0").trigger("keydown.enter")
    await user.should_see("No se puede dividir entre cero.")
    await user.should_not_see("Traceback")


async def test_campo_vacio_da_mensaje_claro(user: User):
    await user.open("/")
    user.find("Resolver").click()
    await user.should_see("Escribe un ejercicio para empezar")


async def test_ejercicio_por_enlace(user: User):
    await user.open("/?q=2%2B2")
    await user.should_see("Resultado")


async def test_un_paso_a_la_vez(user: User):
    await user.open("/")
    user.find(marker="un-paso").click()
    user.find(ui.input).type("2 + 3 × 4").trigger("keydown.enter")
    await user.should_see("Siguiente paso")
    await user.should_not_see("Resultado")
    user.find("Siguiente paso").click()
    await user.should_see("Resultado")
    await user.should_not_see("Siguiente paso")


async def test_teclado_escribe_y_borra(user: User):
    await user.open("/")
    campo = user.find(ui.input).elements.pop()
    for tecla in ["7", "×", "2"]:
        user.find(marker=f"tecla-{tecla}").click()
    assert campo.value == "7×2"
    user.find(marker="tecla-⌫").click()
    assert campo.value == "7×"
    user.find(marker="tecla-C").click()
    assert campo.value == ""


async def test_teclas_de_porcentaje_y_raiz(user: User):
    await user.open("/")
    campo = user.find(ui.input).elements.pop()
    for tecla in ["2", "0", "%", "de", "5", "0"]:
        user.find(marker=f"tecla-{tecla}").click()
    assert campo.value == "20% de 50"
    user.find("Resolver").click()
    await user.should_see("de cada 100")
    user.find(marker="tecla-C").click()
    user.find(marker="tecla-√").click()
    user.find(marker="tecla-4").click()
    user.find(marker="tecla-9").click()
    assert campo.value == "√49"


async def test_numero_mixto_y_raiz_por_enlace(user: User):
    await user.open("/?q=3 1/2 %2B √49")
    await user.should_see("número mixto")
    await user.should_see("Resultado")


async def test_modo_en_columnas(user: User):
    await user.open("/")
    user.find(marker="modo-columnas").click()
    user.find(ui.input).type("4567 + 289").trigger("keydown.enter")
    await user.should_see("llevamos 1")
    await user.should_see("Resultado")


async def test_modo_en_columnas_pide_una_sola_operacion(user: User):
    await user.open("/")
    user.find(marker="modo-columnas").click()
    user.find(ui.input).type("2 + 3 × 4").trigger("keydown.enter")
    await user.should_see("una sola operación")


async def test_ejemplo_a_mano_activa_el_modo_y_resuelve(user: User):
    await user.open("/")
    user.find("7845 ÷ 12").click()
    await user.should_see("casita")
    await user.should_see("cociente 653 y residuo 9")


async def test_ecuacion_desde_la_pantalla(user: User):
    await user.open("/")
    user.find(ui.input).type("2x + 3 = 11").trigger("keydown.enter")
    await user.should_see("restamos 3 en ambos lados")
    await user.should_see("Resultado")


async def test_ejemplo_de_ecuacion(user: User):
    await user.open("/")
    user.find("3x − 5 = 2x + 7").click()
    await user.should_see("restamos 2x en ambos lados")


async def test_teclas_de_raices_especiales_y_ecuaciones(user: User):
    await user.open("/")
    campo = user.find(ui.input).elements.pop()
    for tecla in ["∛", "2", "7"]:
        user.find(marker=f"tecla-{tecla}").click()
    assert campo.value == "∛27"
    user.find("Resolver").click()
    await user.should_see("raíz cúbica de 27 es 3")
    user.find(marker="tecla-C").click()
    for tecla in ["2", "x", "=", "8"]:
        user.find(marker=f"tecla-{tecla}").click()
    assert campo.value == "2x=8"
    user.find(marker="tecla-C").click()
    for tecla in ["3", "espacio", "1", "/", "2"]:
        user.find(marker=f"tecla-{tecla}").click()
    assert campo.value == "3 1/2"
    user.find(marker="tecla-C").click()
    user.find(marker="tecla-∜").click()
    assert campo.value == "∜"


async def test_raiz_cubica_con_modo_columnas_explica_que_hay_que_apagarlo(user: User):
    """El caso real: ∛125 con «En columnas (a mano)» encendido."""
    await user.open("/")
    user.find(marker="modo-columnas").click()
    user.find(ui.input).type("∛125").trigger("keydown.enter")
    await user.should_see("Apaga «En columnas (a mano)»")


async def test_ecuacion_con_modo_columnas_tambien_avisa(user: User):
    await user.open("/")
    user.find(marker="modo-columnas").click()
    user.find(ui.input).type("2x + 3 = 11").trigger("keydown.enter")
    await user.should_see("Apaga «En columnas (a mano)»")


async def test_ejemplo_normal_apaga_el_modo_columnas(user: User):
    await user.open("/")
    user.find(marker="modo-columnas").click()
    user.find("2x + 3 = 11").click()
    await user.should_see("restamos 3 en ambos lados")
    await user.should_not_see("Apaga «En columnas (a mano)»")


async def test_desigualdad_desde_la_pantalla(user: User):
    await user.open("/")
    user.find(ui.input).type("−2x + 1 ≥ 7").trigger("keydown.enter")
    await user.should_see("el sentido de la desigualdad se invierte")
    await user.should_see("En intervalo: (−∞, −3]")


async def test_ejemplo_de_desigualdad(user: User):
    await user.open("/")
    user.find("3(x − 1) > 2x + 4").click()
    await user.should_see("En intervalo: (7, +∞)")


async def test_teclas_de_comparacion(user: User):
    await user.open("/")
    campo = user.find(ui.input).elements.pop()
    for tecla in ["x", "≥", "3"]:
        user.find(marker=f"tecla-{tecla}").click()
    assert campo.value == "x≥3"
    user.find(marker="tecla-C").click()
    for tecla in ["x", "<", "5"]:
        user.find(marker=f"tecla-{tecla}").click()
    user.find("Resolver").click()
    await user.should_see("En intervalo: (−∞, 5)")


async def test_la_operacion_en_los_dos_lados_se_dibuja(user: User):
    await user.open("/?q=2x %2B 3 = 11")
    await user.should_see("Resultado")
    from web.app import _paso_html
    from motor import resolver_ecuacion
    html = _paso_html(resolver_ecuacion("2x + 3 = 11").pasos[0])
    assert html.count('class="paso-expr') == 2 and "paso-previa" in html


async def test_formula_desde_la_pantalla(user: User):
    await user.open("/")
    user.find(ui.input).type("despejar t en v = d/t").trigger("keydown.enter")
    await user.should_see("multiplicamos ambos lados por t")
    await user.should_see("Se supone que t, v no valen 0")
    await user.should_see("Resultado")


async def test_ejemplo_de_formula(user: User):
    await user.open("/")
    user.find("despejar h en A = b·h/2").click()
    await user.should_see("Se supone que b no vale 0")


async def test_tecla_despejar(user: User):
    await user.open("/")
    campo = user.find(ui.input).elements.pop()
    user.find(marker="tecla-despejar").click()
    assert campo.value == "despejar "
    user.find(marker="tecla-C").click()
    for tecla in ["x", "="]:
        user.find(marker=f"tecla-{tecla}").click()
    user.find(marker="tecla-despejar").click()
    assert campo.value == "x=, despejar "


async def test_varias_letras_sin_despejar_explica_como(user: User):
    await user.open("/")
    user.find(ui.input).type("v = d/t").trigger("keydown.enter")
    await user.should_see("despejar d en v = d/t")


async def test_formula_con_modo_columnas_avisa(user: User):
    await user.open("/")
    user.find(marker="modo-columnas").click()
    user.find(ui.input).type("despejar t en v = d/t").trigger("keydown.enter")
    await user.should_see("Apaga «En columnas (a mano)»")


async def test_factorizar_desde_la_pantalla(user: User):
    await user.open("/")
    user.find(ui.input).type("factorizar x² − 9").trigger("keydown.enter")
    await user.should_see("diferencia de cuadrados")
    await user.should_see("Casos usados")
    await user.should_see("Resultado")


async def test_algebra_sin_comando_por_enlace(user: User):
    await user.open("/?q=(x %2B 3)²")
    await user.should_see("producto notable")
    await user.should_see("Fórmula usada")


async def test_ejemplos_de_algebra_fracciones_y_raices(user: User):
    await user.open("/")
    user.find("(x + 2)(x + 5)").click()
    await user.should_see("término común")
    user.find("(x² − 9)/(x − 3)").click()
    await user.should_see("Se supone que x ≠ 3")
    user.find("√12").click()
    await user.should_see("12 = 2²·3")
    await user.should_see("En decimales")


async def test_ejemplo_de_factorizar(user: User):
    await user.open("/")
    user.find("factorizar 2x² + 7x + 3").click()
    await user.should_see("a·c = 6")


async def test_teclas_de_comandos_y_potencias(user: User):
    await user.open("/")
    campo = user.find(ui.input).elements.pop()
    for tecla in ["x", "²", "−", "9"]:
        user.find(marker=f"tecla-{tecla}").click()
    assert campo.value == "x²−9"
    user.find(marker="tecla-factorizar").click()
    assert campo.value == "factorizar x²−9"
    user.find(marker="tecla-simplificar").click()           # cambia el comando, no lo repite
    assert campo.value == "simplificar x²−9"
    user.find(marker="tecla-C").click()
    user.find(marker="tecla-desarrollar").click()
    assert campo.value == "desarrollar "
    user.find(marker="tecla-C").click()
    user.find(marker="tecla-³").click()
    assert campo.value == "³"


async def test_algebra_con_modo_columnas_avisa(user: User):
    await user.open("/")
    user.find(marker="modo-columnas").click()
    user.find(ui.input).type("factorizar x² − 9").trigger("keydown.enter")
    await user.should_see("Apaga «En columnas (a mano)»")


async def test_error_de_ecuacion_no_lineal(user: User):
    await user.open("/")
    user.find(ui.input).type("x² = 4").trigger("keydown.enter")
    await user.should_see("no es lineal")


def test_pizarra_marca_y_escapa():
    from web.app import _pizarra_html
    html = _pizarra_html({"lineas": ["  12", "+ <5"], "marcas": [[0, 3, 4], [1, 2, 4]]})
    assert html.count("<mark>") == 2 and "&lt;" in html and "<5" not in html
    assert "<mark>2</mark>" in html


def test_formulas_con_texto_peligroso_se_escapan():
    assert "<script>" not in resaltar("<script>alert(1)</script> 2 + 3", "2 + 3")
    assert "<mark" in resaltar("Sumamos 2 + 3 = 5.", "2 + 3")


def test_formula_que_falla_cae_a_texto_plano(monkeypatch):
    import web.formulas as f
    monkeypatch.setattr(f, "convert", lambda *a, **k: (_ for _ in ()).throw(ValueError("boom")))
    assert "formula-plana" in f.mathml("\\badlatex", "2 + 3")


async def test_direccion_de_salud_para_render(user: User):
    respuesta = await user.http_client.get("/salud")
    assert respuesta.status_code == 200 and respuesta.text == "ok"


async def test_un_ejercicio_que_tarda_demasiado_se_corta_con_un_mensaje(user: User, monkeypatch):
    import time

    import web.app as app_web
    monkeypatch.setattr(app_web, "TIEMPO_MAXIMO", 0.2)
    monkeypatch.setattr(app_web, "resolver_auto", lambda texto: time.sleep(1.5))
    await user.open("/")
    user.find(ui.input).type("2 + 3").trigger("keydown.enter")
    await user.should_see("tarda demasiado")
    await user.should_not_see("Resultado")


async def test_la_pagina_sigue_viva_despues_de_un_ejercicio_lento(user: User, monkeypatch):
    """Tras cortar un ejercicio lento, el siguiente ejercicio normal se resuelve sin problema."""
    import time

    import web.app as app_web
    monkeypatch.setattr(app_web, "TIEMPO_MAXIMO", 0.2)
    original = app_web.resolver_auto
    monkeypatch.setattr(app_web, "resolver_auto", lambda texto: time.sleep(1.0))
    await user.open("/")
    user.find(ui.input).type("2 + 3").trigger("keydown.enter")
    await user.should_see("tarda demasiado")
    monkeypatch.setattr(app_web, "resolver_auto", original)
    user.find("Resolver").click()
    await user.should_see("Resultado")


# ---------------------------------------------------------------------------
# Pestañas, niveles y el Formulario
# ---------------------------------------------------------------------------

async def test_hay_dos_pestanas(user: User):
    await user.open("/")
    await user.should_see(marker="pestana-calculadora")
    await user.should_see(marker="pestana-formulas")


async def test_el_nivel_basica_oculta_lo_de_algebra_y_todo_lo_vuelve_a_mostrar(user: User):
    await user.open("/")
    await user.should_see(marker="tecla-factorizar")
    user.find(marker="nivel-Básica").click()
    await user.should_not_see(marker="tecla-factorizar")
    await user.should_not_see(marker="tecla-despejar")
    await user.should_not_see(marker="tecla-x")
    await user.should_see(marker="tecla-√")                       # lo básico se queda
    await user.should_see("Prueba con:")
    await user.should_not_see("Factorizar:")
    user.find(marker="nivel-Ecuaciones").click()
    await user.should_see(marker="tecla-despejar")
    await user.should_see(marker="tecla-x")
    await user.should_not_see(marker="tecla-factorizar")
    await user.should_see("Ecuaciones:")
    user.find(marker="nivel-Todo").click()
    await user.should_see(marker="tecla-factorizar")
    await user.should_see("Factorizar:")


async def test_resolver_sigue_funcionando_con_nivel_basico(user: User):
    await user.open("/")
    user.find(marker="nivel-Básica").click()
    user.find(ui.input).type("2 + 3 × 4").trigger("keydown.enter")
    await user.should_see("Resultado")


async def test_formulario_elegir_tema_y_formula(user: User):
    await user.open("/")
    user.find(marker="pestana-formulas").click()
    await user.should_see("Movimiento")
    await user.should_see("Elige una fórmula")
    user.find(marker="tema-electricidad").click()
    await user.should_see("Ley de Ohm")
    user.find(marker="formula-ohm").click()
    await user.should_see("¿Qué letra quieres hallar?")
    await user.should_see("voltaje")                              # el significado de cada letra
    await user.should_see(marker="valor-I")
    await user.should_see(marker="valor-R")


async def test_formulario_calcular_con_numeros(user: User):
    await user.open("/")
    user.find(marker="pestana-formulas").click()
    user.find(marker="formula-velocidad").click()
    await user.should_see(marker="valor-d")                       # la pantalla se redibuja al elegir la fórmula
    user.find(marker="valor-d").type("100")
    user.find(marker="valor-t").type("8")
    user.find(marker="btn-calcular").click()
    await user.should_see("Respuesta: v = 25/2 m/s = 12.5 m/s")
    await user.should_see("ponemos los valores")


async def test_formulario_cambiar_la_letra_a_hallar(user: User):
    await user.open("/")
    user.find(marker="pestana-formulas").click()
    user.find(marker="formula-velocidad").click()
    await user.should_see(marker="objetivo-t")
    user.find(marker="objetivo-t").click()
    await user.should_see(marker="valor-v")
    await user.should_see(marker="valor-d")
    user.find(marker="valor-v").type("4")
    user.find(marker="valor-d").type("20")
    user.find(marker="btn-calcular").click()
    await user.should_see("Respuesta: t = 5 s")


async def test_formulario_solo_despejar(user: User):
    await user.open("/")
    user.find(marker="pestana-formulas").click()
    user.find(marker="tema-electricidad").click()
    await user.should_see("Ley de Ohm")
    user.find(marker="formula-ohm").click()
    await user.should_see(marker="objetivo-I")
    user.find(marker="objetivo-I").click()
    await user.should_see(marker="valor-V")
    user.find(marker="btn-despejar").click()
    await user.should_see("dividimos ambos lados")
    await user.should_see("Resultado")


async def test_formulario_valor_que_no_es_numero(user: User):
    await user.open("/")
    user.find(marker="pestana-formulas").click()
    user.find(marker="formula-velocidad").click()
    await user.should_see(marker="valor-d")
    user.find(marker="valor-d").type("veinte")
    user.find(marker="valor-t").type("8")
    user.find(marker="btn-calcular").click()
    await user.should_see("debe ser un número")


async def test_formulario_falta_un_valor_y_division_entre_cero(user: User):
    await user.open("/")
    user.find(marker="pestana-formulas").click()
    user.find(marker="formula-velocidad").click()
    await user.should_see(marker="valor-d")
    user.find(marker="valor-d").type("20")
    user.find(marker="btn-calcular").click()
    await user.should_see("Falta el valor de t")
    user.find(marker="valor-t").type("0")
    user.find(marker="btn-calcular").click()
    await user.should_see("No se puede dividir entre cero")
