"""Resúmenes legibles de un modelo, usados en el detalle del workflow y en el chat (RF-15, RF-17)."""
from __future__ import annotations

from .model import Model
from .validator import LINK_ENDS

LAYERS = {
    "cloud": ("CloudNode",),
    "fog": ("FogNode",),
    "edge": ("IoTGateway", "Sensor", "Actuator", "Tag"),
}


def summarize_model(model: Model) -> dict:
    mm = model.mm
    objs = list(model.walk())

    def names(*classes: str) -> list[str]:
        return [o.name for o in objs if o.cls in classes]

    systems = [o for o in objs if o.cls == "IoTSystem"]
    flows = []
    for f in (o for o in objs if o.cls == "DataFlow"):
        flows.append(
            {
                "description": f.attrs.get("description") or "",
                "type": f.attrs.get("dataFlowType", "DataCollectionFlow"),
                "communication": f.attrs.get("communicationType", "Asynchronous"),
                "every": f"{f.attrs.get('flowExecutionTimeInterval', 0)} {f.attrs.get('unitOfTime', 'Millisecond')}",
                "links": len(f.get_refs("isSupported")),
                "rules": len(f.get_refs("containsDataMappingRule")),
            }
        )
    physical = [o for o in objs if mm.is_subtype(o.cls, "PhysicalEntity")]
    return {
        "name": model.root.attrs.get("name") or "",
        "systems": [s.name for s in systems],
        "physicalEntities": [o.name for o in physical],
        "layers": {layer: names(*classes) for layer, classes in LAYERS.items()},
        "resources": {
            "databases": names("DataBase"),
            "middlewares": names("Middleware"),
            "brokers": names("Broker"),
            "apis": names("API"),
            "applications": names("Application"),
            "services": names("Service"),
            "topics": names("Topic"),
        },
        "networks": names("Network"),
        "categories": names("EntityCategory"),
        "properties": len([o for o in objs if o.cls == "Property"]),
        "links": len([o for o in objs if o.cls in LINK_ENDS]),
        "flows": flows,
        "elements": len(objs),
    }


def describe_summary(s: dict) -> str:
    """Texto breve en español para el chat."""
    lines = [f"**{s['name']}**" if s["name"] else "**Modelo generado**"]
    if s["systems"]:
        lines.append(f"- Sistemas: {', '.join(s['systems'])}")
    lines.append(f"- Entidades físicas: {', '.join(s['physicalEntities']) or '—'}")
    for layer, label in (("edge", "Capa edge"), ("fog", "Capa fog"), ("cloud", "Capa cloud")):
        lines.append(f"- {label}: {', '.join(s['layers'][layer]) or '—'}")
    lines.append(f"- Redes: {', '.join(s['networks']) or '—'}")
    if s["flows"]:
        lines.append(f"- Flujos de datos ({len(s['flows'])}):")
        for f in s["flows"]:
            kind = "agregación" if f["type"] == "DataAggregationFlow" else "recolección"
            comm = "síncrono" if f["communication"] == "Synchronous" else "asíncrono"
            lines.append(f"  - {f['description'] or 'Flujo'}: {kind}, {comm}, cada {f['every']} ({f['links']} enlaces)")
    return "\n".join(lines)
