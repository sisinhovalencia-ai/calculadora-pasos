# Calculadora paso a paso

Motor matemático que resuelve ejercicios **explicando cada paso**, en español.
Proyecto a largo plazo: empieza por aritmética básica y crece (ecuaciones, álgebra tipo Baldor, derivadas, integrales…).

> Cambia el nombre de la carpeta/proyecto cuando tengas el definitivo. Nada en el código depende de él.

## Instalar (una sola vez)

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows (en Mac/Linux: source .venv/bin/activate)
pip install -r requirements-dev.txt
```

## Probarlo

**En el navegador:**

```bash
python main.py                    # y abre http://localhost:8000
```

También acepta un ejercicio en la dirección: `http://localhost:8000/?q=1/2+1/3`

**En la terminal:**

```bash
python cli.py "2 + 3 × (4 − 1)^2"        # resuelve y muestra los pasos
python cli.py "8 ÷ 2(2+2)" --porque      # agrega el "porqué" de cada paso
python cli.py "1/2 + 1/3" --json         # salida JSON (lo que usará la web)
python cli.py "7845 ÷ 12" --columnas     # a mano, en columnas (suma, resta, ×, ÷ larga)
python cli.py "2x + 3 = 11"              # ecuaciones: basta con escribir el signo =
python cli.py "−2x + 1 ≥ 7"             # desigualdades: <  >  ≤  ≥  (también <= y >=)
python cli.py "despejar t en v = d/t"   # despejar una letra de una fórmula
python cli.py                            # modo interactivo
```

Pruebas (necesita `pip install -r requirements-dev.txt`):

```bash
python -m pytest
```

El motor de **aritmética, columnas, ecuaciones y desigualdades** no depende de ninguna librería (solo Python 3.10+). El **álgebra** (fórmulas, polinomios, factorización, fracciones algebraicas y radicales) usa SymPy, que se carga solo cuando se usa. La web usa NiceGUI y latex2mathml.

## Cómo está organizado

```
motor/
  errores.py     errores con mensajes en español para el estudiante
  numeros.py     formato de números exactos (enteros, fracciones, decimales)
  arbol.py       el árbol de la expresión (Num, Neg, Paren, BinOp)
  parser.py      texto -> árbol (acepta × ÷ − · : ** y coma decimal, 2(3+4)…)
  render.py      árbol -> texto plano / LaTeX
  pasos.py       ★ EL FORMATO COMÚN: Paso y Solucion
  aritmetica.py  solucionador de aritmética (jerarquía de operaciones)
  columnas.py    operaciones "a mano": suma, resta, multiplicación y división larga en columnas
  ecuaciones.py  ecuaciones y desigualdades lineales de una incógnita (2x + 3 = 11, 2x + 3 < 11), con comprobación
  formulas.py    despejar una letra de una fórmula (despejar t en v = d/t); usa SymPy
  expr.py        ★ expresiones algebraicas para ESCRIBIR pasos (x² + 5x + 6, (x − 3)(x + 3), 2√3): dibuja como un libro
  algebra.py     comandos (factorizar, desarrollar, simplificar), libreta de pasos y verificación numérica
  polinomios.py  desarrollar y reducir: productos notables, distributiva, términos semejantes
  factorizacion.py  factorización por casos (factor común, diferencias de cuadrados, trinomios, agrupación, cubos)
  fracciones_alg.py fracciones algebraicas: simplificar, sumar, restar, multiplicar, dividir (con restricciones x ≠ …)
  radicales.py   radicales con números: √12 = 2√3, operar, racionalizar, exponentes fraccionarios
web/
  app.py         la página (solo dibuja una `Solucion`; no sabe de matemática)
  estilos.py     colores y diseño (hoja de cuaderno cuadriculado); modo oscuro automático
  formulas.py    LaTeX -> MathML y texto seguro (todo pasa por escape)
main.py          arranca la web: python main.py
cli.py           para probar desde la terminal
tests/           pruebas del motor y de la web
requirements.txt        librerías de la app
requirements-dev.txt    + lo necesario para las pruebas
ROADMAP.md       qué falta, decisiones tomadas e ideas guardadas
```

Regla: `motor/` nunca importa nada de `web/`. Así la misma lógica sirve para web, app o celular.

## La idea central

Todo solucionador recibe texto y devuelve una `Solucion` hecha de `Paso`s (ver `motor/pasos.py`).
La pantalla (`web/`) solo sabe dibujar ese formato, así que **agregar un tipo de ejercicio nuevo no obliga a tocar la interfaz**.

Cada `Paso` trae: `explicacion` (qué se hizo), `motivo` (por qué ahora), `operacion`, `resultado_parcial`,
`expresion` (cómo queda todo) y `latex`.

## Cómo agregar un tipo de ejercicio nuevo (ej. ecuaciones lineales)

1. Crea `motor/ecuaciones.py` con una función `resolver_ecuacion(texto) -> Solucion` (mismo formato de `Paso`).
2. Si necesita símbolos (x), amplía el parser o crea uno propio; no rompas el de aritmética.
3. Escribe primero las pruebas en `tests/`: casos fijos + comparación contra una fuente fiable
   (Python con `Fraction` para aritmética; SymPy para álgebra).
4. Mantén la **invariante de pasos**: cada paso, vuelto a resolver, debe dar el mismo resultado final.
5. Anota en `ROADMAP.md` qué quedó hecho y las decisiones que tomaste.

## Convenciones (para no confundirse en el futuro)

- Todo es **exacto** (`Fraction`): `0.1 + 0.2` da exactamente `0.3`.
- `-3^2` = −9 y `(-3)^2` = 9. `2^3^2` = 2^(3^2) = 512.
- `8 ÷ 2(2+2)` = 16: la multiplicación implícita tiene la misma precedencia que `×` (igual que casi todas las calculadoras).
- Los decimales se muestran como decimales solo si el estudiante escribió decimales; si no, como fracción.
- **`/` entre dos enteros es una fracción** (`1/2`, `6/3`): se muestra tal cual y, si se puede simplificar, tiene su propio paso.
  **`÷` y `:` son siempre una división.** Se respeta el orden normal: `2^6/3` es (2^6)/3 y `3/4^2` es 3/(4^2).
- Con decimales en el ejercicio, la barra `/` se queda como división (no se convierte en fracción).
- **Orden normal, de izquierda a derecha:** `a ÷ b/c` es (a ÷ b)/c, igual que en Python y en las calculadoras.
  Para dividir entre una fracción escribe paréntesis: `a ÷ (b/c)`. La línea "Ejercicio" muestra cómo se interpretó.
- **Porcentajes:** `20%` significa 20/100. «de» significa multiplicar (`20% de 150`). Un porcentaje suelto vale su fracción:
  `50 + 10%` es 50 + 1/10 (no como las calculadoras de bolsillo, que suman el 10 % de 50).
- **Números mixtos:** `3 1/2` (con espacio) es 3 + 1/2. `-3 1/2` es −(3 1/2). No se aceptan seguidos de `^` (`3 1/2^2` es ambiguo).
- **Raíces:** `√`, `∛`, `∜` (hay una tecla para cada una), `raiz( )`, `raíz( )` y `sqrt( )`. Se aplican al número o paréntesis que sigue:
  `√9^2` es (√9)^2 y `2√9` es 2 × √9. Por ahora **solo raíces exactas** (√49, √(9/16), ∛(−27)).
- Mensajes de error siempre en español y entendibles; nunca trazas técnicas en pantalla.

## Ecuaciones y desigualdades lineales

Basta escribir un signo `=` (o `<`, `>`, `≤`, `≥`; también `<=` y `>=`): la calculadora decide sola qué es, sin
interruptores. Una sola incógnita (cualquier letra, normalmente `x`) y de primer grado:

```
2x + 3 = 11        3x − 5 = 2x + 7       2(x + 3) = 14       x/2 + 1 = 5
2x + 3 < 11        −2x + 1 ≥ 7           3(x − 1) > 2x + 4   5 < 2x + 1
```

**El método** (el de la escuela, con tres cuidados didácticos):
1. La propiedad distributiva y la reducción de términos semejantes van en pasos **separados**.
2. Las incógnitas se juntan **donde su coeficiente queda positivo**, así casi nunca hay que dividir entre un negativo.
   Si la x queda a la derecha, al final se lee la igualdad al revés.
3. Cada operación se muestra **escrita en los dos lados** (en gris) antes de simplificarla:
   `2x + 2 − 3x = 3x − 9 − 3x` → `−x + 2 = −9`. Así se ve por qué "se hace lo mismo en ambos lados".

**Desigualdades:** el símbolo se **invierte** al dividir entre un número negativo (`−2x ≥ 6` → `x ≤ −3`) y al leerla
al revés (`3 > x` → `x < 3`); cada vez se explica. El resultado trae el **intervalo** (`(−∞, −3]`) y dice si el número
frontera cuenta o no. La comprobación prueba la frontera y un número de la solución.

Casos especiales: **sin solución** (`x + 1 = x + 2`), **infinitas soluciones** (`2x + 2 = 2(x + 1)`) y, en desigualdades,
**todos los números reales** (`2x + 3 > 2x + 1`).
Siempre termina con una **comprobación** calculada con el motor de aritmética (otro camino de cálculo), así que un paso
mal hecho se detectaría en vez de mostrarse.

- `2x` significa 2 × x. `x²` y `x^2` se leen como x al cuadrado y dan el aviso "no es lineal".
- Por ahora no resuelve: la x en un denominador, en una raíz o en un exponente (`3/x = 2`, `2^x = 8`), de segundo grado,
  desigualdades dobles (`1 < x < 5`) ni con dos incógnitas. Dan un mensaje claro.
- Con decimales, los coeficientes se muestran en decimales; si no, en fracciones.

## Despejar una letra de una fórmula

Se escribe **«despejar» + la letra + la fórmula**, en el orden que quieras:

```
despejar t en v = d/t          despejar h en A = b·h/2         despejar w en P = 2l + 2w
v = d/t, despejar d            despejar C en F = 9C/5 + 32     despejar r en C = 2πr
```

Las demás letras se tratan como números que no conocemos. Se aceptan letras pegadas (`ma` = m·a), la constante `π`
y fracciones con letras (`d/t`). Los pasos son los del cuaderno: propiedad distributiva, **quitar denominadores**
(multiplicando los dos lados), juntar los términos con la letra en un lado, sacar **factor común**, dividir entre el
coeficiente y simplificar. Cada operación se muestra escrita en los dos lados (en gris). Si la letra queda a la derecha,
se lee la igualdad al revés.

- Al final aparece una **nota con los supuestos**: "Se supone que t, v no valen 0" (no se puede dividir entre 0).
- La comprobación es independiente: reemplaza la respuesta en la fórmula original y la compara con el resolvedor de SymPy.
- La letra a despejar tiene que ser de **primer grado** (después de quitar los denominadores). No despeja letras
  elevadas a una potencia o dentro de una raíz (`x² = a`), ni subíndices (`x0`): usa letras distintas.
- Una fórmula con **una sola letra** se resuelve como ecuación normal.
- Atención: «de» (dos letras pegadas) se lee como la palabra "de" (multiplicar); para d·e escribe `d·e` o `d e`.
- SymPy se instala con `requirements.txt` pero **solo se carga cuando despejas una fórmula**: arrancar la app y
  resolver aritmética o ecuaciones no lo usa.

## Álgebra (Etapa 3, tipo Baldor)

Se pide con una palabra al principio, o simplemente escribiendo (la calculadora lo adivina):

| Escribes | Pasa esto |
|---|---|
| `(x + 3)²`, `(2x + 3)(2x − 3)`, `(3x² + 2x) − (x² − 5x)` | Polinomios: producto notable o distributiva, y términos semejantes |
| `factorizar x² − 9` | Factorización por casos |
| `(x² − 9)/(x − 3)` o `simplificar …` | Fracciones algebraicas |
| `desarrollar …`, `reducir …` | Fuerza el desarrollo (útil con `x² + 5x + 6`, que sola ya está reducida) |
| `√12`, `√50 + √8`, `1/√2`, `8^(1/3)` | Radicales (lo que la aritmética rechazaba por «no exacta») |

Las teclas `²`, `³`, `factorizar`, `desarrollar` y `simplificar` están en el teclado de la pantalla.

**Polinomios y productos notables.** Reconoce y nombra: cuadrado y cubo de un binomio, binomio a una potencia (Newton),
cuadrado de un trinomio, suma por diferencia y binomios con un término común. Muestra la fórmula (en gris), la fórmula
con los valores puestos (`a = 2x y b = 3`) y luego las operaciones. Lo que no es notable se resuelve con la propiedad
distributiva y juntando términos semejantes. Si escribes un polinomio ya reducido sin decir nada, te sugiere `factorizar`.

**Factorización.** Casos, en este orden: factor común → diferencia de cuadrados → suma o diferencia de cubos →
trinomio cuadrado perfecto → `x² + bx + c` (también con `x⁴`, `x⁶`… y con dos letras) → `ax² + bx + c` (descompone el término
del medio y agrupa, en 3 pasos) → cubo perfecto → agrupación. Cada factor se vuelve a revisar hasta que ya no se pueda
(irreducible). Si ningún caso del libro aplica pero sí hay factores (raíces racionales), lo dice como «método avanzado».
Un polinomio que no se puede factorizar (`x² + 1`) lo dice con claridad.

**Fracciones algebraicas.** Factoriza (con los mismos casos), cancela factores comunes y avisa de los valores prohibidos:
«Se supone que x ≠ 3». Suma y resta con denominador común (mínimo común múltiplo, cuidando el signo −), multiplica y divide.
`a/b ÷ c/d` sin paréntesis se lee de izquierda a derecha, como en toda la calculadora: para dividir entre una fracción,
ponla entre paréntesis: `((x+1)/(x−1)) ÷ ((x+2)/(x−1))`.

**Radicales** (índices 2, 3 y 4, solo con números): saca de la raíz lo que se puede (descomponiendo en primos: `12 = 2²·3`),
junta radicales semejantes, multiplica raíces, racionaliza denominadores (`1/√2`, y con el **conjugado** `3/(2 + √5)`) y
simplifica fracciones. Da el valor decimal aproximado. Un **exponente fraccionario es una raíz**: `8^(1/3) = 2`, `2^(1/2) = √2`.

**Cómo se verifica todo esto:** cada resultado se evalúa con números (sin usar SymPy) contra lo que escribió el estudiante, y las
pruebas comparan miles de expresiones al azar contra SymPy y comprueban que cada paso intermedio valga lo mismo que lo escrito.

## Publicarla en internet (Render)

Render publica la aplicación **desde un repositorio de GitHub**, así que primero hay que subir el proyecto ahí (una sola vez).
Todo lo necesario ya está en el proyecto: `render.yaml` (la configuración), `asgi.py` (el arranque para servidores),
`.gitignore` (qué no se sube), `.python-version`, `requirements.txt` y la dirección `/salud` que Render consulta para saber
que la app está viva. En tu computador sigues usando `python main.py`; en Render se usa `python -m uvicorn asgi:app`.

**1. Subirla a GitHub** (una sola vez; necesitas tener Git instalado: https://git-scm.com). Abre la terminal de VS Code
dentro de la carpeta del proyecto:

```
git init
git add .
git commit -m "Calculadora paso a paso"
git branch -M main
```

En https://github.com crea un repositorio nuevo (botón **New**), con nombre `calculadora-pasos`, **Private** (privado), y **sin**
README ni .gitignore (ya los tienes). GitHub te muestra su dirección; úsala aquí:

```
git remote add origin https://github.com/TU_USUARIO/calculadora-pasos.git
git push -u origin main
```

Si te pide iniciar sesión, usa el navegador que te abre (o un *token* personal de GitHub como contraseña).

**2. Publicarla en Render.** En https://render.com crea una cuenta con tu GitHub. Luego **New + → Blueprint**, elige el
repositorio `calculadora-pasos` y confirma. Render lee `render.yaml`, instala las librerías y arranca la app (la primera vez
tarda unos minutos). Al terminar te da una dirección como `https://calculadora-pasos.onrender.com`: ábrela en tu celular.

Si prefieres hacerlo a mano (New + → Web Service): *Runtime* Python, *Build Command* `pip install -r requirements.txt`,
*Start Command* `python -m uvicorn asgi:app --host 0.0.0.0 --port $PORT --log-level info`, *Health Check Path* `/salud`, plan **Free**
y las variables de entorno `PYTHON_VERSION` = `3.12.7` y `PYTHONUNBUFFERED` = `1`.

**Si el despliegue falla** («Deploy failed» o «Timed out»): abre **Logs** y busca las líneas que empiezan con `[asgi +…]`.
Cada una marca una etapa del arranque, y la **última** que aparece dice dónde se quedó:

| Última línea que ves | Significa |
|---|---|
| ninguna `[asgi …]` | Render no llegó a ejecutar `asgi.py`: revisa el *Start Command* en **Settings** |
| `Python 3.12.x · PORT=10000 · RENDER=true` | Arrancó Python pero se quedó cargando FastAPI |
| `NiceGUI cargado` | Se quedó cargando el motor de la calculadora |
| `Listo: la aplicación está montada…` y luego `Uvicorn running on http://0.0.0.0:10000` | Todo bien: ya debería responder `/salud` |

Copia esas líneas (y cualquier `Traceback`) y con eso se encuentra el problema.

**3. Actualizarla después.** Cada vez que cambies algo y quieras que se vea en internet:

```
git add .
git commit -m "Describe lo que cambiaste"
git push
```

Render detecta el `push` y publica la versión nueva solo (`autoDeploy`).

**Qué esperar del plan gratis:**
- Si nadie la usa durante ~15 minutos, Render la «duerme»: el primer acceso siguiente tarda 30–60 segundos en despertarla.
  Después va rápido. Conviene abrirla un minuto antes de enseñarla.
- La app **no guarda ningún dato** de nadie (no hay cuentas ni base de datos): no hay nada privado que proteger.
- Cada ejercicio se resuelve en un hilo con un tiempo máximo de 20 s, y el álgebra limita los exponentes a 20, para que una
  expresión pesada no deje a los demás esperando.

**Probar el «modo nube» en tu computador** (escucha en todas las direcciones, como en Render):
`set RENDER=1 && set PORT=10000 && python main.py` (Windows) y abre http://localhost:10000/salud (debe decir `ok`).

## Operaciones en columnas ("a mano")

Se activan con el interruptor **"En columnas (a mano)"** de la web, o con `--columnas` en la terminal.
Una sola operación entre números positivos (con decimales): `4567 + 289`, `905 − 267`, `123 × 45`, `7845 ÷ 12`.

- **Suma:** de 2 a 5 sumandos, con llevadas. Las comas se alinean y se completa con ceros.
- **Resta:** con "pedir prestado" (incluidos los préstamos en cadena, como `1000 − 1`).
  Si el primero es menor, se resta al revés y se pone el signo menos.
- **Multiplicación:** una fila por cada cifra de abajo (corrida un lugar con ceros), luego se suman las filas.
  Con decimales se multiplica como enteros y al final se pone la coma.
- **División larga ("la casita"):** cifra por cifra, con el cociente creciendo a la derecha.
  Con decimales se mueve la coma en ambos números. Si sobra residuo, **sigue con decimales hasta 4 cifras**
  y avisa si no termina (se **corta**, no se redondea). Siempre muestra "cociente X y residuo Y" con enteros.
- Límites de tamaño: suma/resta hasta 15 cifras, multiplicación hasta 8 cifras por número,
  división de hasta 12 cifras entre un divisor de hasta 6.
- Cada paso trae una `pizarra` (ver `motor/pasos.py`): las líneas de texto tal como se ven en ese momento y
  las marcas de lo que se resalta. La web las dibuja en monoespaciado; mañana podrían exportarse a PDF.

## Notas de la interfaz

- Las fórmulas se dibujan con MathML (lo entienden Chrome, Edge, Firefox y Safari actuales): no hace falta internet para ellas.
- La tipografía (Atkinson Hyperlegible) se descarga de Google Fonts; sin internet se usa la del sistema y todo sigue funcionando.
- Las teclas especiales que no existen en los teclados del PC o del celular (`√ ∛ ∜ % de x = < > ≤ ≥`, un espacio y `despejar`) están en
  el teclado virtual de la web. Si agregas una tecla o un ejemplo, edita `TECLAS` / `EJEMPLOS` en `web/app.py`.
- Al pulsar "Resolver" la página baja sola hasta el resultado (en el celular quedaba fuera de la pantalla).
- Si el interruptor "En columnas (a mano)" está encendido y el ejercicio no es una sola operación (una raíz, una
  ecuación…), la pantalla lo dice y te indica apagarlo.
- Las pruebas de la web (`tests/test_web.py`) comprueban que la pantalla funciona; la apariencia se revisa a ojo.

## Límites conocidos (por ahora)

- Álgebra: la letra de las raíces no se soporta (`√x`), ni raíces de índice mayor que 4, ni exponentes que no sean enteros o 1/2, 1/3, 1/4.
- Factorización: coeficientes enteros (o fraccionarios con factor común); los trinomios `ax² + bx + c` con dos letras pasan por el «método avanzado».
- Fracciones algebraicas: sin raíces; una suma con muchos términos puede dar pasos largos.
- «de» pegado se lee como la palabra «de» (multiplicar); para d·e escribe `d·e`. Un subíndice (`x0`) no se soporta: usa letras distintas.
- Las fracciones se escriben con la barra (`1/2`); una entrada visual con numerador sobre denominador vendrá más adelante.
- Fracciones con numerador o denominador que no sean enteros escritos (por ejemplo `(1+1)/4`) se tratan como divisiones normales.
- Números gigantes (más de ~4000 cifras) se rechazan para no colgar ni romper la pantalla.
