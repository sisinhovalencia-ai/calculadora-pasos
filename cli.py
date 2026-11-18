"""Prueba el motor desde la terminal.

    python cli.py "2 + 3 × (4 − 1)^2"     resuelve una expresión
    python cli.py                          modo interactivo (línea vacía o 'salir' para terminar)
    python cli.py "1/2 + 1/3" --json       salida en JSON (lo que usará la web)
    python cli.py "8 ÷ 2(2+2)" --porque    agrega el "porqué" de cada paso
    python cli.py "7845 ÷ 12" --columnas   resuelve en columnas, como a mano
"""

import json
import sys

from motor import ErrorMotor, resolver, resolver_columnas


def mostrar(entrada: str, con_porque: bool, como_json: bool, columnas: bool = False) -> None:
    try:
        sol = resolver_columnas(entrada) if columnas else resolver(entrada)
    except ErrorMotor as e:
        print(f"  ✗ {e}\n")
        return

    if como_json:
        print(json.dumps(sol.a_dict(), ensure_ascii=False, indent=2))
        return

    print(f"\n  Ejercicio:  {sol.expresion_inicial}\n")
    for p in sol.pasos:
        print(f"  Paso {p.numero}: {p.explicacion}")
        if con_porque:
            print(f"          ¿Por qué ahora? {p.motivo}")
        if p.pizarra:
            print("\n".join("          " + linea for linea in p.pizarra["lineas"]) + "\n")
        else:
            print(f"          {p.expresion}\n")
    extra = ""
    if sol.resultado_decimal:
        extra = f"   ({'=' if sol.decimal_exacto else '≈'} {sol.resultado_decimal})"
    print(f"  Resultado:  {sol.resultado}{extra}")
    if sol.nota:
        print(f"              {sol.nota}")
    print()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")   # para × ÷ − en consolas de Windows

    banderas = {a for a in sys.argv[1:] if a.startswith("--")}
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    con_porque, como_json = "--porque" in banderas, "--json" in banderas
    columnas = "--columnas" in banderas

    if args:
        mostrar(" ".join(args), con_porque, como_json, columnas)
        return

    print("Calculadora paso a paso (escribe 'salir' o deja la línea vacía para terminar)")
    while True:
        try:
            entrada = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not entrada or entrada.lower() == "salir":
            return
        mostrar(entrada, con_porque, como_json, columnas)


if __name__ == "__main__":
    main()
