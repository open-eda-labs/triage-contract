# Changelog

Formato baseado em Keep a Changelog; versões seguem semver.

## [0.1.0] - não lançada

### Adicionado

- `schemas/alert-event.yaml`: envelope CloudEvents 1.0 com `traceparent` e `dataref`; tipos `alert.firing`, `alert.resolved` e `vulnerability.detected`.
- `schemas/recommendation.yaml`: até 3 hipóteses com evidência estruturada, `not_enough_evidence`, ação sugerida, status (`recommended`, `pr_opened`, `no_change`, `failed`) e bloco `fix` do vuln fixer.
- Exemplos válidos e inválidos para os dois schemas e `tests/test_schemas.py`.
- `AGENTS.md` e skills `triage-recommendation` e `vuln-fix-maven`.
- CI com lint (workflow reutilizável da org) e pytest, com `timeout-minutes: 5` por job.
- Schemas e exemplos passam a ser YAML.
- README: seções "O que o schema não garante" e "Escolhas [P] a confirmar".

### Endurecido após revisão independente

- Todos os patterns fecham com `$(?!\n)`: `re.search` aceitava `\n` final antes de `$`. Teste anexa `\n` a cada string dos exemplos válidos.
- `safeText` barra também `\u000b`, `\u000c`, `\u0085`, `\u2028`, `\u2029`, `//` (URL relativa a protocolo), `tel:` e domínio seguido de caminho (`.tld/`). Domínio nu sem caminho fica com o publicador (texto puro, sem mrkdwn e sem unfurl).
- `identifier` e `eventId` sem `@` e `+` (e-mail é D2). Nenhum uso legítimo dependia deles; versões Maven com `+` continuam no pattern próprio de versão.
- `query_id` com pattern próprio, sem `..` e sem `@`.
- `rule_name` restrito a rótulo de até 64 caracteres, sem `:` nem `/`; faixa de letras acentuadas `À-ÖØ-öø-ÿ`, que exclui os sinais de multiplicação e divisão.
- `dataref` só com esquemas `s3` e `https`, sem porta e sem segmentos `.` ou `..`.
- `failure_reason` restrito por `kind`; `no_change` proíbe `patch_sha256` e `pr_number`.
- Teste garante que cada valor de `type` fecha `data` com `$ref` para um objeto fechado.
- Skill `vuln-fix-maven` lista o que o workflow preenche.
