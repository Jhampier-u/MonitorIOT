import json
from pathlib import Path

import pytest

from app.builder import SpecError, build_model
from app.metamodel import get_metamodel
from app.validator import validate
from app.xmi import read_xmi, write_xmi

EXAMPLE = Path(__file__).resolve().parent.parent / "app" / "knowledge" / "examples" / "emergency_case.json"
MM = get_metamodel()


def codes(issues, severity="error"):
    return {i.code for i in issues if i.severity == severity}


def minimal_spec():
    return {
        "name": "Bedroom temperature monitoring",
        "containsEntityCategory": [{"name": "Room", "hasPropertyTemplate": [{"key": "tpl", "name": "temperature"}]}],
        "containsEntity": [{
            "eClass": "PhysicalEntity", "key": "house", "name": "House",
            "containsComputingNode": [{
                "eClass": "IoTGateway", "key": "rpi", "name": "RaspberryPi3",
                "containsResource": [{"eClass": "API", "key": "api", "name": "getTemperature"}],
            }],
            "containsSubPhysicalEntity": [{
                "key": "bedroom", "name": "Bedroom",
                "hasProperty": [{"name": "temperature", "isBasedOn": "tpl"}],
                "containsComputingNode": [{"eClass": "Sensor", "key": "sensor", "name": "TemperatureSensor", "isControlled": "rpi"}],
            }],
        }],
        "containsDataFlow": [{"key": "flow", "description": "Temperature"}],
        "containsLink": [{"eClass": "LinkAPIToIoTDevice", "supports": "flow", "linksIoTDevice": "sensor", "linksAPI": "api"}],
    }


def test_metamodel_loaded():
    assert MM.ns_uri == "http://www.uazuay.edu.ec/MonitorIoT"
    assert MM.classes["Entity"].abstract
    assert MM.feature("DataTable", "hasLinkServiceToDatable").opposite == "linksDataTable"
    assert MM.default_value(MM.feature("DataFlow", "communicationType")) == "Asynchronous"
    assert MM.default_value(MM.feature("DataFlow", "dataFlowType")) == "DataCollectionFlow"


def test_positional_references_and_opposites_like_appendix_d():
    xmi = write_xmi(build_model(minimal_spec(), MM))
    sensor = "//@containsEntity.0/@containsSubPhysicalEntity.0/@containsComputingNode.0"
    api = "//@containsEntity.0/@containsComputingNode.0/@containsResource.0"
    assert f'linksIoTDevice="{sensor}"' in xmi and f'linksAPI="{api}"' in xmi
    assert 'hasLinkAPIToIoTDevice="//@containsLink.0"' in xmi  # el lado opuesto se completó
    assert 'isControlled="//@containsEntity.0/@containsComputingNode.0"' in xmi
    assert 'controls="' + sensor + '"' in xmi
    assert "communicationType" not in xmi  # valor por defecto omitido


def test_example_case_is_valid_and_round_trips():
    model = build_model(json.loads(EXAMPLE.read_text(encoding="utf-8")), MM)
    xmi = write_xmi(model)
    again, issues = read_xmi(xmi, MM)
    assert issues == []
    assert validate(again) == []
    assert write_xmi(again) == xmi


def test_spec_errors_are_reported():
    spec = minimal_spec()
    spec["containsEntity"][0]["colour"] = "red"
    spec["containsLink"][0]["linksAPI"] = "nope"
    with pytest.raises(SpecError) as e:
        build_model(spec, MM)
    assert {i.code for i in e.value.issues} == {"UNKNOWN_FEATURE", "UNKNOWN_KEY"}


def test_validator_detects_metamodel_errors():
    model = build_model(minimal_spec(), MM)
    sensor = next(o for o in model.walk() if o.cls == "Sensor")
    sensor.attrs["sensorType"] = "Laser"  # no existe en la enumeración
    prop = next(o for o in model.walk() if o.cls == "Property")
    prop.refs.pop("isBasedOn")  # propiedad sin plantilla
    sensor.refs["hasLinkAPIToIoTDevice"] = []  # relación de doble sentido incompleta
    assert {"BAD_VALUE", "MISSING_REQUIRED", "MISSING_OPPOSITE"} <= codes(validate(model))


def test_validator_detects_broken_chain():
    spec = minimal_spec()
    rpi = spec["containsEntity"][0]["containsComputingNode"][0]
    rpi["containsResource"].append({"eClass": "Application", "key": "app", "name": "controller"})
    spec["containsLink"].append({"eClass": "LinkAppToAPI", "supports": "flow", "linksAPI": "api", "linksApp": "app"})
    found = codes(validate(build_model(spec, MM)))
    assert "BROKEN_CHAIN" in found and "NO_MAPPING" in found


def test_reader_rejects_non_monitoriot_xml():
    with pytest.raises(ValueError):
        read_xmi("<root/>", MM)
