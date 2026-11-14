"""Valida os schemas do contrato e os exemplos em examples/."""

import json
import pathlib

import pytest
from jsonschema import Draft202012Validator

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCHEMAS = {
    "alert-event": ROOT / "schemas" / "alert-event.json",
    "recommendation": ROOT / "schemas" / "recommendation.schema.json",
}
FORMAT_CHECKER = Draft202012Validator.FORMAT_CHECKER

# Cada exemplo inválido precisa falhar pelo motivo certo: ao menos um erro
# com uma destas palavras-chave do JSON Schema.
EXPECTED_INVALID = {
    "alert-event": {
        "extra-field-in-data": {"additionalProperties"},
        "raw-payload-in-envelope": {"additionalProperties"},
        "wrong-specversion": {"const"},
        "rule-name-too-long": {"maxLength"},
        "url-in-rule-name": {"pattern"},
        "traceparent-all-zero": {"pattern"},
        "missing-dataref": {"required"},
        "vulnerability-from-grafana-source": {"pattern"},
        "resolved-without-ends-at": {"required"},
        "unknown-type": {"enum"},
    },
    "recommendation": {
        "extra-field-in-hypothesis": {"additionalProperties"},
        "url-in-cause": {"pattern"},
        "markdown-link-in-action": {"pattern"},
        "markdown-image-in-evidence": {"pattern"},
        "slack-link-syntax-in-action": {"pattern"},
        "cause-too-long": {"maxLength"},
        "status-out-of-enum": {"enum"},
        "not-enough-evidence-with-hypotheses": {"maxItems"},
        "four-hypotheses": {"maxItems"},
        "numeric-confidence": {"enum"},
        "pr-opened-without-pr-number": {"required"},
        "triage-with-pr-opened": {"enum"},
        "failed-without-reason": {"required"},
        "multiline-text": {"pattern"},
        "recommended-without-hypotheses": {"minItems"},
    },
}


def load(path):
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def validator(name):
    return Draft202012Validator(load(SCHEMAS[name]), format_checker=FORMAT_CHECKER)


def examples(name, kind):
    return sorted((ROOT / "examples" / name / kind).glob("*.json"))


def cases(kind):
    return [
        pytest.param(name, path, id=f"{name}/{kind}/{path.stem}")
        for name in SCHEMAS
        for path in examples(name, kind)
    ]


def walk(node, pointer=""):
    """Percorre todos os subschemas (dicts) com o JSON Pointer de cada um."""
    if isinstance(node, dict):
        yield pointer, node
        for key, value in node.items():
            yield from walk(value, f"{pointer}/{key}")
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield from walk(value, f"{pointer}/{i}")


@pytest.mark.parametrize("name", SCHEMAS)
def test_schema_is_valid_against_metaschema(name):
    schema = load(SCHEMAS[name])
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(SCHEMAS[name].name)
    assert schema["title"]
    Draft202012Validator.check_schema(schema)


def test_date_time_format_is_enforced():
    # Sem rfc3339-validator o format "date-time" é ignorado em silêncio.
    assert "date-time" in FORMAT_CHECKER.checkers
    assert not FORMAT_CHECKER.conforms("2026-13-45T25:00:00Z", "date-time")


@pytest.mark.parametrize("name", SCHEMAS)
def test_schema_is_closed_and_bounded(name):
    """Guardrail D-13: todo objeto fechado, toda string e todo array limitados."""
    for pointer, node in walk(load(SCHEMAS[name])):
        kind = node.get("type")
        if kind == "object" and pointer != "/properties/data":
            assert node.get("additionalProperties") is False, pointer
        if kind == "string":
            assert "maxLength" in node, pointer
        if kind == "array":
            assert "maxItems" in node, pointer


def test_event_reference_matches_alert_event():
    """recommendation.event usa as mesmas regras de source e id do evento."""
    event = load(SCHEMAS["alert-event"])["$defs"]
    ref = load(SCHEMAS["recommendation"])["properties"]["event"]["properties"]
    for field, definition in (("source", "eventSource"), ("id", "eventId")):
        assert ref[field]["pattern"] == event[definition]["pattern"]
        assert ref[field]["maxLength"] == event[definition]["maxLength"]


@pytest.mark.parametrize("name,kind,minimum", [
    ("alert-event", "valid", 3),
    ("alert-event", "invalid", 5),
    ("recommendation", "valid", 3),
    ("recommendation", "invalid", 5),
])
def test_minimum_number_of_examples(name, kind, minimum):
    assert len(examples(name, kind)) >= minimum


@pytest.mark.parametrize("name,path", cases("valid"))
def test_valid_example_passes(name, path):
    errors = [e.message for e in validator(name).iter_errors(load(path))]
    assert errors == []


@pytest.mark.parametrize("name,path", cases("invalid"))
def test_invalid_example_fails_for_the_expected_reason(name, path):
    expected = EXPECTED_INVALID[name].get(path.stem)
    assert expected, f"adicione {path.stem} em EXPECTED_INVALID"
    errors = list(validator(name).iter_errors(load(path)))
    assert errors, "exemplo inválido passou na validação"
    found = {e.validator for err in errors for e in [err, *err.context]}
    assert found & expected, f"esperado {expected}, encontrado {found}"


@pytest.mark.parametrize("name", SCHEMAS)
def test_every_expected_invalid_has_a_file(name):
    stems = {p.stem for p in examples(name, "invalid")}
    assert set(EXPECTED_INVALID[name]) == stems
