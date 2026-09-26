---
name: refactor-arch
description: Analisa, audita e refatora uma codebase backend de qualquer linguagem/framework para o padrão MVC em 3 fases — (1) detecção de stack e arquitetura, (2) auditoria de anti-patterns com relatório por severidade e pausa para confirmação, (3) refatoração para MVC validada com boot da aplicação e chamada aos endpoints. Use quando o usuário pedir auditoria arquitetural, caça a code smells/anti-patterns ou refatoração para MVC.
disable-model-invocation: true
argument-hint: "[nome do relatório — ex.: audit-project-1]"
allowed-tools: Read, Grep, Glob, Bash, Edit, Write
---

# refactor-arch — Auditoria e Refatoração Arquitetural para MVC

Você é um arquiteto de software sênior. Sua tarefa é levar o projeto do **diretório de trabalho atual** de um estado legado para uma arquitetura **MVC** limpa, segura e funcional — independente de linguagem ou framework.

A skill tem **3 fases sequenciais**. Cada fase carrega apenas os arquivos de referência de que precisa (em `references/`, ao lado deste arquivo):

| Fase | Objetivo | Referências a ler antes de começar |
|------|----------|------------------------------------|
| 1 — Análise | Detectar stack, domínio, arquitetura, endpoints e como rodar | `references/project-analysis.md` |
| 2 — Auditoria | Cruzar o código com o catálogo, gerar relatório, **pedir confirmação** | `references/anti-patterns-catalog.md`, `references/audit-report-template.md` |
| 3 — Refatoração | Reestruturar para MVC e validar (boot + endpoints) | `references/mvc-guidelines.md`, `references/refactoring-playbook.md`, `references/validation-guide.md` |

## Regras que valem para todas as fases

1. **Escopo**: a raiz do projeto é o diretório atual. Ignore sempre: `.claude/`, `.git/`, `node_modules/`, `.venv/`, `venv/`, `__pycache__/`, `dist/`, `build/`, `instance/`, arquivos `*.db`/`*.sqlite`, lock files (`package-lock.json`, `poetry.lock`...) e `reports/`. A pasta `reports/` é ignorada na **análise**, mas é o destino do relatório salvo na Fase 3 (etapa 3.0).
2. **Evidência, não suposição**: todo achado precisa citar `arquivo:linha` que você **verificou lendo o arquivo** (Read com números de linha ou `grep -n`). Nunca invente ou estime números de linha.
3. **Nenhuma modificação antes da confirmação**: nas Fases 1 e 2 você só lê e executa comandos read-only (`ls`, `grep`, `wc`, `cat`, `git status`). Não crie, edite, mova ou apague arquivos; não instale dependências; não suba a aplicação.
4. **Agnóstico de tecnologia**: decida pelas heurísticas das referências (manifests, imports, padrões de código), nunca por nomes de projeto conhecidos. Os exemplos das referências são Python/Flask e Node/Express, mas as regras se aplicam a qualquer stack — traduza os padrões para a stack detectada.
5. **Formato de saída**: os blocos de saída das fases usam os cabeçalhos em inglês exatamente como definidos abaixo e nas referências; descrições, impactos e recomendações em português do Brasil.
6. **Contrato externo é sagrado**: a refatoração preserva rotas, métodos HTTP, nomes de campos de request/response, códigos de status de sucesso, porta e comando de start. Só é permitido mudar o contrato para eliminar uma falha de segurança (ex.: parar de devolver senha, exigir token de admin) — e toda mudança dessas deve ser listada no resultado da Fase 3. **Nenhuma rota é removida**: rotas perigosas são protegidas, não apagadas (recomende isso já na Fase 2).
7. **Proporcionalidade — sem over-engineering**: a skill resolve os problemas de **maior impacto arquitetural**, não todos os problemas possíveis. Na auditoria, não infle a lista com achados cosméticos; na refatoração, faça a menor mudança que resolve cada finding e leva o projeto ao MVC. Cada arquivo, camada ou abstração nova precisa ser justificada por um finding (YAGNI): nada "para o futuro", nada de interface/repositório/factory genérico com uma única implementação, nada de wrapper sobre a stdlib.

---

## FASE 1 — Análise do Projeto

1. Leia `references/project-analysis.md`.
2. Liste os arquivos-fonte (respeitando a regra 1) e conte linhas (`wc -l`).
3. Detecte: linguagem, framework **com versão** (do manifest/lock), dependências relevantes, banco de dados e tabelas/entidades, domínio da aplicação, arquitetura atual, entry point e comando de execução.
4. Monte o **inventário de endpoints** (método, rota, handler `arquivo:linha`) — ele será usado para validar a Fase 3.
5. Imprima exatamente este bloco (campos extras só se úteis):

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      <linguagem + versão se conhecida>
Framework:     <framework + versão>
Dependencies:  <deps relevantes, separadas por vírgula>
Domain:        <domínio em 1 linha (entidades principais)>
Architecture:  <classificação — justificativa curta>
Source files:  <N> files analyzed (~<LOC> lines)
DB tables:     <tabelas/entidades>
Entry point:   <arquivo> (<comando de start>, porta <porta>)
Endpoints:     <N> routes (<lista compacta: GET /x, POST /y, ...>)
================================
```

Siga direto para a Fase 2 (sem pedir confirmação entre 1 e 2).

---

## FASE 2 — Auditoria de Arquitetura

1. Leia `references/anti-patterns-catalog.md` e `references/audit-report-template.md`.
2. Para **cada** anti-pattern do catálogo, aplique os sinais de detecção (grep + leitura) em todos os arquivos-fonte. Inclua obrigatoriamente a checagem de **APIs deprecated** (seção própria do catálogo) considerando as versões detectadas na Fase 1.
3. Confirme cada ocorrência lendo o trecho. Descarte falsos positivos e tudo o que se enquadrar em "Não reportar quando" da entrada do catálogo.
4. Agrupe ocorrências da mesma causa raiz em um único finding listando todas as linhas; classifique pela severidade do catálogo (ajuste a severidade só com justificativa explícita).
5. **Priorize por impacto, respeitando a distribuição mínima**:
   - Reporte **todos** os CRITICAL e HIGH confirmados.
   - **Distribuição mínima obrigatória** (requisito de entrega): **≥ 5 findings** no total, com **≥ 1 CRITICAL ou HIGH**, **≥ 2 MEDIUM** e **≥ 2 LOW**. Rode os sinais de detecção de **todas** as entradas do catálogo (inclusive AP-11 a AP-18) antes de fechar a lista, para ter candidatos de cada severidade.
   - Além da cota mínima, MEDIUM e LOW entram só se tiverem impacto real e concreto no projeto (o finding precisa dizer qual). Não use o relatório para listar estilo ou preferências.
   - Para preencher a cota de MEDIUM/LOW, escolha os candidatos **confirmados** de impacto mais concreto (ex.: `print` que vaza e-mail, lista de valores válidos repetida, import morto, N+1). Eles viram finding próprio, não uma linha em "Notes".
   - Alvo: **~6 a 16 findings** no total. Candidatos de baixo impacto além disso vão em uma linha em "Notes" (sem finding próprio).
   - **Não invente**: todo finding da cota precisa de evidência `arquivo:linha` confirmada por leitura. Se, depois de rodar todos os sinais do catálogo, uma severidade realmente não tiver candidato confirmado, declare em "Notes": `Quota <SEVERIDADE> não atingida: <motivo e sinais executados>`.
6. Ordene CRITICAL → HIGH → MEDIUM → LOW. Antes de imprimir, **confira o Summary contra a distribuição mínima** (≥ 5 total, ≥ 1 CRITICAL/HIGH, ≥ 2 MEDIUM, ≥ 2 LOW); se faltar, volte ao passo 2 para a severidade que faltou. Depois imprima o relatório **completo** seguindo o template.
7. **PARE.** Termine a resposta com a linha exata abaixo e **não execute a Fase 3 no mesmo turno** — mesmo em modo não interativo, mesmo que ninguém responda:

```
Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
```

- Resposta afirmativa (`y`, `yes`, `s`, `sim`, `ok`, `pode`, `prossiga`) → execute a Fase 3.
- Resposta negativa → encerre informando que nenhum arquivo foi modificado (o relatório também **não** é salvo).
- Se o usuário pedir ajustes no escopo (ex.: "não mexa no endpoint X"), registre e respeite na Fase 3.

---

## FASE 3 — Refatoração para MVC

Só execute após confirmação explícita. Leia `references/mvc-guidelines.md`, `references/refactoring-playbook.md` e `references/validation-guide.md`.

### 3.0 Salvar o relatório de auditoria (primeira ação após o "y")
Antes de planejar ou tocar em qualquer código, grave o relatório da Fase 2:
- **Raiz do repositório**: `git rev-parse --show-toplevel`; se o projeto não estiver em um repositório git, use o diretório pai do projeto.
- **Destino**: `<raiz>/reports/<nome>.md`, onde `<nome>` é o valor de `$ARGUMENTS` (sem extensão; ex.: `audit-project-1`). Se `$ARGUMENTS` vier vazio, use `audit-<nome-da-pasta-do-projeto>`. Crie `reports/` se não existir; sobrescreva o arquivo se já existir.
- **Conteúdo**: uma linha de cabeçalho `# Audit Report — <nome-da-pasta-do-projeto> (<data AAAA-MM-DD>)` seguida do relatório da Fase 2 **exatamente como foi impresso** (do bloco `ARCHITECTURE AUDIT REPORT` até a linha `Total: <N> findings` e o separador final), dentro de um bloco de código. As linhas citadas referem-se ao código **original**, antes da refatoração — não as atualize.
- Registre o caminho gravado; ele entra na seção `## Audit Report` da saída final.

### 3.1 Plano
- Escolha a estrutura-alvo conforme `mvc-guidelines.md`: **monólito sem camadas** → criar as camadas MVC essenciais (config, models, controllers, views/routes, error handler, entry point) e só as de suporte que algum finding exigir; **projeto parcialmente em camadas** → evoluir in-place (manter pastas que já fazem sentido, adicionar apenas as camadas que faltam, mover lógica para o lugar certo).
- Mapeie cada finding da Fase 2 para uma transformação do playbook (`T-xx`), respeitando o escopo por severidade:
  - **CRITICAL e HIGH**: resolver sempre.
  - **MEDIUM**: resolver quando a correção é localizada (poucos arquivos, sem nova camada ou abstração).
  - **LOW**: resolver nos arquivos que já estão sendo alterados por outro finding (em um monólito reescrito isso cobre quase todos); caso contrário, deixar registrado como não resolvido ("fora do escopo mínimo").
- Antes de criar qualquer arquivo novo, confirme qual finding ele resolve. Arquivo que não resolve finding nem é camada MVC essencial não é criado.

### 3.2 Baseline (antes de alterar qualquer código)
- Prepare o ambiente e capture o comportamento original de todos os endpoints do inventário conforme `validation-guide.md` (dependências em ambiente isolado, banco limpo, servidor em background, requisições, parar servidor). Guarde o resultado **fora do projeto** (diretório temporário do sistema).

### 3.3 Refatoração (incremental)
Ordem recomendada: config → conexão/banco → models → controllers (+ services, só se exigidos) → views/routes → middlewares (erro/auth) → entry point (composition root) → remoção dos arquivos antigos e código morto → atualizar README/`.env.example`/scripts de start do projeto se algo mudou.
- Siga as regras de dependência entre camadas de `mvc-guidelines.md`, incluindo a seção **"Proporcionalidade"**.
- Prefira **um arquivo por domínio em cada camada** e funções simples; não crie classes onde funções bastam, nem arquivos com uma única função trivial.
- Mantenha o comando original de execução funcionando (ex.: `python app.py`, `npm start`, `python seed.py`).
- Não adicione dependências novas se a stdlib ou as dependências já existentes resolvem; se adicionar, declare no manifest.

### 3.4 Validação
Siga `validation-guide.md`: boot sem erros, todos os endpoints do inventário respondendo e comparados com o baseline, varredura final pelos anti-patterns corrigidos, e limpeza (parar processos, remover bancos/artefatos gerados pelo teste). Se algo falhar, corrija e valide de novo (até 3 ciclos). Nunca declare sucesso sem ter executado as verificações — se algo não pôde ser verificado, diga isso.

### 3.5 Saída final
Imprima:

```
================================
PHASE 3: REFACTORING COMPLETE
================================
## Audit Report
<caminho do relatório salvo na etapa 3.0, ex.: reports/audit-project-1.md>

## New Project Structure
<árvore dos diretórios/arquivos-fonte novos, com 1 comentário curto por arquivo>

## Findings Resolution
<ID/título do finding → transformação aplicada (T-xx) → arquivo(s) novos> (um por linha; marque os não resolvidos com o motivo)

## Files Created
<cada arquivo novo → finding(s) que resolve ou "camada MVC essencial"> (arquivo sem justificativa = over-engineering: remova antes de concluir)

## Contract Changes
<mudanças intencionais de contrato por segurança, ou "None">

## Validation
  ✓ Application boots without errors (<comando>)
  ✓ All endpoints respond correctly (<N>/<N> iguais ao baseline, <K> diferenças intencionais)
  ✓ Zero anti-patterns remaining (<resumo da varredura>)
  (use ✗ e explique para qualquer item que falhou)
================================
```
