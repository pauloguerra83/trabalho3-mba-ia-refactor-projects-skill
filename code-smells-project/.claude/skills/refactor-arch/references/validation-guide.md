# Referência — Guia de Validação (Fase 3)

Objetivo: provar, com execução real, que (1) a aplicação sobe sem erros, (2) todos os endpoints originais continuam respondendo como antes e (3) os anti-patterns corrigidos não existem mais. O mesmo roteiro é usado no **baseline** (antes de mexer no código) e **depois** da refatoração.

---

## 1. Preparar o ambiente (isolado, sem poluir o sistema)

| Stack | Comando |
|-------|---------|
| Python | Reutilize `.venv/`/`venv/` se existir; senão `python -m venv .venv`. Instale com `<venv>/bin/python -m pip install -r requirements.txt` (Windows: `<venv>/Scripts/python.exe`). |
| Node | `npm install` (ou `npm ci` se houver lock). Não use `-g`. |
| Outras | `go mod download`, `mvn -q package -DskipTests`, `bundle install`... |

Detecte o SO (`uname` / `$OS` / `process.platform`) e use o caminho de executável correto. Se o projeto precisa de seed antes do boot (README ou `seed.*`), rode-o no baseline e depois.

## 2. Estado limpo e determinístico

- Banco em arquivo: remova/renomeie o arquivo do banco **gerado em runtime** antes de cada rodada (`loja.db`, `instance/*.db`) para que baseline e pós-refatoração partam do mesmo seed. Banco em memória já é limpo a cada boot.
- Nunca apague arquivos versionados; confira com `git status`/`git ls-files` antes de remover um `.db`.
- Garanta que a porta está livre antes de subir (`netstat -ano | grep :PORT` no Windows, `lsof -i :PORT` no Unix).

## 3. Subir em background e esperar ficar pronto

```bash
# Python
.venv/Scripts/python app.py > "$TMP_DIR/server.log" 2>&1 &      # Unix: .venv/bin/python
# Node
npm start > "$TMP_DIR/server.log" 2>&1 &

for i in $(seq 1 60); do curl -s -m 2 -o /dev/null "http://localhost:$PORT/" && break; sleep 0.5; done
```
- `TMP_DIR`: diretório temporário do sistema (`mktemp -d`, `$TMPDIR`, `/tmp`), **fora do projeto**.
- Falha de boot = ler `server.log`, corrigir, repetir. Registre também `DeprecationWarning`/warnings no log (entram na varredura final).
- Rode o servidor com a configuração padrão (sem `.env`) — a app precisa subir só com os defaults de dev.

## 4. Exercitar todos os endpoints do inventário

Para cada rota da Fase 1, faça ao menos: um caso de sucesso e um caso de erro relevante (404 de id inexistente, 400 de payload inválido). Use payloads de `api.http`/README quando existirem. Ordene para respeitar dependências (criar → ler → atualizar → deletar) e deixe rotas destrutivas (reset, delete em massa) por último.

```bash
req() {  # req METHOD PATH [JSON]
  local body="${3:-}"
  if [ -n "$body" ]; then out=$(curl -s -m 15 -w $'\n%{http_code}' -X "$1" "$BASE$2" -H 'Content-Type: application/json' -d "$body")
  else out=$(curl -s -m 15 -w $'\n%{http_code}' -X "$1" "$BASE$2"); fi
  printf '%-7s %-35s -> %s | %s\n' "$1" "$2" "${out##*$'\n'}" "$(echo "${out%$'\n'*}" | tr -d '\n' | cut -c1-150)"
}
req GET /produtos
req POST /produtos '{"nome":"Teste","preco":10,"estoque":1}'
```
Salve a saída do baseline e a do pós-refatoração em arquivos no `TMP_DIR` e compare (`diff`), linha a linha:
- **Status code** deve ser igual. **Estrutura** da resposta (chaves) deve ser igual; valores voláteis (timestamps, ids gerados, hashes) podem diferir.
- Diferenças permitidas somente as intencionais de segurança (ex.: `senha` removida da resposta; `/admin/*` agora 403 sem token; injeção SQL no login agora 401). Para rotas protegidas, faça também uma chamada **com** o token de admin configurado via variável de ambiente para provar que continuam funcionando.
- Toda diferença não intencional é bug: corrija e rode de novo.

## 5. Varredura final de anti-patterns

Reexecute os greps do catálogo para cada finding que foi marcado como resolvido e confirme zero ocorrências no código novo, por exemplo:
```bash
grep -rnE "execute\([^)]*(\+|%|\.format\(|f\")" --include=*.py . --exclude-dir=.venv      # AP-01
grep -rniE "(secret|passw|api[_-]?key).{0,20}[=:] *['\"][^'\"]{6,}" . --exclude-dir={node_modules,.venv,.claude}   # AP-02
grep -rnE "hashlib\.md5|debug=True|utcnow\(|\.query\.get\(" . --exclude-dir={.venv,.claude}  # AP-03/10/15
```
**Checagem de camada (obrigatória, independente dos findings auditados)** — nenhum acesso a dados fora de models/database:
```bash
grep -rnE "execute\(|executemany\(|db\.session\.(get|execute|scalar|scalars|add|delete|query)\(|\.query\.|this\.db\.(run|get|all)\(|\b(SELECT|INSERT INTO|UPDATE|DELETE FROM|PRAGMA)\b" \
  --include=*.py --include=*.js . --exclude-dir={.venv,node_modules,.claude} | grep -E "/(controllers|routes|views|services)/"
```
Resultado esperado: **0 linhas**, exceto delimitação de transação (`db.session.commit()`/`rollback()`, `with db:`, `transaction(...)`) e menções em docstrings/comentários. Qualquer outra ocorrência → aplicar T-16 e validar de novo.

**Checagem de excesso (anti over-engineering)** — liste os arquivos-fonte criados pela refatoração e justifique cada um:
```bash
git status --porcelain | grep '^??'      # novos arquivos (ou compare com a listagem da Fase 1)
```
Para cada arquivo novo: qual finding ele resolve, ou qual camada MVC essencial ele é. Remova (e revalide) arquivos sem justificativa, com uma única função trivial ou que só repassam chamadas (wrappers). O resultado vai para a seção "Files Created" da saída da Fase 3.

Confirme também: arquivos antigos removidos, nenhum import quebrado (o boot já prova), `seed`/scripts auxiliares ainda rodam.

## 6. Encerrar e limpar

- Pare **somente** os processos que você iniciou: pelo PID (`kill $PID`) ou pela porta (Windows: `netstat -ano | grep ":PORT .*LISTENING"` → `taskkill //F //T //PID <pid>`; Unix: `kill $(lsof -ti tcp:PORT)`). Não mate processos por nome (pode derrubar processos de outras pessoas/ferramentas).
- Remova bancos e artefatos gerados pelo teste que não existiam antes (`*.db`, `__pycache__/` se criado, logs temporários).
- `git status` deve mostrar apenas as mudanças da refatoração.

## 7. Como reportar

No bloco final da Fase 3:
```
## Validation
  ✓ Application boots without errors (python app.py — 0 errors, 0 warnings)
  ✓ All endpoints respond correctly (25/25 requests; 22 idênticas ao baseline, 3 diferenças intencionais de segurança)
  ✓ Zero anti-patterns remaining (SQL concatenado: 0, segredos hardcoded: 0, print: 0, utcnow: 0)
```
Liste cada diferença intencional em "Contract Changes". Se algo não pôde ser validado (ex.: runtime ausente), marque com ✗ e explique — nunca afirme sucesso sem execução.
