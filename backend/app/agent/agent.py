"""Agente Monitor-IoT: atiende los mensajes del chat y avanza por el workflow (RF-16).

Cada acción produce eventos que la interfaz recibe en tiempo real:
  {"type": "step", "id": 2, "status": "running" | "completed" | "error", "detail": {...}}
  {"type": "message", "role": "assistant", "content": "..."}
  {"type": "version", "version": {...}}
  {"type": "error", "message": "..."}

Avance 1: conversación con GLM 4.6 (si hay clave) y la tubería completa
especificación JSON → modelo → XMI → validación → visor, demostrada con el caso
ilustrativo del artículo. En el avance 2 el agente producirá esa especificación
a partir del caso del usuario.
"""
from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from typing import AsyncIterator

from ..builder import SpecError, build_model
from ..metamodel import get_metamodel
from ..sessions import Session
from ..summary import describe_summary, summarize_model
from .llm import LLMClient, LLMError

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "knowledge" / "examples"
STEP_PAUSE = 0.35  # pausa breve para que el usuario pueda seguir cada paso

SYSTEM_PROMPT = """Eres el Asistente Monitor-IoT, un experto en el lenguaje Monitor-IoT \
(Erazo-Garzón et al., IEEE Access 2022) para modelar arquitecturas de monitoreo IoT en las capas edge, fog y cloud.
Tu tarea en esta etapa es ENTENDER el caso del usuario siguiendo la actividad 1 del proceso de diseño:
- Identifica el sistema y sus subsistemas, las entidades físicas (lugares, objetos, personas), los nodos de cómputo
  de cada capa (sensores, actuadores, gateways, nodos fog, nodos cloud) con sus recursos (bases de datos, middleware,
  servicios, brokers y tópicos, APIs, aplicaciones), las redes y protocolos, las propiedades a monitorear y los flujos
  de datos (recolección o agregación, síncronos o asíncronos, con su frecuencia).
- Si falta información importante (frecuencia de envío, dónde se guardan los datos, cómo se comunican), haz como
  máximo 3 preguntas concretas.
- Si el usuario no conoce un dato, propone un valor razonable y márcalo claramente como **Supuesto**.
- Nunca inventes credenciales reales: usa valores de ejemplo.
Responde siempre en español, de forma breve y clara. Los nombres de los elementos del modelo van en inglés
(por ejemplo, TemperatureSensor, HouseEnvironment)."""

DEMO_REPLY = """Estoy en **modo demostración**: todavía no hay conexión con GLM 4.6 (falta configurar `GLM_API_KEY`).

Mientras tanto puede:
- Escribir **ejemplo** para cargar el caso del artículo de Monitor-IoT (adulto mayor que vive solo) y ver cómo se genera, valida y dibuja el modelo.
- Usar el botón **+** para abrir un XMI existente (.MonitorIoT o .xmi) y revisar su validación en el visor.

Su mensaje quedó guardado en la conversación."""

EXAMPLE_WORDS = re.compile(r"\b(ejemplo|demo|demostraci[oó]n|adulto mayor)\b", re.IGNORECASE)


def step(sid: int, status: str, detail: dict | None = None, error: str | None = None) -> dict:
    return {"type": "step", "id": sid, "status": status, "detail": detail, "error": error}


class MonitorIoTAgent:
    def __init__(self, llm: LLMClient | None):
        self.llm = llm

    @property
    def mode(self) -> str:
        return "glm" if self.llm else "demo"

    async def handle_message(self, session: Session, text: str) -> AsyncIterator[dict]:
        session.messages.append({"role": "user", "content": text})
        if self.llm is None and EXAMPLE_WORDS.search(text):
            async for ev in self.run_example(session):
                yield ev
            return

        session.reset_steps()
        yield _apply(session, step(1, "running"))
        if self.llm is None:
            await asyncio.sleep(STEP_PAUSE)
            yield _apply(session, step(1, "completed", {"text": "Modo demostración: sin conexión con GLM 4.6."}))
            yield _say(session, DEMO_REPLY)
            return

        history = [{"role": m["role"], "content": m["content"]} for m in session.messages if m["role"] in ("user", "assistant")]
        try:
            reply = await self.llm.chat([{"role": "system", "content": SYSTEM_PROMPT}, *history])
        except LLMError as e:
            # RNF-13: se informa, se conserva la conversación y se permite reintentar
            yield _apply(session, step(1, "error", error=str(e)))
            yield {"type": "error", "message": str(e), "retryable": True}
            return
        yield _apply(session, step(1, "completed", {"text": f"Respuesta de {self.llm.name}."}))
        yield _say(session, reply)

    async def run_example(self, session: Session, name: str = "emergency_case") -> AsyncIterator[dict]:
        """Recorre el workflow completo con un caso de ejemplo de la base de conocimiento."""
        spec = json.loads((EXAMPLES_DIR / f"{name}.json").read_text(encoding="utf-8"))
        description = (EXAMPLES_DIR / f"{name}.txt").read_text(encoding="utf-8").strip()
        session.reset_steps()
        session.messages.append({"role": "user", "content": description, "kind": "example"})
        yield {"type": "message", "role": "user", "content": description, "kind": "example"}

        yield _apply(session, step(1, "running"))
        await asyncio.sleep(STEP_PAUSE)
        yield _apply(session, step(1, "completed", {"text": "Caso ilustrativo del artículo de Monitor-IoT (Apéndice C de la ERS)."}))

        yield _apply(session, step(2, "running"))
        await asyncio.sleep(STEP_PAUSE)
        try:
            model = build_model(spec, get_metamodel())
        except SpecError as e:
            yield _apply(session, step(2, "error", {"issues": [i.to_dict() for i in e.issues]}, "La especificación del modelo tiene errores."))
            yield {"type": "error", "message": "No se pudo construir el modelo del ejemplo.", "retryable": False}
            return
        s = summarize_model(model)
        yield _apply(session, step(2, "completed", {
            "headline": f"{len(s['physicalEntities'])} entidades físicas · {len(s['flows'])} flujos",
            "items": {
                "Sistemas": s["systems"],
                "Entidades físicas": s["physicalEntities"],
                "Flujos de datos": [f["description"] for f in s["flows"]],
            },
        }))

        yield _apply(session, step(3, "running"))
        await asyncio.sleep(STEP_PAUSE)
        r = s["resources"]
        yield _apply(session, step(3, "completed", {
            "headline": f"{sum(len(v) for v in s['layers'].values())} nodos · {s['properties']} propiedades",
            "items": {
                "Edge": s["layers"]["edge"],
                "Fog": s["layers"]["fog"],
                "Cloud": s["layers"]["cloud"],
                "Bases de datos": r["databases"],
                "Servicios": r["services"],
                "Tópicos": r["topics"],
                "Redes": s["networks"],
                "Categorías": s["categories"],
            },
        }))

        yield _apply(session, step(4, "running"))
        await asyncio.sleep(STEP_PAUSE)
        yield _apply(session, step(4, "completed", {
            "headline": f"{len(s['flows'])} flujos · {s['links']} enlaces",
            "items": {f["description"]: [
                "agregación" if f["type"] == "DataAggregationFlow" else "recolección",
                "síncrono" if f["communication"] == "Synchronous" else "asíncrono",
                f"cada {f['every']}", f"{f['links']} enlaces", f"{f['rules']} reglas de mapeo",
            ] for f in s["flows"]},
        }))

        yield _apply(session, step(5, "running"))
        await asyncio.sleep(STEP_PAUSE)
        version = session.add_version(model, "example", "Caso de ejemplo")
        val = version.validation
        if val["valid"]:
            yield _apply(session, step(5, "completed", {"headline": f"Modelo válido · {val['warnings']} advertencias"}))
        else:
            yield _apply(session, step(5, "error", {"headline": f"{val['errors']} errores"}, "El modelo no pasó la validación."))

        yield _apply(session, step(6, "running"))
        await asyncio.sleep(STEP_PAUSE)
        yield _apply(session, step(6, "completed", {"headline": f"Versión {version.number} lista para descargar"}))
        yield {"type": "version", "version": {"number": version.number}}
        yield _say(session, "Generé el modelo del caso de ejemplo y lo validé contra el metamodelo Monitor-IoT.\n\n"
                   + describe_summary(version.summary))


def _apply(session: Session, ev: dict) -> dict:
    for s in session.steps:
        if s["id"] == ev["id"]:
            s.update(status=ev["status"], detail=ev["detail"], error=ev["error"])
    return ev


def _say(session: Session, content: str) -> dict:
    session.messages.append({"role": "assistant", "content": content})
    return {"type": "message", "role": "assistant", "content": content}
