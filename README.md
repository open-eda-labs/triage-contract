# triage-contract

Contrato versionado entre as peças do laboratório open-eda-labs: o evento que entra, a recomendação que sai e as instruções para agentes. Intake-adapter, agent-workflows, triage-eval, publicação Slack/Teams e vuln fixer dependem só deste repositório, nunca uns dos outros (D-01, D-27).

Plano de origem: [Plano Mestre](https://github.com/open-eda-labs/open-eda-labs.github.io/blob/main/docs/PLANO_MESTRE.md).

## Layout

| Caminho | Conteúdo |
| --- | --- |
| `schemas/alert-event.json` | Evento de entrada: envelope CloudEvents 1.0 com `data` próprio (alerta ou vulnerabilidade) |
| `schemas/recommendation.schema.json` | Saída da triagem read-only e do vuln fixer |
| `examples/<schema>/valid/`, `examples/<schema>/invalid/` | Exemplos sintéticos; os inválidos documentam o que o schema barra |
| `tests/test_schemas.py` | Valida schemas contra o metaschema e todos os exemplos |
| `AGENTS.md` | Regras para qualquer harness de agente (D-15) |
| `.agents/skills/` | Skills `triage-recommendation` e `vuln-fix-maven` |

## Validar localmente

Requer Python 3.12. Crie o venv fora do repositório:

```sh
python3 -m venv ~/.venvs/triage-contract
~/.venvs/triage-contract/bin/pip install -r requirements-dev.txt
~/.venvs/triage-contract/bin/pytest -q
pipx run yamllint==1.35.1 --strict .
npx --yes markdownlint-cli2@0.14.0 "**/*.md"
```

`rfc3339-validator` é necessário: sem ele o `format: date-time` é ignorado em silêncio, e há teste que falha nesse caso.

## Tipos de evento

| `type` | `source` | `data` |
| --- | --- | --- |
| `io.github.open-eda-labs.alert.firing` | `/grafana/<instância>`, `/azure-monitor/<instância>`, `/datadog/<instância>` | alerta |
| `io.github.open-eda-labs.alert.resolved` | idem | alerta, com `ends_at` |
| `io.github.open-eda-labs.vulnerability.detected` | `/osv-scanner/<instância>`, `/dependabot/<instância>` | vulnerabilidade Maven |

Duplicata é o mesmo par `source` + `id`. No achado do OSV-Scanner, `id` = `<advisory>:<owner/repo>:<groupId:artifactId>`.

## Campo e decisão

| Campo | Regra | Decisão |
| --- | --- | --- |
| envelope, `specversion` 1.0 | CloudEvents estruturado, sem extensões além das listadas | D-10 |
| `source` + `id` | definem duplicata | D-10 |
| `source` por emissor | um adapter por fonte, todos em CloudEvents | D-36, D-30 |
| `traceparent` | obrigatório; seu trace-id é o `trace_id` da saída | D-12 |
| `dataref` | payload completo fora do evento, sem query nem credencial | D-10, D-22 |
| `data` fechado e curto | só campos permitidos D0/D1, sem texto livre do emissor | D-22, D-42, D-43 |
| `data` de vulnerabilidade | advisory, repositório, pacote Maven, versões | D-29, D-30 |
| `hypotheses` (até 3), `confidence`, `evidence` | evidência como referência a consulta fixa | D-06, D-11, G-P1 |
| `not_enough_evidence` | true exige zero hipóteses | D-11, G-P1 |
| `status` | `pr_opened`, `no_change`, `failed`; `recommended` para read-only | D-11, D-02 |
| `fix` | nível N1/N2, hash do patch, número do PR, CI, re-scan | D-28, D-31, P5 |
| `versions` | schema, prompt e nome lógico do modelo | D-09, P1 |
| `additionalProperties: false`, `maxLength`, texto sem URL e sem markdown de link | guardrail por arquitetura; links montados pelo workflow | D-13, R-01, R-02 |
| `AGENTS.md`, `.agents/skills/` com só `name` e `description` | fonte única de instruções | D-15 |

## Versionamento

- Tag semver no formato `vMAJOR.MINOR.PATCH`. Consumidores fixam a tag.
- Mudança incompatível (campo obrigatório novo, campo removido, limite mais estreito, valor de enum removido) é major (D-01).
- Campo opcional novo ou valor de enum novo é minor. Correção de descrição ou exemplo é patch.
- Enquanto a versão for 0.x, minor pode quebrar; `versions.schema` aceita só `0.1.x` nesta linha.
- Toda mudança entra no `CHANGELOG.md`.
