from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass
class Issue:
    """Un problema encontrado en un modelo, escrito en lenguaje sencillo (RI-04)."""

    severity: str  # "error" | "warning"
    code: str
    message: str  # qué pasó
    element: str | None = None  # referencia por posición o etiqueta del elemento
    hint: str | None = None  # qué puede hacer el usuario

    def to_dict(self) -> dict:
        return asdict(self)


def error(code: str, message: str, element: str | None = None, hint: str | None = None) -> Issue:
    return Issue("error", code, message, element, hint)


def warning(code: str, message: str, element: str | None = None, hint: str | None = None) -> Issue:
    return Issue("warning", code, message, element, hint)
