"""Carga el metamodelo Monitor-IoT (tesismetamodelo.ecore) y lo expone como objetos Python.

Todo el resto del sistema (generador, lector y validador XMI) se guía por esta
información, de modo que si el .ecore cambia basta con reemplazar el archivo (RNF-17).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
import xml.etree.ElementTree as ET

ECORE_PATH = Path(__file__).parent / "knowledge" / "tesismetamodelo.ecore"

XSI = "http://www.w3.org/2001/XMLSchema-instance"
XMI = "http://www.omg.org/XMI"

PRIMITIVES = {"EString", "EInt", "EBoolean", "EDate", "EDouble", "EFloat", "ELong"}


@dataclass
class EFeature:
    name: str
    kind: str  # "attribute" | "reference"
    type: str  # nombre de EClass, EEnum o primitivo (EString, EInt...)
    lower: int = 0
    upper: int = 1  # -1 = muchos
    containment: bool = False
    opposite: str | None = None
    default: str | None = None
    owner: str = ""

    @property
    def many(self) -> bool:
        return self.upper == -1 or self.upper > 1


@dataclass
class EClass:
    name: str
    abstract: bool = False
    supertypes: list[str] = field(default_factory=list)
    features: list[EFeature] = field(default_factory=list)  # solo las propias


@dataclass
class EEnum:
    name: str
    literals: list[str] = field(default_factory=list)

    @property
    def default(self) -> str:
        return self.literals[0]


class Metamodel:
    def __init__(self, path: Path = ECORE_PATH):
        root = ET.parse(path).getroot()
        self.name = root.get("name")
        self.ns_uri = root.get("nsURI")
        self.ns_prefix = root.get("nsPrefix")
        self.classes: dict[str, EClass] = {}
        self.enums: dict[str, EEnum] = {}
        for cl in root.findall("eClassifiers"):
            kind = cl.get(f"{{{XSI}}}type")
            name = cl.get("name")
            if kind == "ecore:EEnum":
                self.enums[name] = EEnum(name, [lit.get("name") for lit in cl.findall("eLiterals")])
            elif kind == "ecore:EClass":
                ec = EClass(
                    name,
                    abstract=cl.get("abstract") == "true",
                    supertypes=[_local(s) for s in (cl.get("eSuperTypes") or "").split()],
                )
                for sf in cl.findall("eStructuralFeatures"):
                    is_ref = sf.get(f"{{{XSI}}}type") == "ecore:EReference"
                    opp = sf.get("eOpposite")
                    ec.features.append(
                        EFeature(
                            name=sf.get("name"),
                            kind="reference" if is_ref else "attribute",
                            type=_local(sf.get("eType")),
                            lower=int(sf.get("lowerBound", "0")),
                            upper=int(sf.get("upperBound", "1")),
                            containment=sf.get("containment") == "true",
                            opposite=opp.split("/")[-1] if opp else None,
                            default=sf.get("defaultValueLiteral"),
                            owner=name,
                        )
                    )
                self.classes[name] = ec
        self._all_features: dict[str, list[EFeature]] = {}

    # ---- consultas -------------------------------------------------------
    def all_supertypes(self, cls: str) -> list[str]:
        """Supertipos en orden de EMF (primero los más generales), sin repetir."""
        out: list[str] = []
        for st in self.classes[cls].supertypes:
            for s in self.all_supertypes(st) + [st]:
                if s not in out:
                    out.append(s)
        return out

    def all_features(self, cls: str) -> list[EFeature]:
        """eAllStructuralFeatures: heredadas primero, en el orden del .ecore."""
        if cls not in self._all_features:
            feats: list[EFeature] = []
            for c in self.all_supertypes(cls) + [cls]:
                feats.extend(self.classes[c].features)
            self._all_features[cls] = feats
        return self._all_features[cls]

    def feature(self, cls: str, name: str) -> EFeature | None:
        for f in self.all_features(cls):
            if f.name == name:
                return f
        return None

    def is_subtype(self, cls: str, of: str) -> bool:
        return cls == of or of in self.all_supertypes(cls)

    def concrete_subtypes(self, cls: str) -> list[str]:
        return [c for c, ec in self.classes.items() if not ec.abstract and self.is_subtype(c, cls)]

    def default_value(self, f: EFeature):
        """Valor por defecto según EMF (se usa al leer un XMI que omite el atributo)."""
        if f.kind != "attribute":
            return None
        if f.type in self.enums:
            return f.default or self.enums[f.type].default
        if f.default is not None:
            return parse_primitive(f.type, f.default)
        return {"EInt": 0, "ELong": 0, "EDouble": 0.0, "EFloat": 0.0, "EBoolean": False}.get(f.type)


def parse_primitive(type_name: str, text: str):
    if type_name in ("EInt", "ELong"):
        return int(text)
    if type_name in ("EDouble", "EFloat"):
        return float(text)
    if type_name == "EBoolean":
        if text not in ("true", "false"):
            raise ValueError(f"'{text}' no es un booleano (true/false)")
        return text == "true"
    return text


def _local(ref: str | None) -> str:
    """'#//IoTSystem' -> 'IoTSystem'; 'ecore:EDataType http://...#//EString' -> 'EString'."""
    if not ref:
        return ""
    return ref.split("#//")[-1]


@lru_cache
def get_metamodel() -> Metamodel:
    return Metamodel()
