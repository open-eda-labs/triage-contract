"""Valida os schemas do contrato e os exemplos em examples/."""

import copy
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
        "trailing-newline-in-id": {"pattern"},
        "email-in-event-id": {"pattern"},
        "colon-in-rule-name": {"pattern"},
        "dataref-scheme-not-allowed": {"pattern"},
        "dataref-dot-dot-segment": {"pattern"},
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
        "trailing-newline-in-cause": {"pattern"},
        "line-separator-in-text": {"pattern"},
        "protocol-relative-url-in-text": {"pattern"},
        "tel-scheme-in-text": {"pattern"},
        "bare-domain-path-in-cause": {"pattern"},
        "at-sign-in-query-id": {"pattern"},
        "dot-dot-in-query-id": {"pattern"},
        "triage-with-build-failed": {"enum"},
        "no-change-with-patch-hash": {"not"},
    },
}

# Quebras de linha que o texto livre não pode conter (safeText).
LINE_BREAKS = ["\r", "\n", "\u000b", "\u000c", "\u0085", "\u2028", "\u2029"]


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


def string_leaves(node, path=()):
    """Caminhos de todas as strings de um documento JSON."""
    if isinstance(node, str):
        yield path
    elif isinstance(node, dict):
        for key, value in node.items():
            yield from string_leaves(value, (*path, key))
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield from string_leaves(value, (*path, i))


def replaced(doc, path, fn):
    doc = copy.deepcopy(doc)
    node = doc
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = fn(node[path[-1]])
    return doc


@pytest.mark.parametrize("name,path", cases("valid"))
def test_trailing_newline_is_rejected_in_every_string(name, path):
    """re.search aceita "\\n" antes de `$`; os patterns precisam barrar isso."""
    doc, check = load(path), validator(name)
    for leaf in string_leaves(doc):
        bad = replaced(doc, leaf, lambda s: s + "\n")
        assert not check.is_valid(bad), f"{'/'.join(map(str, leaf))} aceitou newline final"


@pytest.mark.parametrize("char", LINE_BREAKS, ids=[f"U+{ord(c):04X}" for c in LINE_BREAKS])
def test_safe_text_rejects_line_breaks(char):
    doc = load(ROOT / "examples" / "recommendation" / "valid" / "triage-hypotheses.json")
    check = validator("recommendation")
    for leaf in (("suggested_action", "text"), ("hypotheses", 0, "cause"),
                 ("hypotheses", 0, "evidence", 0, "value")):
        bad = replaced(doc, leaf, lambda s: f"antes{char}depois")
        assert not check.is_valid(bad), leaf


@pytest.mark.parametrize("text", [
    "java.lang.OutOfMemoryError no pod demo-service",
    "data: 14/11, latência p95 em 2.17.1",
    "requests/failed acima de 10 por minuto",
])
def test_safe_text_keeps_legitimate_causes(text):
    doc = load(ROOT / "examples" / "recommendation" / "valid" / "triage-hypotheses.json")
    doc["hypotheses"][0]["cause"] = text
    assert validator("recommendation").is_valid(doc)


def test_every_event_type_closes_data_with_ref():
    """Todo valor de `type` cai num ramo `then` que fecha `data` com `$ref`."""
    schema = load(SCHEMAS["alert-event"])
    for event_type in schema["properties"]["type"]["enum"]:
        refs = []
        for branch in schema["allOf"]:
            cond = branch["if"]["properties"]["type"]
            matches = cond.get("const") == event_type or event_type in cond.get("enum", [])
            data = branch["then"].get("properties", {}).get("data", {})
            if matches and "$ref" in data:
                refs.append(data["$ref"])
        assert len(refs) == 1, (event_type, refs)
        target = schema["$defs"][refs[0].rsplit("/", 1)[-1]]
        assert target["additionalProperties"] is False


@pytest.mark.parametrize("name", SCHEMAS)
def test_every_expected_invalid_has_a_file(name):
    stems = {p.stem for p in examples(name, "invalid")}
    assert set(EXPECTED_INVALID[name]) == stems
