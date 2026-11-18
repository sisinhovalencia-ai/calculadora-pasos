"""Errores del motor.

Todos los mensajes están escritos en español y pensados para mostrarse tal
cual al estudiante (nada de trazas técnicas en pantalla).
"""


class ErrorMotor(Exception):
    """Base de todos los errores del motor."""


class ErrorDeEntrada(ErrorMotor):
    """El texto escrito no se puede interpretar (falta un paréntesis, etc.)."""


class ErrorMatematico(ErrorMotor):
    """La expresión se entiende, pero la operación no es válida
    (división entre cero, 0^0, etc.) o todavía no está soportada."""
