"""FORMATO COMÚN DE PASOS.

Este es el contrato más importante del proyecto: TODOS los solucionadores
(aritmética hoy; ecuaciones, factorización, integrales mañana) devuelven una
`Solucion` hecha de `Paso`s. La pantalla solo sabe dibujar este formato, así
que agregar un tipo de ejercicio nuevo nunca obliga a tocar la interfaz.

Si algún día necesitas un campo nuevo, agrégalo aquí con valor por defecto
para no romper a los solucionadores existentes.
"""

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class Paso:
    numero: int               # 1, 2, 3...
    regla: str                # identificador estable: 'suma', 'potencia', ...
    explicacion: str          # QUÉ se hizo, en español, para el estudiante
    motivo: str               # POR QUÉ se hizo ahora (el "porqué" didáctico)
    operacion: str            # el trozo que se resolvió: '3 + 4'
    resultado_parcial: str    # lo que quedó en su lugar: '7'
    expresion: str            # expresión completa DESPUÉS del paso (texto plano)
    latex: str                # lo mismo en LaTeX, para dibujar fórmulas
    en_parentesis: bool = False
    # Solo para operaciones en columnas: la "pizarra" tal como queda en este paso.
    #   {"lineas": ["  4567", "+  289", ...], "marcas": [[línea, col_inicio, col_fin], ...]}
    # Las marcas son lo que se resalta en ese paso (columna actual, llevada, etc.).
    pizarra: dict | None = None
    # Solo para ecuaciones y desigualdades: la línea con la operación escrita en los DOS lados,
    # antes de simplificar (ej. "2x + 2 − 3x = 3x − 9 − 3x"). La pantalla la muestra encima del resultado.
    intermedio: str = ""
    latex_intermedio: str = ""


@dataclass(frozen=True)
class Solucion:
    tipo: str                 # 'aritmetica', 'ecuacion_lineal', ...
    entrada: str              # lo que escribió el estudiante, tal cual
    expresion_inicial: str    # la misma expresión ya interpretada y ordenada
    latex_inicial: str
    pasos: list[Paso] = field(default_factory=list)
    resultado: str = ""       # '14', '7/2', '3.5'
    resultado_latex: str = ""
    resultado_decimal: str | None = None   # '3.5' si el resultado es fracción
    decimal_exacto: bool = True            # False => resultado_decimal es aproximado
    nota: str = ""                         # aviso extra bajo el resultado (ej. cociente y residuo)

    def a_dict(self) -> dict:
        """Listo para convertir a JSON (lo usará la API/web más adelante)."""
        return asdict(self)
