# triage-contract

Contrato versionado entre as peças do laboratório open-eda-labs: o evento que entra, a recomendação que sai e as instruções para agentes. Intake-adapter, agent-workflows, triage-eval, publicação Slack/Teams e vuln fixer dependem só deste repositório, nunca uns dos outros (D-01, D-27).

Plano de origem: [Plano Mestre](https://github.com/open-eda-labs/open-eda-labs.github.io/blob/main/docs/PLANO_MESTRE.md).

## Layout

| Caminho | Conteúdo |
| --- | --- |
| `schemas/alert-event.yaml` | Evento de entrada: envelope CloudEvents 1.0 com `data` próprio (alerta ou vulnerabilidade) |
| `schemas/recommendation.yaml` | Saída da triagem read-only e do vuln fixer |
| `examples/alert-event.yaml`, `examples/recommendation.yaml` | Casos sintéticos (`name`, `valid`, `rule`, `doc`); os inválidos documentam o que o schema barra |
| `tests/test_schemas.py` | Valida schemas contra o metaschema e todos os exemplos |
| `requirements-dev.txt` | Dependências pinadas dos testes |
| `AGENTS.md` | Regras para qualquer harness de agente (D-15) |
| `.agents/skills/` | Skills `triage-recommendation` e `vuln-fix-maven` |
| `CHANGELOG.md` | Histórico de versões |

## Validar localmente

Requer Python 3.12. Crie o venv fora do repositório:

```sh
python3 -m venv ~/.venvs/triage-contract
~/.venvs/triage-contract/bin/pip install -r requirements-dev.txt
~/.venvs/triage-contract/bin/pytest -q
```

O lint é o workflow reutilizável da org (repositório `.github`), chamado pelo CI.

`rfc3339-validator` é necessário: sem ele o `format: date-time` é ignorado em silêncio, e há teste que falha nesse caso.

## Tipos de evento

| `type` | `source` | `data` |
| --- | --- | --- |
| `io.github.open-eda-labs.alert.firing` | `/grafana/<instância>`, `/azure-monitor/<instância>`, `/datadog/<instância>` | alerta |
| `io.github.open-eda-labs.alert.resolved` | idem | alerta, com `ends_at` |
| `io.github.open-eda-labs.vulnerability.detected` | `/osv-scanner/<instância>`, `/dependabot/<instância>` | vulnerabilidade Maven |

Duplicata é o mesmo par `source` + `id`. No achado do OSV-Scanner, `id` = `<advisory>:<owner/repo>:<groupId:artifactId>`.

`dataref` aceita só `s3://` e `https://`, sem porta, credencial, query, fragmento nem segmentos `.` ou `..`. O consumidor só resolve hosts da sua allowlist; o schema não sabe quais são.

## Campo e decisão

| Campo | Regra | Decisão |
| --- | --- | --- |
| envelope, `specversion` 1.0 | CloudEvents estruturado, sem extensões além das listadas | D-10 |
| `source` + `id` | definem duplicata | D-10 |
| `source` por emissor | um adapter por fonte, todos em CloudEvents | D-36, D-30 |
| `traceparent` | obrigatório; seu trace-id é o `trace_id` da saída | D-12 |
| `dataref` | payload completo fora do evento, esquemas fixos, sem query nem credencial | D-10, D-22 |
| `data` fechado e curto | só os campos listados, pensados para D0/D1; o único texto do emissor é `rule_name`, rótulo de até 64 caracteres sem `:` nem `/` | D-22, D-42, D-43 |
| `data` de vulnerabilidade | advisory, repositório, pacote Maven, versões | D-29, D-30 |
| `hypotheses` (até 3), `confidence`, `evidence` | `collector` + `query_id` referenciam a consulta fixa; `value` é resumo curto em texto | D-06, D-11, G-P1 |
| `not_enough_evidence` | true exige zero hipóteses | D-11, G-P1 |
| `status` | `pr_opened`, `no_change`, `failed`; `recommended` para read-only | D-11, D-02 |
| `fix` | nível N1/N2, hash do patch, número do PR, CI, re-scan | D-28, D-31, P5 |
| `versions` | schema, prompt e nome lógico do modelo | D-09, P1 |
| `additionalProperties: false`, `maxLength`, texto sem URL e sem markdown de link | guardrail por arquitetura; links montados pelo workflow | D-13, R-01, R-02 |
| `AGENTS.md`, `.agents/skills/` com só `name` e `description` | fonte única de instruções | D-15 |

## O que o schema não garante

O schema limita forma e tamanho. Estas verificações são do workflow e do publicador (passo sem modelo), antes de qualquer publicação:

- **Texto puro.** O publicador publica texto sem mrkdwn, sem HTML e sem unfurl de link. O schema barra `//`, esquemas conhecidos, `www.` e domínio seguido de caminho (`.tld/`), mas não barra domínio nu (`exemplo.com`) sozinho, para não rejeitar causas como `java.lang.OutOfMemoryError`.
- **Detector de D-43.** Roda sobre todo texto (`cause`, `value`, `text`) antes de publicar: mascara D2 e bloqueia D3.
- **Registro de consultas.** O workflow confere cada `collector` + `query_id` contra o registro de consultas fixas; referência desconhecida reprova a saída.
- **Coerência semântica.** `fix.ci_status` compatível com `status`, hipóteses repetidas, `ends_at` posterior a `starts_at` e `rescan: clean` quando `pr_opened` não são verificados pelo schema.

## Versionamento

- Tag semver no formato `vMAJOR.MINOR.PATCH`. Consumidores fixam a tag.
- Mudança incompatível (campo obrigatório novo, campo removido, limite mais estreito, valor de enum removido) é major (D-01).
- Campo opcional novo ou valor de enum novo é minor. Correção de descrição ou exemplo é patch.
- Enquanto a versão for 0.x, minor pode quebrar; `versions.schema` aceita só `0.1.x` nesta linha.
- Toda mudança entra no `CHANGELOG.md`.

## Escolhas [P] a confirmar

Escolhas feitas neste contrato onde o plano não decide. Valem até o dono confirmar ou trocar.

1. `$id` dos schemas em `https://open-eda-labs.github.io/triage-contract/schemas/...` (não precisa resolver).
2. Envelope fechado: só `subject`, `traceparent` e `dataref` como atributos opcionais/extensões; `traceparent`, `dataref` e `time` são obrigatórios.
3. `source` no formato `/<emissor>/<instância>`, com emissor em enum e cruzado com `type`.
4. `id` de alerta = fingerprint + início + estado, para o resolved não ser duplicata do firing.
5. `dataref` só com `s3` ou `https`, sem query, porta, credencial ou segmentos `.`/`..`.
6. Lista de campos de `data` (alerta e vulnerabilidade) e severidade normalizada em `critical`, `high`, `medium`, `low`, `info`, `unknown`.
7. `status: recommended` para a recomendação read-only; vai além da tabela do plano, que só traz `pr_opened`, `no_change` e `failed`.
8. `confidence` como enum `low`, `medium`, `high`.
9. Tipos de `suggested_action` (`investigate`, `escalate`, `rollback_change`, `scale_resource`, `restart_component`, `review_pr`, `no_action`); o plano não define enum.
10. Regras condicionais: `not_enough_evidence` exige zero hipóteses; `failed` exige `failure_reason`; `pr_opened` exige PR, hash e versão; `no_change` proíbe hash e PR; vuln_fix sem hipóteses.
11. `kind` (`triage`, `vuln_fix`), `failure_reason` (com valores por `kind`) e `fix.level` (`N1`, `N2`) vão além da tabela do plano.
12. Filtro de texto livre e o resíduo de domínio nu delegado ao publicador.
13. `versions`: `schema` em `0.1.x`, `prompt` em `nome.vN`, `model` como nome lógico, opcional só no N1.
14. Saída do N2: patch pronto devolve só `/out/patch.diff`; o passo de publicação escreve `recommendation.json` com `pr_opened`.
15. Política de versionamento: campo opcional novo ou valor de enum novo é minor.
