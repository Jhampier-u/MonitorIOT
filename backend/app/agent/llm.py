"""Capa intermedia hacia el modelo de lenguaje (respuesta a los riesgos R001 y R011).

El agente solo conoce la interfaz `LLMClient`. GLM 4.6 se usa a través de su API
compatible con OpenAI (Z.ai). Cambiar de proveedor o de versión del modelo es cuestión
de configurar otras variables de entorno, sin tocar el agente.
"""
from __future__ import annotations

import os
from typing import Protocol

import httpx


class LLMError(Exception):
    """Fallo del modelo de lenguaje; el mensaje es apto para mostrarse al usuario (RNF-13)."""


class LLMClient(Protocol):
    name: str

    async def chat(self, messages: list[dict], temperature: float = 0.3) -> str: ...


class OpenAICompatibleClient:
    def __init__(self, api_key: str, base_url: str, model: str, timeout: float = 120.0):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.name = model
        self.timeout = timeout

    async def chat(self, messages: list[dict], temperature: float = 0.3) -> str:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                r = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"model": self.model, "messages": messages, "temperature": temperature},
                )
        except httpx.TimeoutException as e:
            raise LLMError("El modelo de lenguaje tardó demasiado en responder. Puede reintentar.") from e
        except httpx.HTTPError as e:
            raise LLMError("No se pudo conectar con el modelo de lenguaje. Revise la conexión y reintente.") from e
        if r.status_code == 401:
            raise LLMError("La clave de acceso a GLM 4.6 no es válida. Revise GLM_API_KEY en el archivo .env.")
        if r.status_code == 429:
            raise LLMError("Se alcanzó el límite de uso del modelo de lenguaje. Espere un momento y reintente.")
        if r.status_code >= 400:
            raise LLMError(f"El modelo de lenguaje devolvió un error ({r.status_code}). Puede reintentar.")
        try:
            return r.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, ValueError) as e:
            raise LLMError("La respuesta del modelo de lenguaje no tiene el formato esperado.") from e


def get_llm_client() -> LLMClient | None:
    """Devuelve el cliente configurado, o None si no hay clave (modo demostración)."""
    key = os.getenv("GLM_API_KEY", "").strip()
    if not key:
        return None
    return OpenAICompatibleClient(
        api_key=key,
        base_url=os.getenv("GLM_BASE_URL", "https://api.z.ai/api/paas/v4"),
        model=os.getenv("GLM_MODEL", "glm-4.6"),
    )
