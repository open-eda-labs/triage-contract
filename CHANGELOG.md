# Changelog

Formato baseado em Keep a Changelog; versões seguem semver.

## [0.1.0] - não lançada

### Adicionado

- `schemas/alert-event.json`: envelope CloudEvents 1.0 com `traceparent` e `dataref`; tipos `alert.firing`, `alert.resolved` e `vulnerability.detected`.
- `schemas/recommendation.schema.json`: até 3 hipóteses com evidência estruturada, `not_enough_evidence`, ação sugerida, status (`recommended`, `pr_opened`, `no_change`, `failed`) e bloco `fix` do vuln fixer.
- Exemplos válidos e inválidos para os dois schemas e `tests/test_schemas.py`.
- `AGENTS.md` e skills `triage-recommendation` e `vuln-fix-maven`.
- CI com yamllint, markdownlint e pytest.
