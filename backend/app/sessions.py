"""Sesiones de trabajo en memoria: conversación, versiones del modelo y estado del workflow.

Cada sesión tiene un identificador aleatorio y no es visible para otras (RNF-14).
La persistencia en base de datos queda para una versión posterior.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .issues import Issue
from .metamodel import get_metamodel
from .model import Model
from .summary import summarize_model
from .validator import summarize, validate
from .xmi import read_xmi, write_xmi

# Pasos del workflow del agente (ERS, Figura 2). Los pasos 2, 3 y 4 son las tres
# actividades del proceso de diseño de Monitor-IoT.
WORKFLOW_STEPS = [
    {"id": 1, "title": "Entender el caso", "description": "Lee el chat y los documentos, y pregunta si falta información.", "activity": None},
    {"id": 2, "title": "Identificar", "description": "Sistema, subsistemas, entidades, propiedades y flujos de datos.", "activity": 1},
    {"id": 3, "title": "Modelar entidades y propiedades", "description": "Nodos edge, fog y cloud, recursos, redes, categorías y propiedades.", "activity": 2},
    {"id": 4, "title": "Modelar flujos de datos", "description": "Reglas de mapeo y cadena ordenada de enlaces entre elementos.", "activity": 3},
    {"id": 5, "title": "Validar y corregir", "description": "Revisa el modelo contra el metamodelo y corrige los errores.", "activity": None},
    {"id": 6, "title": "Entregar el resultado", "description": "Genera el XMI, lo dibuja en el visor y habilita la descarga.", "activity": None},
]


@dataclass
class Version:
    number: int
    xmi: str
    source: str  # "agent" | "example" | "upload"
    label: str
    created_at: str
    validation: dict
    summary: dict
    model_json: dict


@dataclass
class Session:
    id: str
    case_name: str = "Caso nuevo"
    messages: list[dict] = field(default_factory=list)
    versions: list[Version] = field(default_factory=list)
    steps: list[dict] = field(default_factory=list)

    def reset_steps(self) -> None:
        self.steps = [{**s, "status": "pending", "detail": None, "error": None} for s in WORKFLOW_STEPS]

    def add_version(self, model: Model, source: str, label: str, read_issues: list[Issue] | None = None) -> Version:
        """Registra una versión nueva. Valida exactamente el XMI que se entrega:
        se escribe, se vuelve a leer y se valida lo leído (RNF-12)."""
        mm = get_metamodel()
        xmi = write_xmi(model)
        delivered, issues = read_xmi(xmi, mm)
        all_issues = (read_issues or []) + issues + validate(delivered)
        v = Version(
            number=len(self.versions) + 1,
            xmi=xmi,
            source=source,
            label=label,
            created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            validation=summarize(all_issues),
            summary=summarize_model(delivered),
            model_json=delivered.to_json(),
        )
        self.versions.append(v)
        if delivered.root.attrs.get("name"):
            self.case_name = str(delivered.root.attrs["name"])
        return v

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "caseName": self.case_name,
            "messages": self.messages,
            "steps": self.steps,
            "versions": [version_meta(v) for v in self.versions],
        }


def version_meta(v: Version) -> dict:
    return {
        "number": v.number,
        "source": v.source,
        "label": v.label,
        "createdAt": v.created_at,
        "valid": v.validation["valid"],
        "errors": v.validation["errors"],
        "warnings": v.validation["warnings"],
    }


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def create(self) -> Session:
        s = Session(id=uuid.uuid4().hex)
        s.reset_steps()
        self._sessions[s.id] = s
        return s

    def get(self, sid: str) -> Session | None:
        return self._sessions.get(sid)


store = SessionStore()
