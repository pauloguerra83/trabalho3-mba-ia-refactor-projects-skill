# Referência — Template do Relatório de Auditoria (Fase 2)

O relatório é impresso na íntegra no terminal ao final da Fase 2 (ele é salvo depois como `audit-*.md`, então precisa ser Markdown válido e autocontido).

## Regras

1. **Ordem**: CRITICAL → HIGH → MEDIUM → LOW. Dentro da mesma severidade, pela ordem do catálogo (AP-xx).
2. **Localização exata**: `File:` traz `caminho/relativo.ext:linha` ou `:inicio-fim`. Várias ocorrências da mesma causa → várias localizações separadas por vírgula (`models.py:28, models.py:47-50`). Caminhos relativos à raiz do projeto.
3. **Um finding por causa raiz**: não repita o mesmo anti-pattern em N findings; agrupe as linhas. Anti-patterns diferentes no mesmo trecho viram findings diferentes.
4. **Foco em impacto**: todos os CRITICAL/HIGH confirmados; MEDIUM/LOW só com impacto concreto descrito em `Impact`. Alvo de ~5 a 12 findings; candidatos de baixo impacto excedentes vão em uma linha de "Notes" ("Outros pontos menores, fora do escopo: ..."), sem finding próprio.
5. **Summary bate com a lista**: as contagens por severidade e o `Total` precisam ser exatamente o número de findings listados.
6. **Deprecated APIs**: sempre presente — como finding(s) AP-15 ou, se nada for encontrado, a linha `Deprecated APIs: none detected` na seção "Notes".
7. **Recomendação acionável**: cite a transformação do playbook (`T-xx`) e o destino na arquitetura MVC (ex.: "mover para `controllers/pedido_controller.py`").
8. Descrições em português; cite o valor/trecho problemático entre crases quando curto (nunca imprima segredos completos de produção — mascare após 4 caracteres, ex.: `pk_l****`).
9. **Nenhum arquivo é modificado** ao produzir o relatório.

## Template

```
================================
ARCHITECTURE AUDIT REPORT
================================
Project: <nome da pasta do projeto>
Stack:   <Linguagem> + <Framework versão>
Files:   <N> analyzed | ~<LOC> lines of code

## Summary
CRITICAL: <n> | HIGH: <n> | MEDIUM: <n> | LOW: <n>

| # | Severity | Anti-pattern | Location |
|---|----------|--------------|----------|
| 1 | CRITICAL | <nome> | <arquivo:linha> |
| … | …        | …      | …               |

## Findings

### [CRITICAL] <Nome do anti-pattern> (AP-xx)
File: <arquivo:linha[, arquivo:linha-linha ...]>
Description: <o que acontece, com o trecho/valor concreto>
Impact: <consequência técnica/negócio: segurança, testabilidade, consistência, performance>
Recommendation: <correção concreta> (T-xx)

### [HIGH] ...

### [MEDIUM] ...

### [LOW] ...

## Notes
- Deprecated APIs: <resumo ou "none detected">
- <observações de arquitetura geral: camadas existentes, pontos positivos a preservar>

================================
Total: <N> findings
================================

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
```

## Exemplo de finding bem escrito

```
### [CRITICAL] SQL Injection (AP-01)
File: models.py:28, models.py:47-50, models.py:109-111, models.py:289-299
Description: Queries montadas por concatenação de strings com dados do request (ex.: `"SELECT * FROM usuarios WHERE email = '" + email + "'"`). No login, o payload `' OR '1'='1` autentica sem senha.
Impact: Leitura/alteração arbitrária do banco e bypass de autenticação por qualquer cliente anônimo.
Recommendation: Usar queries parametrizadas (`?`) em todas as funções de acesso a dados, concentradas nos models (T-01).
```

## Exemplo de finding ruim (não faça)

```
### [HIGH] Código ruim
File: models.py
Description: O código tem problemas.
```
(sem linha, sem anti-pattern identificado, sem impacto nem recomendação)
