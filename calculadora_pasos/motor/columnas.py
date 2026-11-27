"""Operaciones "a mano" en columnas, como se enseñan en la escuela.

    suma             345 + 78 + 1.5        (2 a 5 sumandos, con decimales)
    resta            905 − 267             (con "pedir prestado"; con decimales)
    multiplicación   123 × 45              (filas parciales + suma; con decimales)
    división larga   7845 ÷ 12             (la "casita"; sigue con decimales)

Cada paso trae una `pizarra`: las líneas de texto tal como se ven en ese momento
(con las llevadas, los préstamos, etc.) y las marcas de lo que se resalta.
Todo se alinea a la derecha porque se trabaja de derecha a izquierda.

El resultado siempre se comprueba en las pruebas contra la aritmética exacta de Python.
"""

import re
from fractions import Fraction

from .errores import ErrorDeEntrada, ErrorMatematico
from .pasos import Paso, Solucion

_MAX_CIFRAS_SUMA = 15
_MAX_SUMANDOS = 5
_MAX_CIFRAS_MULT = 8
_MAX_CIFRAS_DIVIDENDO = 12
_MAX_CIFRAS_DIVISOR = 6
_MAX_DECIMALES_ENTRADA = 6
_MAX_DECIMALES_COCIENTE = 4

_AYUDA = ("El método en columnas se usa con una sola operación entre números, por ejemplo: "
          "345 + 78, 905 − 267, 123 × 45 o 7845 ÷ 12 (sin paréntesis ni mezclar operaciones).")

_EQUIV = str.maketrans({"·": "×", "⋅": "×", "*": "×", ":": "÷", "/": "÷", "−": "-", "–": "-", "—": "-"})
_NUM = r"(?:\d+(?:[.,]\d+)?|[.,]\d+)"
_PATRON = re.compile(rf"^\s*{_NUM}(?:\s*[+\-×÷]\s*{_NUM})+\s*$")

_POS = ["unidades", "decenas", "centenas", "unidades de mil", "decenas de mil", "centenas de mil",
        "unidades de millón", "decenas de millón", "centenas de millón", "unidades de mil millones",
        "decenas de mil millones", "centenas de mil millones", "billones", "decenas de billón",
        "centenas de billón", "unidades de mil billones"]
_DEC = ["décimas", "centésimas", "milésimas", "diezmilésimas", "cienmilésimas", "millonésimas"]

_MOTIVO = {
    "suma": "Se empieza por la columna de la derecha porque las llevadas pasan hacia la izquierda.",
    "resta": "Se empieza por la derecha para poder pedir prestado a la columna de la izquierda cuando haga falta.",
    "mult": "Cada cifra de abajo vale diez veces más que la anterior, por eso cada fila se corre un lugar hacia la izquierda.",
    "div": "Se divide cifra por cifra de izquierda a derecha, porque cada residuo se convierte en decenas de la cifra siguiente.",
}


# ---------------------------------------------------------------------------
# Lectura de la operación
# ---------------------------------------------------------------------------

def _partir(s: str) -> tuple[str, str]:
    """'4,50' -> ('4', '50'); '.5' -> ('0', '5'); '007' -> ('7', '')."""
    ip, _, fp = s.replace(",", ".").partition(".")
    return (ip.lstrip("0") or "0"), fp


def _txt(ip: str, fp: str) -> str:
    return ip + ("." + fp if fp else "")


def _limpiar(s: str) -> str:
    """Quita ceros inservibles: '0.50' -> '0.5', '5.00' -> '5', '0007' -> '7'."""
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    s = s.lstrip("0")
    if s == "" or s.startswith("."):
        s = "0" + s
    return s


def _leer(texto: str):
    if texto is None or not texto.strip():
        raise ErrorDeEntrada("Escribe una operación para resolver.")
    t = texto.strip().translate(_EQUIV)
    if len(t) > 120:
        raise ErrorDeEntrada("La operación es demasiado larga.")
    if re.match(r"^\s*-", t) or re.search(r"[+\-×÷]\s*-", t):
        raise ErrorDeEntrada("Por ahora el método en columnas solo usa números positivos.")
    if not _PATRON.match(t):
        if re.fullmatch(rf"\s*{_NUM}\s*", t):
            raise ErrorDeEntrada("Escribe una operación entre dos números, por ejemplo 345 + 78.")
        raise ErrorDeEntrada(_AYUDA)
    numeros = re.findall(_NUM, t)
    ops = re.findall(r"[+\-×÷]", re.sub(_NUM, " ", t))
    if len(set(ops)) != 1:
        raise ErrorDeEntrada(_AYUDA)
    op = ops[0]
    if op == "+" and len(numeros) > _MAX_SUMANDOS:
        raise ErrorDeEntrada(f"Para sumar en columnas puedes poner hasta {_MAX_SUMANDOS} números.")
    if op != "+" and len(numeros) != 2:
        raise ErrorDeEntrada(_AYUDA)
    partes = [_partir(n) for n in numeros]
    for ip, fp in partes:
        if len(fp) > _MAX_DECIMALES_ENTRADA:
            raise ErrorDeEntrada(f"Usa como máximo {_MAX_DECIMALES_ENTRADA} cifras decimales.")
    return op, partes


# ---------------------------------------------------------------------------
# Nombres de columnas y dibujo de la pizarra
# ---------------------------------------------------------------------------

def _nombre(p: int) -> str:
    """p >= 0: unidades, decenas...; p < 0: décimas, centésimas..."""
    if p >= 0:
        return _POS[p] if p < len(_POS) else f"la posición {p + 1}"
    return _DEC[-p - 1] if -p - 1 < len(_DEC) else f"la posición decimal {-p}"


def _pizarra(filas, ancho: int, marcas=()) -> dict:
    """filas: [(prefijo de 2 caracteres, texto | None para una raya)].
    marcas: (fila, columna desde la izquierda del texto, cuántas columnas) - respecto al ancho `ancho`."""
    lineas = [pre + (("─" * ancho) if txt is None else txt.rjust(ancho)) for pre, txt in filas]
    return {"lineas": lineas, "marcas": [[i, 2 + c, 2 + c + n] for i, c, n in marcas]}


def _crudo(regla, explicacion, motivo, operacion, parcial, expresion, pizarra):
    return dict(regla=regla, explicacion=explicacion, motivo=motivo, operacion=operacion,
                parcial=parcial, expresion=expresion, pizarra=pizarra)


# ---------------------------------------------------------------------------
# Suma en columnas (también se usa dentro de la multiplicación)
# ---------------------------------------------------------------------------

def _expl_col_suma(dig, llevada, s, r, sal, nombre) -> str:
    if not dig:
        return f"No quedan más cifras: bajamos la llevada {llevada}."
    partes = " + ".join(str(d) for d in dig)
    if llevada:
        partes += f" + {llevada} (llevada)"
    if len(dig) == 1 and not llevada:
        return f"En la columna de las {nombre} solo hay un {dig[0]}: lo bajamos."
    texto = f"En la columna de las {nombre}: {partes} = {s}."
    return texto + (f" Escribimos {r} y llevamos {sal}." if sal else f" Escribimos {r}.")


def _sumar_columnas(sumandos, W, col_unidades, filas_arriba, signo_ultimo):
    """Suma `sumandos` (cadenas del mismo ancho W, con dígitos y espacios y quizá un '.').
    Devuelve (pizarra inicial, pasos crudos, texto del resultado sin limpiar)."""
    n = len(sumandos)
    base = len(filas_arriba)
    carry = [" "] * W
    res = [" "] * W

    def tablero(cols, res_txt=None):
        filas = list(filas_arriba) + [("  ", "".join(carry))]
        for i, s in enumerate(sumandos):
            filas.append(("+ " if (signo_ultimo and i == n - 1) else "  ", s))
        filas.append(("  ", None))
        filas.append(("  ", "".join(res) if res_txt is None else res_txt))
        marcas = []
        for c in cols:
            for fila in range(base + 1, base + n + 1):
                marcas.append((fila, c, 1))
            marcas.append((base + n + 2, c, 1))
            if carry[c] != " ":
                marcas.append((base, c, 1))
        return _pizarra(filas, W, marcas)

    inicial = tablero([])
    pasos = []
    llevada = 0
    for c in range(W - 1, -1, -1):
        chars = [s[c] for s in sumandos]
        if chars[0] == ".":
            res[c] = "."
            pasos.append(_crudo(
                "columna_suma",
                "Ya sumamos todas las cifras decimales. Ponemos la coma en el resultado, "
                "justo debajo de las demás comas.",
                _MOTIVO["suma"], ".", ".", "".join(res).strip(), tablero([c])))
            continue
        dig = [int(ch) for ch in chars if ch.isdigit()]
        if not dig and llevada == 0:
            continue
        s = sum(dig) + llevada
        r, sal = s % 10, s // 10
        res[c] = str(r)
        p = (col_unidades - c) if c <= col_unidades else -(c - col_unidades - 1)
        texto = _expl_col_suma(dig, llevada, s, r, sal, _nombre(p))
        llevada_entra = llevada
        llevada = sal
        if sal and c > 0:
            nc = c - 1
            if sumandos[0][nc] == ".":
                nc -= 1
            if nc >= 0:
                carry[nc] = str(sal)
        tab = tablero([c])   # resultado ya escrito y la nueva llevada visible
        sumandos_col = [str(d) for d in dig] + ([str(llevada_entra)] if llevada_entra else [])
        pasos.append(_crudo("columna_suma", texto, _MOTIVO["suma"], " + ".join(sumandos_col),
                            str(r), "".join(res).strip(), tab))
    return inicial, pasos, "".join(res).strip()


def _resolver_suma(partes):
    k = max(len(fp) for _, fp in partes)
    L = max(len(ip) for ip, _ in partes) + 1            # +1 columna libre para la llevada final
    W = L + (1 + k if k else 0)
    for ip, fp in partes:
        if len(ip) + len(fp) > _MAX_CIFRAS_SUMA:
            raise ErrorDeEntrada(f"Para sumar en columnas usa números de hasta {_MAX_CIFRAS_SUMA} cifras.")
    sumandos = [ip.rjust(L) + ("." + fp.ljust(k, "0") if k else "") for ip, fp in partes]
    inicial, pasos, res = _sumar_columnas(sumandos, W, L - 1, [], True)
    if k:
        intro = ("Escribimos los números uno debajo del otro, alineando las comas, y completamos con "
                 "ceros para que todos tengan las mismas cifras decimales.")
    else:
        intro = ("Escribimos los números uno debajo del otro, alineados a la derecha: "
                 "unidades con unidades, decenas con decenas…")
    primero = _crudo("preparacion", intro, _MOTIVO["suma"], "", "", "", inicial)
    final_txt = _limpiar(res)
    nota = f"El resultado es {res}" + (f", que es lo mismo que {final_txt}" if final_txt != res else "") + "."
    ultimo = _crudo("resultado", nota, _MOTIVO["suma"], "", final_txt, res,
                    _pizarra(_filas_finales_suma(sumandos, res, W), W, []))
    return [primero] + pasos + [ultimo], final_txt


def _filas_finales_suma(sumandos, res, W):
    n = len(sumandos)
    filas = [("  ", " " * W)]
    for i, s in enumerate(sumandos):
        filas.append(("+ " if i == n - 1 else "  ", s))
    filas.append(("  ", None))
    filas.append(("  ", res))
    return filas


# ---------------------------------------------------------------------------
# Resta en columnas
# ---------------------------------------------------------------------------

def _resolver_resta(partes):
    (ipa, fpa), (ipb, fpb) = partes
    va = Fraction(f"{ipa}.{fpa or '0'}")
    vb = Fraction(f"{ipb}.{fpb or '0'}")
    negativo = va < vb
    if negativo:
        (ipa, fpa), (ipb, fpb) = (ipb, fpb), (ipa, fpa)
    k = max(len(fpa), len(fpb))
    L = max(len(ipa), len(ipb))
    if L + k > _MAX_CIFRAS_SUMA:
        raise ErrorDeEntrada(f"Para restar en columnas usa números de hasta {_MAX_CIFRAS_SUMA} cifras.")
    W = L + (1 + k if k else 0)
    mi = ipa.rjust(L) + ("." + fpa.ljust(k, "0") if k else "")
    su = ipb.rjust(L) + ("." + fpb.ljust(k, "0") if k else "")
    pres = [" "] * W
    res = [" "] * W

    def tablero(cols, res_txt=None, signo="  "):
        filas = [("  ", "".join(pres)), ("  ", mi), ("− ", su), ("  ", None),
                 (signo, "".join(res) if res_txt is None else res_txt)]
        marcas = []
        for c in cols:
            marcas += [(1, c, 1), (2, c, 1), (4, c, 1)]
            if pres[c] != " ":
                marcas.append((0, c, 1))
        return _pizarra(filas, W, marcas)

    pasos = []
    primero_txt = ""
    if negativo:
        primero_txt = (f"{_txt(*partes[0])} es menor que {_txt(*partes[1])}, así que el resultado será negativo. "
                       f"Restamos al revés ({_txt(ipa, fpa)} − {_txt(ipb, fpb)}) y al final ponemos el signo menos. ")
    primero_txt += ("Escribimos el número mayor arriba y el menor debajo, alineados a la derecha"
                    + (", con las comas una debajo de la otra y ceros para igualar los decimales." if k else
                       ": unidades con unidades, decenas con decenas…"))
    pasos.append(_crudo("preparacion", primero_txt, _MOTIVO["resta"], "", "", "", tablero([])))

    prestamo = 0
    for c in range(W - 1, -1, -1):
        if mi[c] == ".":
            res[c] = "."
            pasos.append(_crudo("columna_resta",
                                "Ya restamos todas las cifras decimales. Ponemos la coma en el resultado.",
                                _MOTIVO["resta"], ".", ".", "".join(res).strip(), tablero([c])))
            continue
        da = int(mi[c]) if mi[c].isdigit() else 0
        db = int(su[c]) if su[c].isdigit() else 0
        if mi[c] == " " and su[c] == " ":
            continue
        p = (L - 1 - c) if c < L else -(c - L)
        nombre = _nombre(p)
        eff = da - prestamo
        if eff >= db:
            r = eff - db
            if prestamo:
                texto = (f"Columna de las {nombre}: antes prestamos 1, así que el {da} queda en {eff}. "
                         f"Restamos {eff} − {db} = {r}.")
            else:
                texto = f"Columna de las {nombre}: restamos {da} − {db} = {r}."
            sale = 0
        else:
            top = eff + 10
            r = top - db
            if prestamo and da == 0:
                texto = (f"Columna de las {nombre}: aquí hay 0 y ya habíamos prestado 1, así que pedimos prestado "
                         f"otra vez a la columna de la izquierda: ahora tenemos 9. Restamos 9 − {db} = {r}.")
            elif prestamo:
                texto = (f"Columna de las {nombre}: antes prestamos 1, así que el {da} queda en {eff}; {eff} es "
                         f"menor que {db}, entonces pedimos prestado 1 a la columna de la izquierda (vale 10): "
                         f"{top} − {db} = {r}.")
            else:
                texto = (f"Columna de las {nombre}: {da} es menor que {db}, así que pedimos prestado 1 a la "
                         f"columna de la izquierda (vale 10): {top} − {db} = {r}.")
            sale = 1
        res[c] = str(r)
        if sale and c > 0:
            nc = c - 1
            if mi[nc] == ".":
                nc -= 1
            if nc >= 0:
                pres[nc] = "1"
        operacion = f"{top if sale else eff} − {db}"      # tal como aparece en la explicación
        pasos.append(_crudo("columna_resta", texto, _MOTIVO["resta"], operacion, str(r),
                            "".join(res).strip(), tablero([c])))
        prestamo = sale

    crudo = "".join(res)
    # quitar ceros de la izquierda que no valen
    listo = list(crudo)
    for i, ch in enumerate(listo):
        if ch == "0" and i < (L - 1):
            listo[i] = " "
        elif ch != " ":
            break
    final_txt = _limpiar(crudo.strip())
    signo = "− " if negativo else "  "
    texto_final = (f"El resultado es {'−' if negativo else ''}{final_txt}"
                   + (" (negativo, porque restamos al revés)." if negativo else "."))
    pasos.append(_crudo("resultado", texto_final, _MOTIVO["resta"], "", ("−" if negativo else "") + final_txt,
                        ("−" if negativo else "") + final_txt,
                        tablero([], res_txt="".join(listo), signo=signo)))
    return pasos, ("-" if negativo else "") + final_txt


# ---------------------------------------------------------------------------
# Multiplicación en columnas
# ---------------------------------------------------------------------------

def _resolver_mult(partes):
    (ipa, fpa), (ipb, fpb) = partes
    t = len(fpa) + len(fpb)
    A = (ipa + fpa).lstrip("0") or "0"
    B = (ipb + fpb).lstrip("0") or "0"
    if len(A) > _MAX_CIFRAS_MULT or len(B) > _MAX_CIFRAS_MULT:
        raise ErrorDeEntrada(f"Para multiplicar en columnas usa números de hasta {_MAX_CIFRAS_MULT} cifras.")
    P = int(A) * int(B)
    Ps = str(P)
    pasos = []
    nota_comas = ""
    if t:
        nota_comas = (f" Ignoramos las comas por ahora: multiplicamos {A} × {B} como si fueran números enteros "
                      f"y al final pondremos la coma.")
    if P == 0:
        W = max(len(A), len(B))
        filas = [("  ", A.rjust(W)), ("× ", B.rjust(W)), ("  ", None), ("  ", "0".rjust(W))]
        pasos.append(_crudo("preparacion", "Cualquier número multiplicado por 0 da 0." + nota_comas,
                            _MOTIVO["mult"], "", "0", "0", _pizarra(filas, W, [])))
        return pasos, "0"

    W = max(len(Ps), len(A), len(B))
    fila_a, fila_b = A.rjust(W), B.rjust(W)
    arriba = [("  ", fila_a), ("× ", fila_b), ("  ", None)]
    carry = [" "] * W
    parciales = []                       # listas de caracteres (ancho W)

    def tablero_mult(marcas, extra=()):
        filas = [("  ", "".join(carry))] + [("  ", fila_a), ("× ", fila_b), ("  ", None)]
        for pr in parciales:
            filas.append(("  ", "".join(pr)))
        for e in extra:
            filas.append(e)
        return _pizarra(filas, W, marcas)

    pasos.append(_crudo(
        "preparacion",
        "Escribimos un número debajo del otro, alineados a la derecha. Multiplicaremos todo el número de arriba "
        "por cada cifra del de abajo, empezando por la derecha." + nota_comas,
        _MOTIVO["mult"], "", "", "", tablero_mult([])))

    nb = len(B)
    for j in range(nb):
        dj = int(B[nb - 1 - j])
        fila = [" "] * W
        for z in range(j):
            fila[W - 1 - z] = "0"
        parciales.append(fila)
        carry[:] = [" "] * W
        idx_fila = 4 + len(parciales) - 1       # índice de esta fila en el tablero (carry, A, B, raya, parciales…)
        nombre_j = _nombre(j)
        if j == 0:
            cab = f"Empezamos multiplicando todo el número de arriba por {dj}, la cifra de las {nombre_j}."
        else:
            cab = (f"Ahora multiplicamos por {dj}, la cifra de las {nombre_j}. Como vale {10 ** j} veces más, "
                   f"la fila empieza con {j} cero{'s' if j > 1 else ''} a la derecha.")
        if dj == 0:
            for i in range(len(A) + j):
                fila[W - 1 - i] = "0"
            pasos.append(_crudo("fila_mult",
                                cab + " Como la cifra es 0, toda la fila vale 0: la llenamos de ceros.",
                                _MOTIVO["mult"], "", "0", "".join(fila).strip(),
                                tablero_mult([(idx_fila, W - 1 - j, 1), (2, W - 1 - j, 1)])))
            continue
        pasos.append(_crudo("fila_mult", cab, _MOTIVO["mult"], "", "", "".join(fila).strip(),
                            tablero_mult([(2, W - 1 - j, 1)])))
        llevada = 0
        na = len(A)
        for i in range(na):
            da = int(A[na - 1 - i])
            prod = da * dj + llevada
            entra = llevada
            col = W - 1 - i - j
            ultima = i == na - 1
            if ultima and prod >= 10:
                fila[col] = str(prod % 10)
                fila[col - 1] = str(prod // 10)
                llevada = 0
                base = f"{da} × {dj}" + (f" + {entra} (llevada)" if entra else "")
                texto = f"{base} = {prod}. Como es la última cifra de arriba, escribimos {prod} completo."
                marcas = [(1, W - 1 - i, 1), (2, W - 1 - j, 1), (idx_fila, col - 1, 2)]
            else:
                fila[col] = str(prod % 10)
                llevada = prod // 10
                base = f"{da} × {dj}" + (f" + {entra} (llevada)" if entra else "")
                texto = f"{base} = {prod}. Escribimos {prod % 10}" + (f" y llevamos {llevada}." if llevada else ".")
                marcas = [(1, W - 1 - i, 1), (2, W - 1 - j, 1), (idx_fila, col, 1)]
                if entra:
                    marcas.append((0, W - 1 - i, 1))
                if llevada and not ultima:
                    carry[W - 2 - i] = str(llevada)
            op = f"{da} × {dj}" + (f" + {entra}" if entra else "")
            pasos.append(_crudo("fila_mult", texto, _MOTIVO["mult"], op, str(prod % 10),
                                "".join(fila).strip(), tablero_mult(marcas)))
        carry[:] = [" "] * W

    # sumar las filas (si hay más de una)
    filas_txt = ["".join(pr) for pr in parciales]
    if len(parciales) > 1:
        inicial, pasos_suma, res = _sumar_columnas(filas_txt, W, W - 1, arriba, False)
        pasos.append(_crudo("preparacion_suma",
                            "Ya tenemos todas las filas. Ahora las sumamos, columna por columna.",
                            _MOTIVO["suma"], "", "", "", inicial))
        pasos += pasos_suma
        producto = res.strip()
    else:
        producto = filas_txt[0].strip()
    assert producto == Ps, (producto, Ps)

    if t:
        digitos = Ps.rjust(t + 1, "0")
        final = digitos[:-t] + "." + digitos[-t:]
        ancho = max(W, len(final))
        filas = [("  ", fila_a), ("× ", fila_b), ("  ", None)]
        for pr in parciales:
            filas.append(("  ", "".join(pr)))
        if len(parciales) > 1:
            filas += [("  ", None), ("  ", producto)]
        filas.append(("= ", final))
        final_l = _limpiar(final)
        texto = (f"Contamos las cifras decimales de los dos números: {len(fpa)} + {len(fpb)} = {t}. "
                 f"Ponemos la coma {t} lugar{'es' if t > 1 else ''} desde la derecha: {Ps} → {final}.")
        if final_l != final:
            texto += f" Eso es lo mismo que {final_l}."
        pasos.append(_crudo("decimales", texto, _MOTIVO["mult"], "", final_l, final, _pizarra(filas, ancho, [])))
        return pasos, final_l

    filas = [("  ", fila_a), ("× ", fila_b), ("  ", None)]
    for pr in parciales:
        filas.append(("  ", "".join(pr)))
    if len(parciales) > 1:
        filas += [("  ", None), ("  ", producto)]
    pasos.append(_crudo("resultado", f"El resultado es {producto}.", _MOTIVO["mult"], "", producto,
                        producto, _pizarra(filas, W, [])))
    return pasos, producto


# ---------------------------------------------------------------------------
# División larga (la "casita")
# ---------------------------------------------------------------------------

def _simular_division(n_str: str, d: int):
    """Calcula todas las etapas de la división larga. Devuelve (etapas, decimales_usados)."""
    dig = [int(c) for c in n_str]
    cur, idx = 0, 0
    while idx < len(dig) and cur < d:
        cur = cur * 10 + dig[idx]
        idx += 1
    etapas, usados = [], 0
    while True:
        q = cur // d
        prod = q * d
        rem = cur - prod
        etapas.append(dict(cur=cur, q=q, prod=prod, rem=rem, fin=idx - 1))
        if idx < len(dig):
            etapas[-1]["trae"] = dig[idx]
            cur = rem * 10 + dig[idx]
            idx += 1
            continue
        if rem != 0 and usados < _MAX_DECIMALES_COCIENTE:
            usados += 1
            etapas[-1]["trae"] = 0
            cur = rem * 10
            idx += 1
            continue
        break
    return etapas, usados


def _resolver_division(partes):
    (ipa, fpa), (ipb, fpb) = partes
    m = max(len(fpa), len(fpb))
    N = int(ipa + fpa.ljust(m, "0"))
    D = int(ipb + fpb.ljust(m, "0"))
    if D == 0:
        raise ErrorMatematico("No se puede dividir entre cero.")
    n_str = str(N)
    if len(n_str) > _MAX_CIFRAS_DIVIDENDO or len(str(D)) > _MAX_CIFRAS_DIVISOR:
        raise ErrorDeEntrada(
            f"Para dividir en columnas usa un dividendo de hasta {_MAX_CIFRAS_DIVIDENDO} cifras "
            f"y un divisor de hasta {_MAX_CIFRAS_DIVISOR}.")
    LN = len(n_str)
    etapas, usados_total = _simular_division(n_str, D)
    M = 1                                                        # margen para el signo "−"
    ancho_izq = M + LN + (1 + usados_total if usados_total else 0)
    d_txt = str(D)

    def pos(i):                                                  # columna de la cifra i del flujo
        return i if i < LN else i + 1

    def q_texto(k):
        sel = etapas[:k + 1]
        enteras = [e["q"] for e in sel if e["fin"] < LN]
        decs = [e["q"] for e in sel if e["fin"] >= LN]
        return "".join(map(str, enteras)) + ("." + "".join(map(str, decs)) if decs else "")

    def dividendo_linea(zeros):
        return " " * M + n_str + ("." + "0" * zeros if zeros else "")

    def armar(izq, qs, marcas_izq=(), marca_q=False):
        """izq: líneas izquierdas (sin la del dividendo); qs: cociente hasta ahora."""
        lineas = list(izq)
        der = [d_txt, "─" * max(len(d_txt), len(qs)), qs]
        total = max(len(lineas), 3)
        lineas += [""] * (total - len(lineas))
        salida = []
        for i in range(total):
            derecha = der[i] if i < 3 else ""
            salida.append(lineas[i].ljust(ancho_izq) + " │ " + derecha)
        marcas = [[l, a, b] for l, a, b in marcas_izq]
        if marca_q and qs:
            marcas.append([2, ancho_izq + 3 + len(qs) - 1, ancho_izq + 3 + len(qs)])
        return {"lineas": salida, "marcas": marcas}

    pasos = []
    if m:
        intro = (f"Para dividir con decimales movemos la coma {m} lugar{'es' if m > 1 else ''} a la derecha en "
                 f"el dividendo y en el divisor (es multiplicar los dos por {10 ** m}): "
                 f"{_txt(ipa, fpa)} ÷ {_txt(ipb, fpb)} pasa a ser {N} ÷ {D}, y el resultado no cambia. "
                 f"Escribimos {N} dentro de la casita y {D} a la derecha.")
    else:
        intro = f"Escribimos el dividendo {N} dentro de la casita y el divisor {D} a la derecha."
    pasos.append(_crudo("preparacion", intro, _MOTIVO["div"], "", "", "",
                        armar([dividendo_linea(0)], "")))

    izq_acum = []                       # líneas de trabajo ya escritas (debajo del dividendo)
    zeros_hechos = 0
    for k, e in enumerate(etapas):
        cur, q, prod, rem, fin = e["cur"], e["q"], e["prod"], e["rem"], e["fin"]
        decimal = fin >= LN
        if decimal:
            zeros_hechos += 1
        # --- paso A: cuántas veces cabe ---
        if k == 0 and cur < D:
            tA = (f"{cur} es menor que {D}: no alcanza para dividir, así que escribimos 0 en el cociente.")
        elif k == 0:
            tA = (f"Tomamos las primeras cifras del dividendo hasta que alcancen para dividir entre {D}: {cur}. "
                  f"{D} cabe {q} veces en {cur}, porque {D} × {q} = {prod}"
                  f" y {D} × {q + 1} = {D * (q + 1)} ya se pasa de {cur}. Escribimos {q} en el cociente.")
        elif q == 0:
            tA = f"{cur} es menor que {D}: no cabe ni una vez. Escribimos 0 en el cociente."
        else:
            tA = (f"¿Cuántas veces cabe {D} en {cur}? Cabe {q} veces, porque {D} × {q} = {prod}"
                  f" y {D} × {q + 1} = {D * (q + 1)} ya se pasa de {cur}. Escribimos {q} en el cociente.")
        col_fin = pos(fin)
        trabajo = list(izq_acum)
        ini_prod = M + col_fin - len(str(prod))               # columna del signo "−"
        if q > 0:
            trabajo.append(" " * ini_prod + "−" + str(prod))
        izq = [dividendo_linea(zeros_hechos)] + trabajo
        marcas = [(len(izq) - 1, ini_prod, M + col_fin + 1)] if q > 0 else []
        pasos.append(_crudo("div_cabe", tA, _MOTIVO["div"], f"{cur} ÷ {D}", str(q), q_texto(k),
                            armar(izq, q_texto(k), marcas, marca_q=True)))
        izq_acum = trabajo
        # --- paso B: restar y bajar ---
        trae = e.get("trae")
        if q > 0:
            tB = f"Restamos: {cur} − {prod} = {rem}."
        else:
            tB = "No hay nada que restar."
        if trae is not None:
            nuevo = rem * 10 + trae
            es_dec = (fin + 1) >= LN
            if es_dec and not decimal:
                tB += (f" Ya no quedan cifras y el residuo {rem} no es 0: ponemos la coma en el cociente y "
                       f"bajamos un 0, queda {nuevo}.")
            elif es_dec:
                tB += f" Bajamos otro 0: queda {nuevo}."
            else:
                tB += f" Bajamos la cifra {trae}: queda {nuevo}."
            texto_rem = (str(rem) if rem > 0 else "") + str(trae)
            col_nueva = pos(fin + 1)
            linea_rem = " " * (M + col_nueva + 1 - len(texto_rem)) + texto_rem
            zeros_B = zeros_hechos + (1 if es_dec else 0)
            izq2 = [dividendo_linea(zeros_B)] + izq_acum + [linea_rem]
            marcas_B = [(len(izq2) - 1, M + col_nueva, M + col_nueva + 1),
                        (0, M + col_nueva, M + col_nueva + 1)]
            # la coma del cociente aparece al bajar el primer 0 decimal
            qs = q_texto(k) + ("." if es_dec and not decimal else "")
            pasos.append(_crudo("div_bajar", tB, _MOTIVO["div"], f"{cur} − {prod}" if q > 0 else "",
                                str(rem), qs, armar(izq2, qs, marcas_B)))
            izq_acum = izq_acum + [linea_rem]
        else:
            linea_rem = " " * (M + col_fin + 1 - len(str(rem))) + str(rem)
            if rem == 0:
                tB += " El residuo es 0: la división es exacta."
            else:
                tB += (f" Ya no quedan cifras que bajar. El residuo es {rem}; "
                       f"hemos llegado a {_MAX_DECIMALES_COCIENTE} decimales y la división sigue, así que paramos "
                       f"aquí (cortamos, no redondeamos).")
            izq2 = [dividendo_linea(zeros_hechos)] + izq_acum + [linea_rem]
            marcas_B = [(len(izq2) - 1, M + col_fin + 1 - len(str(rem)), M + col_fin + 1)]
            pasos.append(_crudo("div_bajar", tB, _MOTIVO["div"], f"{cur} − {prod}" if q > 0 else "",
                                str(rem), q_texto(k), armar(izq2, q_texto(k), marcas_B)))
            izq_acum = izq_acum + [linea_rem]

    q_final = q_texto(len(etapas) - 1)
    rem_final = etapas[-1]["rem"]
    exacto = rem_final == 0
    Qint, Rint = N // D, N % D
    if exacto:
        t_fin = f"El cociente es {q_final}."
    else:
        t_fin = (f"El cociente aproximado es {q_final} (con {_MAX_DECIMALES_COCIENTE} decimales, cortado). "
                 f"La división no termina.")
    ultimo_izq = [dividendo_linea(usados_total)] + izq_acum
    pasos.append(_crudo("resultado", t_fin, _MOTIVO["div"], "", q_final, q_final,
                        armar(ultimo_izq, q_final)))
    nota = ""
    if Rint:
        nota = f"Con números enteros: cociente {Qint} y residuo {Rint}."
        if not exacto:
            nota += (f" La división no termina: se cortó en {_MAX_DECIMALES_COCIENTE} decimales, "
                     "no se redondeó.")
    return pasos, q_final, exacto, nota


# ---------------------------------------------------------------------------
# Entrada pública
# ---------------------------------------------------------------------------

_SIMBOLO = {"+": "+", "-": "−", "×": "×", "÷": "÷"}
_LATEX = {"+": "+", "-": "-", "×": "\\times", "÷": "\\div"}
_REGLAS = {"+": "suma", "-": "resta", "×": "mult", "÷": "div"}


def resolver_columnas(texto: str) -> Solucion:
    """Resuelve una operación en columnas, como se hace a mano."""
    op, partes = _leer(texto)
    nums = [_txt(ip, fp) for ip, fp in partes]
    exacto, nota = True, ""
    if op == "+":
        crudos, res = _resolver_suma(partes)
    elif op == "-":
        crudos, res = _resolver_resta(partes)
    elif op == "×":
        crudos, res = _resolver_mult(partes)
    else:
        crudos, res, exacto, nota = _resolver_division(partes)

    pasos = [
        Paso(numero=i + 1, regla=c["regla"], explicacion=c["explicacion"], motivo=c["motivo"],
             operacion=c["operacion"], resultado_parcial=c["parcial"], expresion=c["expresion"],
             latex="", pizarra=c["pizarra"])
        for i, c in enumerate(crudos)
    ]
    inicial = f" {_SIMBOLO[op]} ".join(nums)
    inicial_latex = f" {_LATEX[op]} ".join(nums)
    res_txt = res.replace("-", "−")
    return Solucion(
        tipo=f"columnas_{_REGLAS[op]}",
        entrada=texto,
        expresion_inicial=inicial,
        latex_inicial=inicial_latex,
        pasos=pasos,
        resultado=res_txt,
        resultado_latex=res,
        decimal_exacto=exacto,
        nota=nota,
    )
