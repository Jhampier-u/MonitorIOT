"""Construye un modelo a partir de una especificación JSON (la que entregará el agente).

Esta es la respuesta al riesgo R002: el agente NO escribe referencias por posición ni
relaciones de doble sentido. Describe el modelo como un árbol JSON en el que:

- cada objeto lleva su clase en "eClass" (se puede omitir si es la del tipo declarado),
- puede llevar una "key" única para que otros objetos lo referencien,
- los atributos se escriben con su nombre del metamodelo ("name", "sensorType"...),
- las relaciones de contención son listas de objetos hijos ("containsEntity": [...]),
- las demás relaciones se escriben con la key (o lista de keys) del destino.

El programa calcula las referencias por posición, completa el lado opuesto de cada
relación bidireccional y asigna identificadores numéricos si faltan.

Ejemplo mínimo:
{
  "name": "Bedroom temperature monitoring",
  "containsEntity": [
    {"eClass": "PhysicalEntity", "key": "house", "name": "House",
     "containsComputingNode": [{"eClass": "IoTGateway", "key": "rpi", "name": "RaspberryPi3"}]}
  ]
}
"""
from __future__ import annotations

from .issues import Issue, error
from .metamodel import Metamodel
from .model import MObject, Model
from .xmi import ROOT_CLASS

RESERVED = {"eClass", "key"}


class SpecError(Exception):
    def __init__(self, issues: list[Issue]):
        super().__init__("; ".join(i.message for i in issues))
        self.issues = issues


def build_model(spec: dict, mm: Metamodel, assign_ids: bool = True) -> Model:
    issues: list[Issue] = []
    keys: dict[str, MObject] = {}
    pending: list[tuple[MObject, str, list[str]]] = []

    def build(node: dict, declared: str, where: str) -> MObject | None:
        if not isinstance(node, dict):
            issues.append(error("SPEC_NOT_OBJECT", f"En {where} se esperaba un objeto JSON.", where))
            return None
        cls = node.get("eClass", declared)
        if cls not in mm.classes:
            issues.append(error("UNKNOWN_CLASS", f"La clase '{cls}' no existe en el metamodelo.", where))
            return None
        if not mm.is_subtype(cls, declared):
            issues.append(error("WRONG_CLASS", f"Un {cls} no puede ir en un lugar donde se espera {declared}.", where))
            return None
        if mm.classes[cls].abstract:
            options = ", ".join(mm.concrete_subtypes(cls))
            issues.append(error("ABSTRACT_CLASS", f"{cls} es abstracta; indique el tipo concreto ({options}).", where))
            return None
        obj = MObject(cls)
        label = f"{where}/{node.get('name', cls)}"
        key = node.get("key")
        if key is not None:
            if key in keys:
                issues.append(error("DUPLICATE_KEY", f"La key '{key}' está repetida.", label))
            keys[key] = obj
        for name, value in node.items():
            if name in RESERVED:
                continue
            f = mm.feature(cls, name)
            if f is None:
                issues.append(error("UNKNOWN_FEATURE", f"La clase {cls} no tiene el dato '{name}'.", label))
                continue
            if f.kind == "attribute":
                obj.attrs[name] = value
            elif f.containment:
                items = value if isinstance(value, list) else [value]
                for i, child in enumerate(items):
                    built = build(child, f.type, f"{label}/{name}[{i}]")
                    if built is not None:
                        obj.add_child(name, built)
            else:
                targets = value if isinstance(value, list) else [value]
                pending.append((obj, name, [str(t) for t in targets]))
        return obj

    spec = dict(spec)
    spec.setdefault("eClass", ROOT_CLASS)
    root = build(spec, ROOT_CLASS, "model")
    if root is None:
        raise SpecError(issues)

    for obj, name, targets in pending:
        for t in targets:
            target = keys.get(t)
            if target is None:
                issues.append(error("UNKNOWN_KEY", f"'{name}' de '{obj.label()}' usa la key '{t}', que no existe.", obj.label()))
                continue
            expected = mm.feature(obj.cls, name).type
            if not mm.is_subtype(target.cls, expected):
                issues.append(error("WRONG_REF_TYPE",
                                    f"'{name}' de '{obj.label()}' debe apuntar a un {expected}, pero '{t}' es {target.cls}.",
                                    obj.label()))
                continue
            obj.add_ref(name, target)

    if issues:
        raise SpecError(issues)

    model = Model(mm, root)
    complete_opposites(model)
    if assign_ids:
        _assign_ids(model)
    return model


def complete_opposites(model: Model) -> None:
    """Para cada relación con eOpposite, asegura que el destino apunte de vuelta al origen."""
    mm = model.mm
    for obj in list(model.walk()):
        for f in mm.all_features(obj.cls):
            if f.kind != "reference" or not f.opposite:
                continue
            for target in list(obj.get_refs(f.name)):
                opp = mm.feature(target.cls, f.opposite)
                if opp is None:
                    continue
                if opp.many:
                    target.add_ref(opp.name, obj)
                else:
                    target.refs[opp.name] = [obj]


def _assign_ids(model: Model) -> None:
    mm = model.mm
    used: set[int] = set()
    for obj in model.walk():
        v = obj.attrs.get("id")
        if isinstance(v, int):
            used.add(v)
        elif isinstance(v, str) and v.isdigit():
            used.add(int(v))
    nxt = 1
    for obj in model.walk():
        f = mm.feature(obj.cls, "id")
        if f is None or obj.attrs.get("id") not in (None, ""):
            continue
        while nxt in used:
            nxt += 1
        obj.attrs["id"] = str(nxt) if f.type == "EString" else nxt
        used.add(nxt)
