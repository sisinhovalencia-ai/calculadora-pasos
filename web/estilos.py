"""Estilos de la interfaz: una hoja de cuaderno cuadriculado.

Idea de diseño (para quien retome esto):
  - Fondo de cuadrícula suave, como la hoja donde el estudiante hace sus ejercicios.
  - Tinta azul de bolígrafo para lo que se escribe (ejercicio y expresiones).
  - Margen rojo con los números de paso: los pasos SÍ son una secuencia.
  - Resaltador amarillo solo sobre la operación que se resuelve en cada paso.
  - Doble subrayado rojo (como lo marca un profesor) solo en el resultado final.
  - Una sola familia tipográfica, pensada para leerse fácil (Atkinson Hyperlegible).

Reglas de mantenimiento:
  - Los colores son variables CSS: el modo oscuro solo las redefine.
  - Las medidas que se repiten (columna del número, hueco, tamaño de la cuadrícula)
    también son variables, así el margen rojo siempre queda alineado con los pasos.
  - El único momento animado es el margen rojo "trazándose" al aparecer un
    resultado; todo lo demás responde a una acción del usuario.
  - Los nombres de clase no cambian: se puede reemplazar este archivo sin tocar la UI.
"""

HEAD_HTML = """
<meta name="color-scheme" content="light dark">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet">
"""

CSS = """
/* ---------- Variables ---------- */
:root {
  --papel: #EEF4F7;
  --cuadricula: #D9E5ED;
  --tinta: #1D3A9E;
  --grafito: #232A33;
  --suave: #4F5D6D;          /* 6:1 sobre el papel: legible también en texto pequeño */
  --margen: #C93550;         /* un poco más oscuro: el rojo del número pasa 4.5:1 */
  --resaltador: #FFE14D;
  --tecla: #FFFFFF;
  --linea: #B7C9D8;

  --celda: 28px;             /* tamaño del cuadro de la cuadrícula */
  --col-num: 44px;           /* columna de los números de paso */
  --hueco: 22px;             /* espacio entre número y contenido */
  --sangria: calc(var(--col-num) + var(--hueco));
  --linea-margen: calc(var(--col-num) + var(--hueco) / 2);
  color-scheme: light;
}
body.body--dark {
  --papel: #10161E;
  --cuadricula: #1A2430;
  --tinta: #97B6FF;
  --grafito: #E7ECF2;
  --suave: #A3B1C0;
  --margen: #FF7B8C;
  --resaltador: rgba(255, 225, 77, 0.32);
  --tecla: #18212C;
  --linea: #3A4C60;
  color-scheme: dark;
}

/* ---------- Base ---------- */
body, body.body--light, body.body--dark {
  background-color: var(--papel);
  background-image:
    linear-gradient(var(--cuadricula) 1px, transparent 1px),
    linear-gradient(90deg, var(--cuadricula) 1px, transparent 1px);
  background-size: var(--celda) var(--celda);
  color: var(--grafito);
  font-family: 'Atkinson Hyperlegible', 'Segoe UI', system-ui, -apple-system, sans-serif;
  -webkit-text-size-adjust: 100%;
}
::selection { background: var(--resaltador); color: var(--grafito); }
.nicegui-content { padding: 0 !important; gap: 0 !important; align-items: stretch !important; }

.hoja { width: 100%; max-width: 780px; margin: 0 auto; padding: 44px 22px 96px; box-sizing: border-box; }

.titulo {
  margin: 0 0 .5rem; color: var(--tinta); font-weight: 700;
  font-size: clamp(2rem, 6vw, 3.3rem); line-height: 1.05; letter-spacing: -0.02em;
  text-wrap: balance;
}
.subtitulo { margin: 0; color: var(--suave); font-size: 1.1rem; max-width: 42rem; line-height: 1.45; text-wrap: pretty; }

/* ---------- Campo donde se escribe el ejercicio ---------- */
.entrada { width: 100%; margin-top: 30px; }
.entrada .q-field__control {
  min-height: 86px; border-bottom: 2px solid var(--tinta); border-radius: 0;
  transition: box-shadow .15s ease;
}
.entrada .q-field__control:before, .entrada .q-field__control:after { display: none; }
/* Al escribir, la línea se engrosa (con sombra, para que nada se mueva) */
.entrada.q-field--focused .q-field__control { box-shadow: 0 2px 0 0 var(--tinta); }
.entrada .q-field__native {
  font-size: 1.8rem; font-weight: 700; color: var(--tinta); padding-top: 34px;
  caret-color: var(--margen);
}
.entrada .q-field__native::placeholder { color: var(--suave); font-weight: 400; opacity: .85; }
.entrada .q-field__label { color: var(--suave); font-size: 1.05rem; }

.fila-accion { display: flex; flex-wrap: wrap; align-items: center; gap: 18px; margin-top: 18px; }
.boton-resolver {
  background: var(--tinta) !important; color: var(--papel) !important;
  font-weight: 700; font-size: 1.1rem; padding: 10px 28px; border-radius: 10px;
  min-height: 48px; text-transform: none; letter-spacing: 0;
  transition: transform .1s ease;
}
.boton-resolver:active { transform: translateY(1px); }
.q-switch__label, .fila-accion .q-toggle__label { color: var(--grafito); }

/* ---------- Teclado de símbolos (útil en el celular) ---------- */
.teclado { display: grid !important; grid-template-columns: repeat(4, 1fr); gap: 8px; max-width: 340px; margin-top: 22px; }
.tecla {
  background: var(--tecla) !important; color: var(--grafito) !important;
  border: 1px solid var(--linea); border-radius: 10px;
  min-height: 52px; font-size: 1.3rem; font-weight: 700;
  transition: background-color .1s ease, transform .1s ease;
}
.tecla.op { color: var(--tinta) !important; }
/* Al tocar una tecla se "resalta", igual que el resaltador del cuaderno */
.tecla:hover { border-color: var(--tinta); }
.tecla:active { background: var(--resaltador) !important; transform: translateY(1px); }
.tecla-ancha { grid-column: span 2; font-size: 1rem; font-weight: 400; letter-spacing: .08em; min-height: 48px; }

.ejemplos { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; margin-top: 22px; color: var(--suave); }
.ejemplo {
  border: 1px solid var(--linea); border-radius: 10px; background: transparent !important;
  color: var(--grafito) !important; text-transform: none; font-size: 1rem;
  padding: 4px 12px; min-height: 40px;
}
.ejemplo:hover { border-color: var(--tinta); }
.ejemplo:active { background: var(--resaltador) !important; }

button:focus-visible, .q-btn:focus-visible, summary:focus-visible,
.q-toggle:focus-visible, .q-checkbox:focus-visible {
  outline: 3px solid var(--tinta); outline-offset: 2px; border-radius: 6px;
}

/* ---------- Resultado ---------- */
.zona { width: 100%; margin-top: 42px; }
math { math-style: normal; font-family: 'Latin Modern Math', 'STIX Two Math', 'Cambria Math', 'Noto Sans Math', math; }
.ejercicio math { font-size: 2.1rem; color: var(--tinta); }
.ejercicio { margin: 0 0 6px var(--sangria); }

.pasos { list-style: none; padding: 0; margin: 28px 0 0; position: relative; }
.pasos::before {
  content: ''; position: absolute; left: var(--linea-margen); top: 0; bottom: 0;
  width: 2px; background: var(--margen); opacity: .7;
  transform-origin: top; animation: trazar-margen .7s ease-out both;
}
.paso, .final {
  display: grid; grid-template-columns: var(--col-num) minmax(0, 1fr);
  column-gap: var(--hueco); padding-bottom: 28px; list-style: none;
}
.paso-num { text-align: right; color: var(--margen); font-weight: 700; font-size: 1.25rem; line-height: 1.5; }
.paso-texto { margin: 0 0 4px; font-size: 1.12rem; line-height: 1.5; max-width: 40rem; text-wrap: pretty; }
mark.marca {
  background: var(--resaltador); color: inherit; padding: 0 .3em; border-radius: 3px;
  -webkit-box-decoration-break: clone; box-decoration-break: clone;
}
/* Una fórmula larga se desliza dentro de su renglón; la página nunca se desborda */
.paso-expr { max-width: 100%; overflow-x: auto; padding: 2px 0; }
.paso-expr math { font-size: 1.7rem; color: var(--tinta); }
.paso-previa math { font-size: 1.35rem; color: var(--suave); }   /* la operación en los dos lados */
.formula-plana { font-size: 1.5rem; color: var(--tinta); }
details.porque { margin-top: 6px; color: var(--suave); }
details.porque summary { cursor: pointer; font-size: .98rem; width: fit-content; padding: 4px 0; }
details.porque p { margin: 6px 0 0; font-size: 1rem; line-height: 1.5; max-width: 38rem; }

/* División larga y otras operaciones escritas en columnas */
.pizarra {
  margin: 8px 0 6px; padding: 0; max-width: 100%; overflow-x: auto; white-space: pre; color: var(--tinta);
  font-family: ui-monospace, 'Cascadia Mono', 'Segoe UI Mono', Consolas, 'DejaVu Sans Mono', monospace;
  font-size: 1.45rem; line-height: 1.3; letter-spacing: .12em; background: transparent;
}
.pizarra mark { background: var(--resaltador); color: inherit; border-radius: 3px; }

/* Resultado final: doble subrayado rojo, como lo marca un profesor */
.final { padding-bottom: 0; }
.final-marca { text-align: right; color: var(--margen); font-weight: 700; font-size: 1.6rem; line-height: 1.3; }
.final-etq { margin: 0 0 4px; color: var(--suave); font-size: 1rem; }
.final-valor { display: inline-block; max-width: 100%; overflow-x: auto; padding-bottom: 4px; border-bottom: 6px double var(--margen); }
.final-valor math { font-size: 2.4rem; color: var(--tinta); }
.final-decimal { margin: 12px 0 0; color: var(--suave); font-size: 1.05rem; }

/* Errores: dicen qué pasó, sin dramatismo */
.error {
  margin-top: 8px; padding: 14px 18px; max-width: 40rem;
  border-left: 4px solid var(--margen);
  background: color-mix(in srgb, var(--margen) 8%, transparent);
  border-radius: 0 10px 10px 0;
}
.error strong { color: var(--margen); font-size: 1.1rem; }
.error p { margin: 6px 0 0; font-size: 1.08rem; line-height: 1.5; }

.siguiente { margin: 6px 0 0 var(--sangria); }

/* ---------- Movimiento: solo el margen rojo al aparecer un resultado ---------- */
@keyframes trazar-margen { from { transform: scaleY(0); } to { transform: scaleY(1); } }

/* ---------- Pantallas pequeñas ---------- */
@media (max-width: 520px) {
  :root { --col-num: 32px; --hueco: 16px; }
  .hoja { padding: 28px 16px 72px; }
  .teclado { max-width: 100%; }
  .tecla { min-height: 56px; }
  .entrada .q-field__native { font-size: 1.5rem; }
  .ejercicio math { font-size: 1.7rem; }
  .paso-expr math { font-size: 1.45rem; }
  .paso-previa math { font-size: 1.2rem; }
  .pizarra { font-size: 1.2rem; }
  .final-valor math { font-size: 2rem; }
}

/* ---------- Impresión: solo la solución, en tinta sobre papel blanco ---------- */
@media print {
  body, body.body--light, body.body--dark {
    --papel: #FFFFFF; --tinta: #1D3A9E; --grafito: #000000; --suave: #444444;
    --margen: #C93550; --resaltador: #FFE14D;
    background: #FFFFFF !important; color: #000000;
  }
  .entrada, .fila-accion, .teclado, .ejemplos, .siguiente, .subtitulo { display: none !important; }
  .hoja { max-width: none; padding: 0; }
  .zona { margin-top: 0; }
  .paso, .final { break-inside: avoid; }
  .pasos::before { animation: none; }
  mark, mark.marca, .pizarra mark, .final-valor {
    -webkit-print-color-adjust: exact; print-color-adjust: exact;
  }
}

/* ---------- Accesibilidad: sin animaciones si el usuario lo pide ---------- */
@media (prefers-reduced-motion: reduce) { * { transition: none !important; animation: none !important; } }

/* ---------- Pestañas y niveles ---------- */
.pestanas { margin-top: 20px; border-bottom: 2px solid var(--linea); }
.pestanas .q-tab { text-transform: none; color: var(--suave); min-height: 50px; padding: 0 22px 0 0; }
.pestanas .q-tab__label { font-size: 1.15rem !important; font-weight: 700 !important; }
.pestanas .q-tab--active { color: var(--tinta); }
.pestanas .q-tab__indicator { background: var(--tinta); height: 3px; }
.paneles, .paneles .q-panel, .paneles .q-tab-panel { background: transparent !important; color: inherit; }
.paneles .q-tab-panel { padding: 0 !important; overflow: visible; }
.paneles .q-panel { overflow: visible !important; }
.fila-nivel { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; margin-top: 20px; color: var(--suave); }
.niveles { display: flex; flex-wrap: wrap; gap: 8px; }
.nivel { border: 1.5px solid var(--linea); border-radius: 999px; background: var(--tecla) !important; color: var(--grafito) !important;
         min-height: 38px; padding: 0 16px; text-transform: none; }
.nivel.activo { background: var(--tinta) !important; color: var(--papel) !important; border-color: var(--tinta); }

/* ---------- El Formulario ---------- */
.formulas-intro { color: var(--suave); max-width: 40rem; margin: 22px 0 0; }
.temas { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 22px; }
.tema { border: 1.5px solid var(--linea); border-radius: 999px; background: var(--tecla) !important; color: var(--grafito) !important;
        padding: 4px 16px; min-height: 42px; text-transform: none; }
.tema.activo { background: var(--tinta) !important; color: var(--papel) !important; border-color: var(--tinta); }
.lista-formulas { display: grid !important; width: 100%; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 10px; margin-top: 18px; }
.tarjeta-formula { border: 1.5px solid var(--linea); border-radius: 12px; background: var(--tecla) !important; color: var(--grafito) !important;
                   padding: 10px 14px; height: auto; text-transform: none; }
.tarjeta-formula .q-btn__content { flex-direction: column; align-items: flex-start; text-align: left; gap: 2px; width: 100%; }
.tarjeta-nombre { font-weight: 700; font-size: 1rem; line-height: 1.25; }
.tarjeta-expr { color: var(--tinta); font-family: 'Cambria Math', 'STIX Two Math', 'Times New Roman', serif; font-size: 1.1rem; }
.tarjeta-formula.activa { border-color: var(--tinta); box-shadow: inset 0 0 0 2px var(--tinta); }
.detalle-formula { width: 100%; box-sizing: border-box; margin-top: 26px; padding: 20px 22px; border: 1.5px solid var(--linea); border-radius: 14px;
                   background: color-mix(in srgb, var(--tecla) 75%, transparent); }
.detalle-formula h2 { margin: 0 0 6px; font-size: 1.35rem; font-weight: 700; }
.formula-grande { font-size: 1.7rem; color: var(--tinta); margin: 4px 0 14px; }
table.variables { border-collapse: collapse; margin: 6px 0 4px; }
table.variables td { padding: 4px 18px 4px 0; text-align: left; vertical-align: baseline; }
table.variables .letra-v { font-weight: 700; color: var(--tinta); font-style: italic; font-size: 1.1rem; }
table.variables .unidad-v { color: var(--suave); }
.nota-formula { color: var(--suave); font-size: .95rem; margin: 6px 0 0; }
.pregunta { margin: 20px 0 8px; font-weight: 700; }
.letras { display: flex; flex-wrap: wrap; gap: 8px; }
.letra { min-width: 50px; min-height: 46px; border: 1.5px solid var(--linea); border-radius: 10px; background: var(--tecla) !important;
         color: var(--grafito) !important; font-size: 1.15rem; font-style: italic; font-weight: 700; text-transform: none; }
.letra.activa { background: var(--tinta) !important; color: var(--papel) !important; border-color: var(--tinta); }
.datos { display: grid !important; width: 100%; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 8px 16px; margin-top: 6px; max-width: 560px; }
.acciones-formula { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 16px; }
.boton-secundario { background: transparent !important; color: var(--tinta) !important; border: 2px solid var(--tinta); }
.zona-formula { width: 100%; margin-top: 30px; }
@media (max-width: 520px) {
  .lista-formulas { grid-template-columns: 1fr; }
  .detalle-formula { padding: 16px 14px; }
  .formula-grande { font-size: 1.45rem; }
}
"""