"""Representación en memoria de un modelo Monitor-IoT (un grafo de objetos).

Cada objeto conoce su clase del metamodelo, sus atributos, sus referencias y su
contenedor. A partir de la posición en el árbol de contención se calculan las
referencias por posición que usa EMF (//@containsEntity.0/@containsComputingNode.1).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator

from .metamodel import Metamodel


@dataclass(eq=False)
class MObject:
    cls: str
    attrs: dict[str, object] = field(default_factory=dict)
    # Todas las referencias (de contención o no) se guardan como listas.
    refs: dict[str, list["MObject"]] = field(default_factory=dict)
    container: "MObject | None" = None
    container_feature: str | None = None

    def get_refs(self, name: str) -> list["MObject"]:
        return self.refs.get(name, [])

    def add_ref(self, name: str, target: "MObject") -> None:
        lst = self.refs.setdefault(name, [])
        if target not in lst:
            lst.append(target)

    def add_child(self, feature: str, child: "MObject") -> None:
        self.refs.setdefault(feature, []).append(child)
        child.container = self
        child.container_feature = feature

    @property
    def name(self) -> str:
        return str(self.attrs.get("name") or self.attrs.get("description") or "")

    def label(self) -> str:
        return f"{self.name or '(sin nombre)'} : {self.cls}"


class Model:
    def __init__(self, mm: Metamodel, root: MObject):
        self.mm = mm
        self.root = root

    def children(self, obj: MObject) -> Iterator[tuple[str, int, MObject]]:
        for f in self.mm.all_features(obj.cls):
            if f.kind == "reference" and f.containment:
                for i, child in enumerate(obj.get_refs(f.name)):
                    yield f.name, i, child

    def walk(self) -> Iterator[MObject]:
        stack = [self.root]
        while stack:
            obj = stack.pop()
            yield obj
            stack.extend(reversed([c for _, _, c in self.children(obj)]))

    def paths(self) -> dict[MObject, str]:
        """Referencia por posición de cada objeto (el raíz es '/')."""
        out: dict[MObject, str] = {self.root: "/"}

        def visit(obj: MObject, path: str) -> None:
            for feat, i, child in self.children(obj):
                p = f"{path}/@{feat}.{i}"
                out[child] = p
                visit(child, p)

        visit(self.root, "/")
        return out

    def to_json(self) -> dict:
        """Vista neutral del modelo para el visor: nodos con todos sus datos (con defaults)."""
        paths = self.paths()
        nodes = []
        for obj in self.walk():
            attrs = {}
            refs = {}
            for f in self.mm.all_features(obj.cls):
                if f.kind == "attribute":
                    v = obj.attrs.get(f.name, self.mm.default_value(f))
                    attrs[f.name] = v
                elif not f.containment and obj.get_refs(f.name):
                    refs[f.name] = [paths[t] for t in obj.get_refs(f.name) if t in paths]
            nodes.append(
                {
                    "id": paths[obj],
                    "cls": obj.cls,
                    "supertypes": self.mm.all_supertypes(obj.cls),
                    "name": obj.name,
                    "parent": paths.get(obj.container) if obj.container else None,
                    "feature": obj.container_feature,
                    "attrs": attrs,
                    "refs": refs,
                }
            )
        return {"nodes": nodes}

    def stats(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for obj in self.walk():
            counts[obj.cls] = counts.get(obj.cls, 0) + 1
        return counts
