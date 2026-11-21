# ROADMAP

Proyecto a largo plazo (4–5 años). Meta: llegar a resolver tanto o más que Photomath, con identidad propia:
español primero, enfoque tipo Baldor, y explicar **el porqué** de cada paso.

## Estado

### Etapa 1 — Aritmética básica
- [x] Base del proyecto: estructura, formato común de pasos (`Paso`/`Solucion`), errores en español
- [x] Parser (símbolos ×, ÷, −, potencias, decimales con punto o coma, multiplicación implícita)
- [x] Jerarquía de operaciones paso a paso (paréntesis, potencias, × ÷, + −)
- [x] Fracciones exactas (suma/resta con mcm, producto, división) y decimales exactos
- [x] Pruebas: casos fijos + miles de expresiones al azar contra Python + invariante de pasos
- [x] Simplificación de fracciones explicada paso a paso (mcd); `a/b` con enteros se trata como fracción
- [x] Números mixtos (3 1/2), porcentajes (20% de 150) y raíces exactas (√, ∛, ∜), con teclas en la web
- [ ] Mostrar fracciones también al escribir (entrada visual numerador/denominador)
- [x] Operaciones "a mano" (suma, resta, multiplicación y división larga en columnas, con decimales)
- [x] Primera interfaz web (NiceGUI): campo, teclado de símbolos, ejemplos, pasos con el "porqué", modo "un paso a la vez", modo oscuro, móvil

### Etapa 2 — Ecuaciones lineales de una variable
- [x] Parser con variable `x` (una letra; `2x` = 2·x; `x²` se detecta como no lineal)
- [x] Solucionador con pasos ("restamos 3 en ambos lados…"), casos sin solución e infinitas soluciones, y comprobación
- [ ] Ecuaciones con la incógnita en el denominador (`3/x = 2`)
- [x] Ecuaciones literales: despejar una letra de una fórmula (`despejar t en v = d/t`), con SymPy, supuestos y comprobación
- [ ] Despejar letras con potencias o raíces (`despejar r en A = πr²` → r = √(A/π))
- [ ] Letras con subíndices (`x0`, `v1`) y letras griegas
- [x] Desigualdades lineales (`2x + 3 < 11`, `−2x + 1 ≥ 7`): invierten el símbolo al dividir entre un negativo y al leer al revés; intervalo y comprobación
- [x] Método mejorado (idea tomada de comparar con ChatGPT): x donde queda positiva, operación escrita en los dos lados, distributiva aparte
- [ ] Desigualdades dobles (`1 < x < 5`) y recta numérica dibujada

### Etapa 3 — Álgebra tipo Baldor
- [x] Base para escribir álgebra (`motor/expr.py`): polinomios, factorizaciones, fracciones y radicales dibujados como en un libro, y releíbles por el parser
- [x] Polinomios: quitar paréntesis, distributiva, términos semejantes, ordenados de mayor a menor grado
- [x] Productos notables (cuadrado y cubo de binomio, Newton, trinomio al cuadrado, suma por diferencia, término común), con su fórmula y los valores puestos
- [x] Factorización por casos (factor común, diferencia de cuadrados, trinomios, cubos, agrupación) hasta que sea irreducible
- [x] Fracciones algebraicas: simplificar, sumar, restar, multiplicar y dividir, con restricciones (`x ≠ 3`)
- [x] Radicales con números: simplificar `√12 = 2√3`, operar, racionalizar (incluido el conjugado) y decimales aproximados
- [x] Exponentes fraccionarios (`8^(1/3) = 2`, `2^(1/2) = √2`): son raíces
- [ ] División de polinomios (división larga y por Ruffini/división sintética)
- [ ] Radicales con letras (`√(x²y)`) y de índice mayor que 4
- [ ] Ecuaciones con fracciones algebraicas (`1/(x − 1) + 1/(x + 1) = 1`) y con radicales
- [ ] Polinomios con coeficientes decimales mostrados en decimales (hoy salen como fracciones)

### Publicación en internet
- [x] Preparada para Render: `render.yaml`, arranque estándar con uvicorn (`asgi.py`, con mensajes de diagnóstico por etapa), dirección `/salud`, `.gitignore`
- [x] Primer intento de despliegue: «Timed out» en el health check; se cambió a `uvicorn asgi:app` y se agregó diagnóstico para ver dónde se queda
- [x] Resolución en un hilo con tiempo máximo (20 s) y exponentes limitados en el álgebra, para que un ejercicio pesado no congele a los demás
- [x] El servidor «calienta» SymPy al arrancar: la primera persona no espera de más
- [ ] Subirla a GitHub y publicarla en Render (la guía está en el README)
- [ ] Probar en un celular real, en Safari y en Firefox
- [ ] Dominio propio (opcional) y plan de pago si la usan muchos estudiantes (el gratis se «duerme» a los 15 min)

### Etapa 4 — Ecuaciones cuadráticas y sistemas
### Etapa 5 — Derivadas e integrales
### Más adelante
- [ ] Reconocimiento por foto (pieza aparte y difícil)
- [ ] Modo práctica: generar ejercicios parecidos para que el estudiante intente solo
- [ ] Publicar (hosting, cuentas, límites de uso)
- [ ] Revisar la interfaz en celular real y en Safari/Firefox (solo se revisó con Chromium)

## Decisiones tomadas

| Decisión | Por qué |
|---|---|
| Python | Es el que tiene SymPy (matemática simbólica); Java habría obligado a programar todo el motor |
| NiceGUI para la web | Ya lo conoces del proyecto de matrices; todo en Python. Si algún día se necesita más control, el motor no cambia: solo se reemplaza `web/` |
| Web primero | Se publica casi gratis después; mismo código puede ser app de escritorio o celular más adelante |
| Motor sin dependencias en la etapa 1 | Más simple y rápido de probar; SymPy entra con el álgebra |
| `Fraction` en vez de `float` | Resultados exactos, sin errores de redondeo |
| Un único formato de `Paso` para todos los solucionadores | La interfaz no cambia al agregar ejercicios |
| Igual precedencia para `2(3+4)` que para `×` | Es lo que hacen casi todas las calculadoras; `8 ÷ 2(2+2) = 16` |
| `/` entre enteros = fracción; `÷` y `:` = división | Es como lo escribe y lo lee un estudiante; el orden normal se respeta (`2^6/3` = (2^6)/3) |
| Columnas dibujadas como texto (`pizarra`) | Se dibuja igual en web, terminal y mañana PDF; cada paso guarda su propio dibujo |
| División larga: 4 decimales, cortados | Evita redondeos engañosos; avisa cuando la división no termina |
| Columnas solo con números positivos | Los negativos se explican mejor con la ley de signos (aritmética normal) |
| Un signo `=` activa el solucionador de ecuaciones solo | Sin interruptores extra: la escritura ya dice qué es |
| La solución se comprueba con el motor de aritmética | Es un segundo camino de cálculo: un paso mal hecho se detecta |
| Teclas virtuales para los símbolos que no existen en teclados (∛ ∜ √ % x =) | Pedido por el usuario: ni el PC ni el celular los traen |
| Las x se juntan donde su coeficiente queda positivo | Evita dividir entre un negativo, que es donde más se equivocan los estudiantes |
| Cada operación se escribe en los dos lados antes de simplificar | Se ve por qué "se hace lo mismo en ambos lados" |
| Desigualdades: la comprobación prueba la frontera y un número de la solución | Verifica el sentido del símbolo, que es el error clásico |
| SymPy entra solo para despejar fórmulas, y se carga cuando se usa | Los coeficientes ahora son expresiones con letras; la app y la aritmética no se vuelven más lentas |
| Las letras de una fórmula salen en el orden en que las escribió el estudiante, los términos positivos primero | Se lee como un libro (`u − f`, `3 − y`) y no en orden alfabético |
| `20%` = 20/100 y «de» = multiplicar; `3 1/2` = 3 + 1/2 | Es como se enseña en la escuela; cada caso está explicado paso a paso |
| `a ÷ b/c` se lee de izquierda a derecha | Igual que Python y las calculadoras; se usa paréntesis para dividir entre fracciones |

| `expr.py` guarda la FORMA que se muestra, y SymPy solo calcula | SymPy simplifica solo `(x−3)(x+3)/(x−3)` al crearlo; para explicar hay que poder escribir lo que no está simplificado |
| El texto dibujado debe volver a leerse igual | Se prueba con miles de expresiones: dibujar → leer con el parser → mismo valor; así ningún paso muestra algo distinto de lo calculado |
| Polinomios de mayor a menor grado; en las fórmulas, positivos primero | Es el orden de Baldor para el álgebra, y el que se lee mejor en una fórmula de física |
| La factorización repite los casos del libro, y SymPy solo es el plan B («método avanzado») | El estudiante ve el caso que aplica, no una caja negra |
| Cada resultado se verifica con números sin pasar por SymPy | Segundo camino de cálculo independiente; un error del motor se detecta en vez de mostrarse |
| `a/b ÷ c/d` se lee de izquierda a derecha | Igual que toda la calculadora; para dividir entre una fracción se usan paréntesis |
| Un exponente fraccionario es una raíz | Es como se enseña: `8^(1/3)` es ∛8; evita tener dos mecanismos distintos |
| Las raíces no exactas ya no son un error: se simplifican como radicales | Lo que antes se rechazaba ahora tiene respuesta (`√12 = 2√3`) |

## Ideas guardadas
- Mostrar el valor decimal de un radical con más cifras si el estudiante lo pide.
- Dibujar la factorización como «árbol» de factores.
- Modo «verifica mi resultado»: el estudiante escribe su respuesta y la calculadora dice si está bien y dónde se equivocó.
- Fórmulas de física e ingeniería industrial como ejemplos (con nombres: velocidad, fuerza…).
- Aceptar la letra a despejar al final como "para t" o "t = ?".
- Dibujar la recta numérica de las desigualdades (círculo abierto o cerrado).
- Pasos más cortos opcionales (modo "resumen") para quien ya domina el método.
- Mensaje más claro cuando el exponente es demasiado grande (`5^5^5`): decir qué exponente fue el problema.
- Aceptar `27^(1/3)` y `raiz(27; 3)` (raíces de cualquier índice) apoyándose en las raíces exactas.
- Método alterno para ecuaciones con fracciones: multiplicar todo por el mcm de los denominadores.
- Mejoras visuales (colores, alineación de los interruptores): pedidas para el final.
- Columnas: detectar el período de los decimales que se repiten (1 ÷ 3 = 0.3̅) en vez de cortar en 4.
- Columnas: botón "ver en columnas" junto al resultado de una operación simple.
- Exportar la pizarra a PDF para imprimir.
- Teclado: insertar el símbolo en la posición del cursor (hoy se agrega al final).
- Guardar historial de ejercicios resueltos.
- Compartir un ejercicio con enlace: hoy se puede abrir con `/?q=...`, pero la página no actualiza la dirección al resolver.
- Decidir cómo escribir fracciones en la interfaz (hoy `1/2` es una división).
- ¿Separador decimal con coma como opción? (`numeros.SEPARADOR_DECIMAL`)
- Resaltar en pantalla el trozo que se resolvió en cada paso (el campo `operacion` ya lo trae).
