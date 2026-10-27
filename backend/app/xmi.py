"""Escritura y lectura de archivos XMI compatibles con Obeo Designer (RNF-07, RNF-08).

Reglas del formato (ERS, Apéndice D):
- XMI 2.0, espacio de nombres http://www.uazuay.edu.ec/MonitorIoT, raíz MonitoringArchitectureModel.
- Referencias entre elementos por posición: //@containsEntity.0/@containsComputingNode.1
- xsi:type solo cuando la clase real es distinta del tipo declarado en la relación.
- Los atributos con el valor por defecto del metamodelo no se escriben.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

from .issues import Issue, error
from .metamodel import XMI, XSI, Metamodel, parse_primitive
from .model import MObject, Model

ROOT_CLASS = "MonitoringArchitectureModel"


# ---------------------------------------------------------------- escritura
def write_xmi(model: Model) -> str:
    mm = model.mm
    ns = mm.ns_uri
    ET.register_namespace("xmi", XMI)
    ET.register_namespace("xsi", XSI)
    ET.register_namespace(mm.ns_prefix, ns)
    paths = model.paths()

    def fill(el: ET.Element, obj: MObject) -> None:
        children: list[tuple[str, MObject]] = []
        for f in mm.all_features(obj.cls):
            if f.kind == "attribute":
                if f.name not in obj.attrs:
                    continue
                v = obj.attrs[f.name]
                if v is None or v == mm.default_value(f):
                    continue
                el.set(f.name, _to_text(v))
            elif f.containment:
                children.extend((f.name, c) for c in obj.get_refs(f.name))
            else:
                targets = [paths[t] for t in obj.get_refs(f.name) if t in paths]
                if targets:
                    el.set(f.name, " ".join(targets))
        for feat, child in children:
            sub = ET.SubElement(el, feat)
            declared = mm.feature(obj.cls, feat).type
            if child.cls != declared:
                sub.set(f"{{{XSI}}}type", f"{mm.ns_prefix}:{child.cls}")  # primero, como EMF
            fill(sub, child)

    root = ET.Element(f"{{{ns}}}{ROOT_CLASS}")
    root.set(f"{{{XMI}}}version", "2.0")
    fill(root, model.root)
    ET.indent(root, space="  ")
    body = ET.tostring(root, encoding="unicode")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + body + "\n"


def _to_text(v: object) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)


# ------------------------------------------------------------------ lectura
def read_xmi(text: str | bytes, mm: Metamodel) -> tuple[Model, list[Issue]]:
    """Reconstruye el modelo desde un XMI. Lo que no se pueda interpretar se informa como error."""
    issues: list[Issue] = []
    try:
        root_el = ET.fromstring(text)
    except ET.ParseError as e:
        raise ValueError(f"El archivo no es un XML válido: {e}") from e

    tag = root_el.tag.split("}")[-1]
    if not root_el.tag.startswith(f"{{{mm.ns_uri}}}") or tag != ROOT_CLASS:
        raise ValueError(
            f"El archivo no es un modelo Monitor-IoT: se esperaba la raíz {mm.ns_prefix}:{ROOT_CLASS} "
            f"con el espacio de nombres {mm.ns_uri}."
        )

    pending: list[tuple[MObject, str, list[str]]] = []

    def build(el: ET.Element, cls: str) -> MObject:
        obj = MObject(cls)
        for key, raw in el.attrib.items():
            if key.startswith("{"):
                continue  # xmi:version, xsi:type, etc.
            f = mm.feature(cls, key)
            if f is None:
                issues.append(error("UNKNOWN_FEATURE", f"La clase {cls} no tiene el dato '{key}' en el metamodelo.", cls))
                continue
            if f.kind == "attribute":
                obj.attrs[key] = _parse_attr(mm, f.type, raw)
            elif f.containment:
                issues.append(error("BAD_CONTAINMENT", f"'{key}' de {cls} debe ser un elemento hijo, no un atributo.", cls))
            else:
                pending.append((obj, key, raw.split()))
        for child_el in el:
            feat = child_el.tag.split("}")[-1]
            f = mm.feature(cls, feat)
            if f is None or f.kind != "reference" or not f.containment:
                issues.append(error("UNKNOWN_FEATURE", f"La clase {cls} no puede contener elementos '{feat}'.", cls))
                continue
            xsi_type = child_el.get(f"{{{XSI}}}type")
            child_cls = xsi_type.split(":")[-1] if xsi_type else f.type
            if child_cls not in mm.classes:
                issues.append(error("UNKNOWN_CLASS", f"La clase '{child_cls}' no existe en el metamodelo.", cls))
                continue
            obj.add_child(feat, build(child_el, child_cls))
        return obj

    root = build(root_el, ROOT_CLASS)
    model = Model(mm, root)
    by_path = {p: o for o, p in model.paths().items()}
    for obj, feat, targets in pending:
        for t in targets:
            target = by_path.get(t)
            if target is None:
                issues.append(
                    error("UNRESOLVED_REF", f"La referencia '{feat}' de '{obj.label()}' apunta a '{t}', que no existe.",
                          None, "Revise que el elemento referenciado exista en el modelo.")
                )
            else:
                obj.refs.setdefault(feat, []).append(target)
    return model, issues


def _parse_attr(mm: Metamodel, type_name: str, raw: str):
    if type_name in mm.enums:
        return raw
    try:
        return parse_primitive(type_name, raw)
    except ValueError:
        return raw  # el validador informará el tipo incorrecto
