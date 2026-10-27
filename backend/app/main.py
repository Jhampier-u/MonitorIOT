"""API web del Asistente Monitor-IoT."""
from __future__ import annotations

import json
import re
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from .agent.agent import MonitorIoTAgent  # noqa: E402
from .agent.llm import get_llm_client  # noqa: E402
from .metamodel import get_metamodel  # noqa: E402
from .sessions import Session, store, version_meta  # noqa: E402
from .xmi import read_xmi  # noqa: E402

MAX_UPLOAD = 20 * 1024 * 1024  # RNF-04
FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

app = FastAPI(title="Asistente Monitor-IoT", version="0.1.0")
agent = MonitorIoTAgent(get_llm_client())


class ChatIn(BaseModel):
    message: str


def _session(sid: str) -> Session:
    s = store.get(sid)
    if s is None:
        raise HTTPException(404, "La sesión no existe o expiró. Recargue la página para empezar un caso nuevo.")
    return s


def _sse(events) -> StreamingResponse:
    async def gen():
        async for ev in events:
            yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
        yield 'data: {"type": "done"}\n\n'

    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@app.get("/api/health")
def health():
    mm = get_metamodel()
    return {
        "status": "ok",
        "agentMode": agent.mode,
        "llm": agent.llm.name if agent.llm else None,
        "metamodel": {"nsURI": mm.ns_uri, "classes": len(mm.classes), "enums": len(mm.enums)},
    }


@app.post("/api/sessions")
def create_session():
    return store.create().to_dict()


@app.get("/api/sessions/{sid}")
def get_session(sid: str):
    return _session(sid).to_dict()


@app.post("/api/sessions/{sid}/chat")
async def chat(sid: str, body: ChatIn):
    s = _session(sid)
    text = body.message.strip()
    if not text:
        raise HTTPException(400, "El mensaje está vacío.")
    return _sse(agent.handle_message(s, text))


@app.post("/api/sessions/{sid}/example")
async def load_example(sid: str):
    return _sse(agent.run_example(_session(sid)))


@app.post("/api/sessions/{sid}/xmi")
async def upload_xmi(sid: str, file: UploadFile = File(...)):
    """RF-23: abrir un XMI de Monitor-IoT existente."""
    s = _session(sid)
    data = await file.read(MAX_UPLOAD + 1)
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, "El archivo supera los 20 MB permitidos.")
    try:
        model, read_issues = read_xmi(data, get_metamodel())
    except ValueError as e:
        raise HTTPException(400, f"No se pudo abrir '{file.filename}'. {e}")
    v = s.add_version(model, "upload", f"Archivo {file.filename}", read_issues)
    s.messages.append({"role": "system", "content": f"Se abrió el archivo {file.filename} como versión {v.number}."})
    return {"session": s.to_dict(), "version": version_meta(v)}


@app.get("/api/sessions/{sid}/versions/{n}")
def get_version(sid: str, n: int):
    v = _version(_session(sid), n)
    return {**version_meta(v), "validation": v.validation, "summary": v.summary, "model": v.model_json, "xmi": v.xmi}


@app.get("/api/sessions/{sid}/versions/{n}/download")
def download(sid: str, n: int, ext: str = "MonitorIoT"):
    """RF-24/RF-25: descarga con la extensión .MonitorIoT o .xmi; indica si es válido."""
    s = _session(sid)
    v = _version(s, n)
    if ext not in ("MonitorIoT", "xmi"):
        raise HTTPException(400, "La extensión debe ser MonitorIoT o xmi.")
    base = re.sub(r"[^A-Za-z0-9_-]+", "_", s.case_name).strip("_")[:60] or "model"
    return Response(
        v.xmi,
        media_type="application/xml",
        headers={
            "Content-Disposition": f'attachment; filename="{base}_v{v.number}.{ext}"',
            "X-Model-Valid": "true" if v.validation["valid"] else "false",
        },
    )


def _version(s: Session, n: int):
    if not 1 <= n <= len(s.versions):
        raise HTTPException(404, f"La versión {n} no existe.")
    return s.versions[n - 1]


# Interfaz web compilada (producción). En desarrollo se usa el servidor de Vite.
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        f = FRONTEND_DIST / path
        return FileResponse(f if path and f.is_file() else FRONTEND_DIST / "index.html")
