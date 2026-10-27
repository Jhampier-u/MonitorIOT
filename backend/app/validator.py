"""Validador independiente del modelo de lenguaje (RNF-09).

Dos niveles:
1. Conformidad con el metamodelo (RF-11): clases, datos, valores de las listas, tipos,
   referencias, relaciones de doble sentido completas y datos obligatorios.
2. Coherencia del monitoreo (RF-12): cada enlace conecta dos elementos, cada flujo
   tiene una cadena de enlaces ordenada y sin cortes, y cada propiedad llega a una columna.
"""
from __future__ import annotations

import re

from .issues import Issue, error, warning
from .metamodel import Metamodel
from .model import MObject, Model

# Extremos de cada tipo de enlace, en el sentido en que viaja el dato.
LINK_ENDS: dict[str, tuple[str, str]] = {
    "LinkAPIToIoTDevice": ("linksIoTDevice", "linksAPI"),
    "LinkAppToAPI": ("linksAPI", "linksApp"),
    "LinkAppToService": ("linksApp", "linksService"),
    "LinkAppToTopic": ("linksApplication", "linksTopic"),
    "LinkServiceToTopic": ("linksService", "linksTopic"),
    "LinkServiceToDataTable": ("linkService", "linksDataTable"),
    "LinkServiceToService": ("linksSourceService", "linksDestinationService"),
    "LinkServiceToAPI": ("linksAPI", "linksService"),
}

SUPPORTED_FLOWS = {"DataCollectionFlow", "DataAggregationFlow"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}(:\d{2}(\.\d+)?)?([+-]\d{2}:?\d{2}|Z)?)?$")


def validate(model: Model) -> list[Issue]:
    issues = _check_metamodel(model)
    issues += _check_coherence(model)
    return issues


def summarize(issues: list[Issue]) -> dict:
    errors = [i for i in issues if i.severity == "error"]
    return {
        "valid": not errors,
        "errors": len(errors),
        "warnings": len(issues) - len(errors),
        "issues": [i.to_dict() for i in issues],
    }


# ------------------------------------------------------------ metamodelo
def _check_metamodel(model: Model) -> list[Issue]:
    mm: Metamodel = model.mm
    issues: list[Issue] = []
    objects = set(model.walk())
    for obj in objects:
        where = obj.label()
        ec = mm.classes.get(obj.cls)
        if ec is None:
            issues.append(error("UNKNOWN_CLASS", f"La clase '{obj.cls}' no existe en el metamodelo.", where))
            continue
        if ec.abstract:
            issues.append(error("ABSTRACT_CLASS", f"{obj.cls} es una clase abstracta y no puede usarse directamente.", where))
        if obj.container is not None:
            f = mm.feature(obj.container.cls, obj.container_feature or "")
            if f is None or not mm.is_subtype(obj.cls, f.type):
                issues.append(error("WRONG_CONTAINMENT",
                                    f"Un {obj.cls} no puede estar dentro de '{obj.container_feature}' de {obj.container.cls}.", where))

        for name, value in obj.attrs.items():
            f = mm.feature(obj.cls, name)
            if f is None or f.kind != "attribute":
                issues.append(error("UNKNOWN_FEATURE", f"{obj.cls} no tiene el dato '{name}'.", where))
                continue
            msg = _check_value(mm, f.type, value)
            if msg:
                issues.append(error("BAD_VALUE", f"El dato '{name}' tiene un valor inválido: {msg}", where))

        for name, targets in obj.refs.items():
            f = mm.feature(obj.cls, name)
            if f is None or f.kind != "reference":
                issues.append(error("UNKNOWN_FEATURE", f"{obj.cls} no tiene la relación '{name}'.", where))
                continue
            if not f.many and len(targets) > 1:
                issues.append(error("TOO_MANY", f"La relación '{name}' admite un solo elemento y tiene {len(targets)}.", where))
            for t in targets:
                if t not in objects:
                    issues.append(error("UNRESOLVED_REF", f"La relación '{name}' apunta a un elemento que no está en el modelo.", where))
                elif not mm.is_subtype(t.cls, f.type):
                    issues.append(error("WRONG_REF_TYPE",
                                        f"La relación '{name}' debe apuntar a un {f.type}, pero apunta a {t.label()}.", where))
                elif f.opposite and obj not in t.get_refs(f.opposite):
                    issues.append(error("MISSING_OPPOSITE",
                                        f"Relación incompleta: '{name}' apunta a '{t.label()}', pero este no tiene "
                                        f"'{f.opposite}' de vuelta.", where,
                                        "Las relaciones de doble sentido deben estar escritas en ambos elementos."))

        for f in mm.all_features(obj.cls):
            if f.lower > 0:
                n = len(obj.get_refs(f.name)) if f.kind == "reference" else int(obj.attrs.get(f.name) is not None)
                if n < f.lower:
                    issues.append(error("MISSING_REQUIRED", _required_msg(obj, f.name), where, _required_hint(obj.cls, f.name)))
    return issues


def _check_value(mm: Metamodel, type_name: str, value) -> str | None:
    if value is None:
        return None
    if type_name in mm.enums:
        lits = mm.enums[type_name].literals
        return None if value in lits else f"'{value}' no está entre los valores permitidos ({', '.join(lits)})."
    if type_name in ("EInt", "ELong"):
        return None if isinstance(value, int) and not isinstance(value, bool) else f"'{value}' no es un número entero."
    if type_name in ("EDouble", "EFloat"):
        return None if isinstance(value, (int, float)) and not isinstance(value, bool) else f"'{value}' no es un número."
    if type_name == "EBoolean":
        return None if isinstance(value, bool) else f"'{value}' debe ser true o false."
    if type_name == "EDate":
        return None if isinstance(value, str) and DATE_RE.match(value) else f"'{value}' no es una fecha válida."
    if type_name == "EString":
        return None if isinstance(value, str) else f"'{value}' debe ser texto."
    return None


def _required_msg(obj: MObject, feat: str) -> str:
    msgs = {
        ("Property", "isBasedOn"): f"La propiedad '{obj.name}' no está basada en ninguna plantilla de propiedad.",
        ("DataTable", "composedOfDataColumn"): f"La tabla '{obj.name}' no tiene columnas.",
    }
    return msgs.get((obj.cls, feat), f"Falta el dato obligatorio '{feat}'.")


def _required_hint(cls: str, feat: str) -> str | None:
    if (cls, feat) == ("Property", "isBasedOn"):
        return "Cree una PropertyTemplate en una EntityCategory y relacione la propiedad con ella."
    return None


# ------------------------------------------------------------- coherencia
def _check_coherence(model: Model) -> list[Issue]:
    issues: list[Issue] = []
    objs = list(model.walk())
    links = [o for o in objs if o.cls in LINK_ENDS]
    flows = [o for o in objs if o.cls == "DataFlow"]

    for link in links:
        src_f, dst_f = LINK_ENDS[link.cls]
        missing = [f for f in (src_f, dst_f) if not link.get_refs(f)]
        if missing:
            issues.append(error("INCOMPLETE_LINK",
                                f"El enlace {link.cls} no conecta dos elementos (falta {', '.join(missing)}).",
                                _link_label(link), "Cada enlace debe tener sus dos extremos."))
        if not link.get_refs("supports"):
            issues.append(warning("ORPHAN_LINK", f"El enlace {_link_label(link)} no pertenece a ningún flujo de datos.",
                                  _link_label(link)))

    for flow in flows:
        issues += _check_flow(flow)

    for prop in (o for o in objs if o.cls == "Property"):
        if not prop.get_refs("hasRulePropertyToDataColumn"):
            issues.append(warning("UNMAPPED_PROPERTY",
                                  f"La propiedad '{prop.name}' de '{prop.container.name if prop.container else '?'}' "
                                  f"no se guarda en ninguna columna.", prop.label(),
                                  "Si se monitorea, agregue una regla PropertyToDataColumn en un flujo de recolección."))
    return issues


def _check_flow(flow: MObject) -> list[Issue]:
    issues: list[Issue] = []
    name = flow.attrs.get("description") or f"DataFlow {flow.attrs.get('id', '')}"
    where = f"{name} : DataFlow"
    ftype = flow.attrs.get("dataFlowType", "DataCollectionFlow")
    if ftype not in SUPPORTED_FLOWS:
        issues.append(warning("UNSUPPORTED_FLOW", f"El flujo '{name}' es de tipo {ftype}, que está fuera del alcance de la primera versión.", where))
    if not flow.attrs.get("flowExecutionTimeInterval"):
        issues.append(warning("NO_FREQUENCY", f"El flujo '{name}' no indica cada cuánto se ejecuta.", where,
                              "Defina flowExecutionTimeInterval y unitOfTime."))

    rules = flow.get_refs("containsDataMappingRule")
    if not rules:
        issues.append(error("NO_MAPPING", f"El flujo '{name}' no tiene reglas de mapeo.", where,
                            "Indique en qué columnas se guardan las propiedades."))
    for r in rules:
        if r.cls == "PropertyToDataColumn" and (not r.get_refs("relatesColumn") or not r.get_refs("relatesSpecificProperty")):
            issues.append(error("INCOMPLETE_RULE", f"Una regla propiedad → columna del flujo '{name}' está incompleta.", where))
        if r.cls == "DataColumnToDataColumn":
            if not r.get_refs("relatesSourceColumn") or not r.get_refs("relatesDestinationColumn"):
                issues.append(error("INCOMPLETE_RULE", f"Una regla columna → columna del flujo '{name}' está incompleta.", where))
            if ftype == "DataCollectionFlow":
                issues.append(warning("RULE_FLOW_MISMATCH", f"El flujo de recolección '{name}' tiene una regla de agregación.", where))
        if r.cls == "PropertyToDataColumn" and ftype == "DataAggregationFlow":
            issues.append(warning("RULE_FLOW_MISMATCH", f"El flujo de agregación '{name}' tiene una regla propiedad → columna.", where))

    links = flow.get_refs("isSupported")
    if not links:
        issues.append(error("NO_LINKS", f"El flujo '{name}' no tiene enlaces.", where, "Defina la cadena de enlaces del flujo."))
        return issues

    in_flow = set(links)
    for link in links:
        for prev in link.get_refs("previousLink"):
            if prev not in in_flow:
                issues.append(error("CHAIN_OUTSIDE_FLOW",
                                    f"En el flujo '{name}', el enlace {_link_label(link)} sigue a un enlace de otro flujo.", where))
            elif not (_ends(prev) & _ends(link)):
                issues.append(error("CHAIN_GAP",
                                    f"En el flujo '{name}', {_link_label(prev)} y {_link_label(link)} son consecutivos pero no comparten ningún elemento.",
                                    where))
    if len(links) > 1:
        followed = {p for l in links for p in l.get_refs("previousLink") if p in in_flow}
        terminals = [l for l in links if l not in followed]
        starts = [l for l in links if not any(p in in_flow for p in l.get_refs("previousLink"))]
        if len(terminals) != 1:
            issues.append(error("BROKEN_CHAIN",
                                f"La cadena de enlaces del flujo '{name}' tiene cortes: termina en {len(terminals)} puntos "
                                f"({', '.join(_link_label(t) for t in terminals)}).", where,
                                "Encadene los enlaces con previousLink desde el origen del dato hasta la tabla."))
        if _has_cycle(links):
            issues.append(error("CYCLIC_CHAIN", f"La cadena de enlaces del flujo '{name}' tiene un ciclo.", where))
        if not starts:
            issues.append(error("BROKEN_CHAIN", f"La cadena del flujo '{name}' no tiene un enlace inicial.", where))
    last = [l for l in links if l not in {p for x in links for p in x.get_refs("previousLink")}]
    if len(last) == 1 and last[0].cls != "LinkServiceToDataTable":
        issues.append(warning("CHAIN_END", f"El flujo '{name}' no termina guardando en una tabla (último enlace: {last[0].cls}).", where))
    return issues


def _ends(link: MObject) -> set[MObject]:
    a, b = LINK_ENDS.get(link.cls, ("", ""))
    return set(link.get_refs(a)) | set(link.get_refs(b))


def _has_cycle(links: list[MObject]) -> bool:
    state: dict[MObject, int] = {}

    def visit(l: MObject) -> bool:
        state[l] = 1
        for p in l.get_refs("previousLink"):
            if state.get(p) == 1 or (p in links and p not in state and visit(p)):
                return True
        state[l] = 2
        return False

    return any(l not in state and visit(l) for l in links)


def _link_label(link: MObject) -> str:
    src_f, dst_f = LINK_ENDS.get(link.cls, ("", ""))
    src = link.get_refs(src_f)
    dst = link.get_refs(dst_f)
    s = src[0].name if src else "?"
    d = dst[0].name if dst else "?"
    return f"{link.cls}({s} → {d})"
