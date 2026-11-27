"""Estilos MatrixOps y clases de presentación de la calculadora.

La paleta, la jerarquía tipográfica y el diseño responsive se definen aquí.
Se conservan las clases funcionales de la calculadora para separar la UI del motor.
"""

HEAD_HTML = """
<meta name="color-scheme" content="light">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Montserrat:wght@600;700;800&family=Poppins:wght@500;600;700&display=swap" rel="stylesheet">
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

/* ---------- Identidad MatrixOps ---------- */
:root {
  --navy: #102C52;
  --sky: #8EC5F5;
  --gold: #D9A12E;
  --warm: #F8F6F0;
  --green: #35A36B;
  --papel: var(--warm);
  --cuadricula: transparent;
  --tinta: #142B4A;
  --grafito: #142B4A;
  --suave: #54677E;
  --margen: var(--gold);
  --resaltador: #F5E7BE;
  --tecla: #FFFFFF;
  --linea: #DCE3EA;
  color-scheme: light;
}
body.body--dark {
  --papel: var(--warm); --tinta: #142B4A; --grafito: #142B4A;
  --suave: #54677E; --margen: var(--gold); --tecla: #FFFFFF;
  --linea: #DCE3EA; color-scheme: light;
}
body, body.body--light, body.body--dark {
  background: var(--warm) !important; color: #142B4A;
  font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
}
.nicegui-content { width: 100%; }
.hoja { width: 100%; max-width: 1640px; padding: 28px clamp(16px, 3vw, 48px) 42px; }
.marca-cabecera { min-height: 112px; display: flex; align-items: center; gap: 18px; padding: 0 4px 22px; border-bottom: 1px solid #DCE3EA; }
.marca-simbolo { width: 64px; height: 64px; flex: 0 0 64px; display: grid; place-items: center; position: relative; border-radius: 18px 18px 18px 5px; background: var(--navy); color: var(--sky); box-shadow: 0 8px 18px #102C5226; }
.marca-simbolo span { font: 700 39px 'Cambria Math', Georgia, serif; transform: translateY(-2px); }
.marca-simbolo i { position: absolute; right: -5px; bottom: -5px; width: 24px; height: 24px; display: grid; place-items: center; border: 2px solid var(--warm); border-radius: 50%; background: var(--gold); color: white; font: 700 13px Inter, sans-serif; }
.marca-texto { display: flex; flex-direction: column; align-items: flex-start; }
.titulo { margin: 0; color: var(--navy); font: 800 clamp(1.65rem, 3vw, 2.15rem)/1 'Montserrat', sans-serif; letter-spacing: .055em; }
.titulo b { color: var(--gold); }
.subtitulo { margin: 7px 0 0; color: #40546C; font: 500 1rem/1.35 'Poppins', sans-serif; }
.lema { margin: 7px 0 0; color: #63768A; font-size: .68rem; font-weight: 700; letter-spacing: .16em; }
.lema i { color: var(--gold); font-style: normal; padding: 0 3px; }
.marca-sello { margin-left: auto; display: flex; align-items: center; gap: 9px; color: #53677E; font-size: .7rem; font-weight: 700; letter-spacing: .11em; }
.sello-punto, .estado-en-linea i { width: 8px; height: 8px; border-radius: 50%; background: var(--green); box-shadow: 0 0 0 4px #35A36B1A; }
.workspace-grid { display: grid !important; grid-template-columns: minmax(220px, 260px) minmax(460px, 1fr) minmax(220px, 260px); gap: 18px; align-items: start; margin-top: 22px; }
.panel-lateral, .panel-central, .recursos-estudio { box-sizing: border-box; border-radius: 18px; box-shadow: 0 8px 26px #102C5210; }
.panel-lateral { padding: 22px 20px; background: var(--navy); color: #F8F6F0; border: 1px solid #8EC5F555; }
.panel-lateral h2, .panel-lateral h3 { font-family: 'Montserrat', sans-serif; color: #fff; }
.panel-lateral h2 { margin: 8px 0 9px; font-size: 1.15rem; line-height: 1.3; }
.panel-lateral h3 { margin: 21px 0 10px; font-size: .82rem; }
.panel-kicker { color: #6B93BC; font: 700 .65rem/1.3 'Montserrat', sans-serif; letter-spacing: .15em; }
.panel-lateral .panel-kicker { color: var(--sky); }
.panel-copy { margin: 0; color: #D5E1ED; font-size: .83rem; line-height: 1.6; }
.motor-badges { display: flex; gap: 7px; margin-top: 15px; }
.motor-badges span { padding: 5px 9px; border: 1px solid #8EC5F566; border-radius: 999px; color: var(--sky); font-size: .72rem; font-weight: 700; }
.codigo-card { margin-top: 13px; overflow: hidden; border: 1px solid #8EC5F544; border-radius: 11px; background: #0B2140; }
.codigo-cabecera { display: flex; align-items: center; gap: 5px; padding: 9px 10px; border-bottom: 1px solid #FFFFFF12; }
.codigo-cabecera > span { width: 6px; height: 6px; border-radius: 50%; background: #8EC5F5; opacity: .8; }
.codigo-cabecera small { margin-left: auto; color: #95A9BF; font-size: .62rem; }
.codigo-card pre { margin: 0; padding: 11px 10px 13px; overflow: auto; color: #E3EDF6; font: .67rem/1.8 ui-monospace, Consolas, monospace; }
.codigo-card code i { color: var(--gold); font-style: normal; }
.modulos { display: flex; flex-wrap: wrap; gap: 6px; }
.modulos span { padding: 6px 8px; border-radius: 7px; background: #FFFFFF12; color: #EAF2FA; font-size: .69rem; }
.arbol { display: grid; justify-items: center; gap: 7px; padding: 11px 8px; border: 1px solid #8EC5F533; border-radius: 10px; background: #FFFFFF08; }
.nodo-raiz, .nodo { display: grid; place-items: center; min-width: 28px; min-height: 25px; padding: 0 7px; border: 1px solid #8EC5F588; border-radius: 6px; color: var(--sky); font-weight: 700; font-size: .8rem; }
.ramas, .hojas { width: 100%; display: flex; justify-content: space-around; position: relative; }
.ramas:before { content: ''; position: absolute; left: 25%; right: 25%; top: -5px; border-top: 1px solid #8EC5F577; }
.hojas span { color: #C5D5E4; font: .68rem ui-monospace, monospace; }
.verificado { display: flex; align-items: center; gap: 10px; margin-top: 15px; padding: 10px; border: 1px solid #35A36B66; border-radius: 10px; background: #35A36B18; }
.verificado > span { display: grid; place-items: center; width: 24px; height: 24px; border-radius: 50%; background: var(--green); color: white; font-weight: 700; }
.verificado strong, .verificado small { display: block; }
.verificado strong { color: #B9E7CC; font-size: .72rem; }
.verificado small { margin-top: 3px; color: #D5E1ED; font-size: .63rem; line-height: 1.35; }
.motor-live-card { margin-top: 14px; border-color: #8EC5F566; }
.motor-cadena { padding: 10px 11px; border-bottom: 1px solid #FFFFFF12; color: #CFE2F3; font: .66rem/1.5 ui-monospace, Consolas, monospace; overflow-wrap: anywhere; }
.motor-resumen { display: grid; gap: 4px; padding: 11px; border-bottom: 1px solid #FFFFFF12; }
.motor-tipo { color: #FFFFFF; font: 600 .8rem 'Poppins', sans-serif; }
.motor-pasos { color: var(--sky); font-size: .68rem; font-weight: 700; }
.motor-resumen small { color: #AFC4D9; font-size: .65rem; line-height: 1.4; }
.motor-espera, .motor-estado { display: grid; gap: 4px; padding: 10px 11px; }
.motor-espera strong { color: #E4EEF7; font-size: .7rem; }
.motor-espera small { color: #B8CADD; font-size: .63rem; line-height: 1.4; }
.motor-estado strong { font-size: .7rem; }
.motor-estado small { font-size: .63rem; line-height: 1.4; }
.motor-estado.warning { background: #D9A12E18; }
.motor-estado.warning strong { color: #F2C96B; }
.motor-estado.warning small { color: #F5E9C8; }
.motor-estado.error { background: #D95B5B20; }
.motor-estado.error strong { color: #FFAAAA; }
.motor-estado.error small { color: #F5D4D4; }
.motor-live-card .verificado { margin: 9px; padding: 8px; }
.motor-live-card .verificado strong { font-size: .66rem; }
.motor-live-card .verificado small { font-size: .59rem; }
.motor-live-card .motor-detalle { display: block; margin-top: 4px; color: #D7E8F4; overflow-wrap: anywhere; }
.panel-central { min-width: 0; padding: 22px clamp(18px, 2vw, 30px) 26px; border: 1px solid #E5E1D7; background: #FFF; }
.centro-encabezado { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.centro-encabezado h2, .recursos-estudio h2 { margin: 5px 0 0; color: var(--navy); font: 700 1.35rem/1.25 'Montserrat', sans-serif; }
.estado-en-linea { display: flex; align-items: center; gap: 9px; white-space: nowrap; color: #53677E; font-size: .72rem; font-weight: 600; }
.pestanas { margin-top: 14px; border-bottom: 1px solid var(--linea); }
.pestanas .q-tab { padding-right: 18px; color: #65768A; }
.pestanas .q-tab__label { font: 600 .92rem 'Poppins', sans-serif !important; }
.pestanas .q-tab--active { color: var(--navy); }
.pestanas .q-tab__indicator { background: var(--gold); height: 3px; }
.entrada { margin-top: 20px; }
.entrada .q-field__control { border-bottom-color: var(--sky); }
.entrada.q-field--focused .q-field__control { box-shadow: 0 2px 0 var(--gold); }
.entrada .q-field__native { color: var(--navy); font: 600 1.55rem 'Cambria Math', Georgia, serif; }
.boton-resolver { background: var(--gold) !important; color: var(--navy) !important; font: 700 .98rem 'Poppins', sans-serif; box-shadow: 0 5px 12px #D9A12E30; }
.tecla { border-color: #DCE3EA; border-radius: 9px; }
.tecla.op { color: var(--navy) !important; }
.tecla:hover { border-color: var(--sky); background: #F1F8FE !important; }
.ejemplo { border-radius: 999px; border-color: #DCE3EA; font-size: .88rem; }
.ejemplo:hover { border-color: var(--gold); }
.nivel.activo, .tema.activo, .letra.activa { background: var(--navy) !important; border-color: var(--navy); color: white !important; }
.ejercicio math, .paso-expr math, .formula-plana, .final-valor math { color: var(--navy); }
.paso-num, .final-marca { color: #A97813; }
.paso-texto, details.porque p { color: #354C65; font-size: 1rem; line-height: 1.65; }
.final-valor { border-bottom-color: var(--green); }
.final-valor math { color: var(--navy); }
.final-etq { color: #53677E; font-weight: 600; }
.panel-guia { padding-bottom: 18px; }
.guia-paso { display: flex; gap: 11px; align-items: flex-start; margin-top: 19px; }
.guia-paso > span { display: grid; place-items: center; width: 28px; height: 28px; flex: 0 0 28px; border-radius: 9px; background: #8EC5F526; color: var(--sky); font: 700 .68rem 'Montserrat', sans-serif; }
.guia-paso strong, .guia-paso small { display: block; }
.guia-paso strong { color: #FFF; font: 600 .81rem 'Poppins', sans-serif; }
.guia-paso small { margin-top: 3px; color: #CBD9E7; font-size: .69rem; line-height: 1.45; }
.modulos-botones { display: flex !important; flex-direction: row; flex-wrap: wrap !important; align-items: center; gap: 8px; }
.modulo-chip { display: inline-flex; align-items: center; width: auto; min-height: 0; padding: 5px 11px; border: 1px solid #FFFFFF33; border-radius: 999px; background: #FFFFFF10; color: #F3F7FB; font-size: .68rem; line-height: 1.25; white-space: nowrap; user-select: none; transition: background-color .15s ease, border-color .15s ease; }
.modulo-chip:hover, .modulo-chip:focus-visible { border-color: #FFFFFF55; background: #FFFFFF20; outline: none; }
.modulo-chip.futuro { border-style: dashed; color: #F0DDAE; }
.arbol-clickable { display: block; width: 100%; padding: 9px 10px; border: 1px solid #8EC5F555; border-radius: 10px; background: #FFFFFF09; color: #E8F1F8; cursor: pointer; transition: border-color .15s ease, background .15s ease; }
.arbol-clickable:hover, .arbol-clickable:focus-visible { border-color: var(--gold); background: #D9A12E12; outline: none; }
.arbol-content { display: flex; flex-direction: column; align-items: center; width: 100%; }
.arbol-prompt { align-self: flex-end; color: var(--gold); font: 600 .58rem 'Poppins', sans-serif; }
.arbol-svg { display: block; width: 100%; max-width: 220px; height: auto; overflow: visible; }
.arbol-lineas path { fill: none; stroke: #8EC5F5A8; stroke-width: 1.4; stroke-linecap: round; }
.arbol-caja { fill: #FFFFFF0A; stroke: #8EC5F588; stroke-width: 1; }
.arbol-caja.raiz { fill: #8EC5F51D; stroke: #8EC5F5B0; }
.arbol-operador { fill: var(--gold); font: 700 15px 'Cambria Math', Georgia, serif; }
.arbol-expresion { fill: #DCEBFA; font: 11px 'Cambria Math', Georgia, serif; }
.arbol-hoja { fill: #B6CADC; font: 10px ui-monospace, Consolas, monospace; }
.arbol-cta { margin-top: 3px; color: #D6E6F3; font-size: .62rem; }
.guia-tarjeta { display: flex !important; flex-wrap: nowrap !important; align-items: flex-start !important; gap: 11px; box-sizing: border-box; width: 100%; min-height: 58px; margin-top: 10px; padding: 9px 8px; border: 1px solid transparent; border-radius: 10px; color: #D7E4EF; cursor: pointer; }
.guia-tarjeta:not(.deshabilitada):hover { background: #FFFFFF0D; }
.guia-tarjeta.deshabilitada { opacity: .5; cursor: default !important; pointer-events: none; }
.guia-tarjeta .guia-num { display: grid; place-items: center; flex: 0 0 28px; width: 28px; height: 28px; border-radius: 9px; background: #FFFFFF14; color: #D7E4EF; font: 700 .68rem 'Montserrat', sans-serif; }
.guia-texto { flex: 1 1 auto; min-width: 0; width: auto !important; gap: 0 !important; align-items: flex-start; }
.guia-tarjeta .guia-titulo { display: block; margin: 0; color: #FFF; font: 600 .81rem/1.25 'Poppins', sans-serif; }
.guia-tarjeta .guia-descripcion { display: block; max-width: 100%; margin: 3px 0 0; color: #CBD9E7; font: .67rem/1.4 'Inter', sans-serif; white-space: normal; overflow-wrap: anywhere; }
.guia-tarjeta.activa { border-color: #8EC5F566; background: #8EC5F51A; }
.guia-tarjeta.activa .guia-num { background: var(--sky); color: var(--navy); }
.guia-tarjeta.completada { border-color: #35A36B66; background: #35A36B18; }
.guia-tarjeta.completada .guia-num { background: var(--green); color: white; }
.historial-rapido { margin-top: 20px; padding-top: 14px; border-top: 1px solid #8EC5F544; }
.historial-titulo { margin-bottom: 8px; color: var(--sky); font: 700 .59rem 'Montserrat', sans-serif; letter-spacing: .12em; }
.historial-item, .historial-demo { display: block; width: 100%; min-height: 36px; margin-top: 6px; padding: 6px 9px; overflow: hidden; border: 1px solid #8EC5F544; border-radius: 8px; color: #ECF4FA !important; text-align: left; text-overflow: ellipsis; text-transform: none; white-space: nowrap; font-size: .67rem; cursor: pointer; transition: color .15s ease, background-color .15s ease, border-color .15s ease; }
.historial-item:hover, .historial-demo:hover { background: #8EC5F51A !important; border-color: var(--sky); }
.historial-demo { border-color: #D9A12E77; color: #F1D38D !important; }
.historial-demo:hover { border-color: #D9A12EAA; background: #D9A12E26 !important; }
.historial-ayuda { display: block; margin-top: 7px; color: #C7D6E4; font-size: .62rem; line-height: 1.4; }
.movil-card { max-width: 175px; margin: 23px auto 0; padding: 12px 13px; border: 1px solid #8EC5F577; border-radius: 17px; background: #0A2344; box-shadow: 0 10px 24px #06172C55; }
.movil-top { display: flex; align-items: center; gap: 6px; margin-bottom: 15px; }
.movil-top > span { width: 5px; height: 5px; border-radius: 50%; background: var(--sky); }
.movil-top small { color: #AFC4D9; font-size: .44rem; letter-spacing: .05em; }
.movil-linea { width: 70%; height: 5px; margin: 7px 0; border-radius: 99px; background: #FFFFFF1E; }
.movil-linea.ancho { width: 95%; }
.movil-math { margin: 11px 0; padding: 9px 5px; border-radius: 7px; background: #F8F6F0; color: var(--navy); text-align: center; font: 700 .83rem 'Cambria Math', Georgia, serif; }
.movil-resultado { padding: 7px 6px; border-radius: 7px; background: #35A36B22; color: #A9E1BF; text-align: center; font: 700 .72rem 'Montserrat', sans-serif; }
.movil-nota { margin: 9px 0 0; color: #C7D6E4; text-align: center; font-size: .64rem; line-height: 1.4; }
.recursos-estudio { display: grid; grid-template-columns: 1.4fr repeat(3, 1fr) 1.1fr; gap: 12px; align-items: center; margin-top: 18px; padding: 19px 22px; border: 1px solid #E5E1D7; background: #FFF; }
.recursos-estudio h2 { font-size: 1rem; }
.recurso { display: flex; align-items: center; gap: 9px; min-width: 0; }
.recurso-icono { display: grid; place-items: center; width: 35px; height: 35px; flex: 0 0 35px; border-radius: 10px; background: #8EC5F526; color: var(--navy); font-size: 1.1rem; }
.recurso strong, .recurso small { display: block; }
.recurso strong { color: var(--navy); font: 600 .71rem 'Poppins', sans-serif; }
.recurso small { margin-top: 3px; color: #65768A; font-size: .61rem; line-height: 1.4; }
.frase-estudio { padding: 10px 12px; border-left: 2px solid var(--gold); color: #70551F; font: 600 .74rem/1.45 'Poppins', sans-serif; }
@media (max-width: 1100px) {
  .workspace-grid { grid-template-columns: minmax(190px, 230px) minmax(0, 1fr); }
  .panel-guia { grid-column: 1 / -1; display: grid !important; grid-template-columns: 1fr 1fr 1fr 1.3fr; gap: 10px 18px; align-items: center; }
  .panel-guia > .panel-kicker, .panel-guia > h2, .panel-guia > .panel-copy { grid-column: 1 / -1; }
  .panel-guia .guia-paso { margin-top: 2px; }
  .panel-guia .movil-card { margin: 0 auto; }
  .panel-guia .movil-nota { display: none; }
  .recursos-estudio { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 720px) {
  .hoja { padding: 18px 13px 30px; }
  .marca-cabecera { min-height: 82px; gap: 12px; padding-bottom: 16px; }
  .marca-simbolo { width: 48px; height: 48px; flex-basis: 48px; border-radius: 14px 14px 14px 4px; }
  .marca-simbolo span { font-size: 30px; }
  .marca-simbolo i { width: 20px; height: 20px; font-size: 11px; }
  .titulo { font-size: 1.45rem; }
  .subtitulo { font-size: .82rem; }
  .lema { font-size: .55rem; }
  .marca-sello { display: none; }
  .workspace-grid { grid-template-columns: minmax(0, 1fr); gap: 13px; margin-top: 14px; }
  .panel-central { grid-row: 1; padding: 18px 15px 21px; }
  .panel-motor { grid-row: 2; }
  .panel-guia { grid-row: 3; display: block !important; }
  .panel-lateral { padding: 18px; }
  .panel-guia .guia-paso { margin-top: 14px; }
  .panel-guia .movil-card { display: none; }
  .panel-guia .movil-nota { display: block; text-align: left; }
  .centro-encabezado h2 { font-size: 1.12rem; }
  .estado-en-linea { font-size: .65rem; }
  .entrada .q-field__native { font-size: 1.3rem; }
  .fila-accion { gap: 9px; }
  .teclado { gap: 6px; }
  .tecla { min-height: 48px; }
  .recursos-estudio { grid-template-columns: 1fr; gap: 14px; padding: 17px; }
  .recursos-estudio h2 { font-size: .95rem; }
  .frase-estudio { margin-top: 2px; }
}
"""
