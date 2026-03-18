---
description: Executa o protocolo de início de sessão padrão. Carrega regras Copilot, recupera contexto da sessão anterior (MCP + arquivos de sessão), protege credenciais e organiza a raiz do projeto.
---

## Ação: Início de Sessão

Este agente executa o protocolo de **recuperação de contexto e inicialização** para sessões recorrentes.

---

## 1. Ferramentas e MCP

- Utilizar ferramentas **Pylance** (mcp_pylance_*) para pesquisa e manuseio de arquivos Python
- Iniciar MCP e verificar disponibilidade das ferramentas

---

## 2. Carregar Regras Copilot

Ler e carregar na memória (em ordem) todos os arquivos de regras:

1. `.copilot-strict-enforcement.md` — **AUTORIDADE MÁXIMA**
2. `.copilot-strict-rules.md` — **PRIORIDADE MÁXIMA**
3. `.copilot-rules.md` — **ALTA prioridade**

> Todos os arquivos são **incrementais** — não sobrescrever, apenas acumular contexto.

---

## 3. Recuperar Contexto da Sessão Anterior

### 3.1 Ler arquivos principais do projeto
- `docs/INDEX.md` — Estado geral e contexto do projeto
- `docs/TODO.md` — Tarefas pendentes e em andamento
- `docs/TODAY_ACTIVITIES.md` — Última atividade registrada (se existir)

### 3.2 Recuperar última sessão
1. Listar pasta `docs/sessions/` e identificar a data mais recente
2. Ler os arquivos da sessão mais recente:
   - `SESSION_RECOVERY_YYYY-MM-DD.md`
   - `TODAY_ACTIVITIES_YYYY-MM-DD.md`
   - `FINAL_STATUS_YYYY-MM-DD.md`
   - `SESSION_REPORT_YYYY-MM-DD.md`

### 3.3 Recuperar dados da memória MCP
- Consultar memória de repositório em `/memories/repo/`
- Consolidar: estado atual, tarefas pendentes, blockers conhecidos

---

## 4. Criar Nova Sessão

Criar pasta e arquivos para a sessão de hoje `docs/sessions/YYYY-MM-DD/`:
- `SESSION_RECOVERY_YYYY-MM-DD.md` — contexto recuperado + estado inicial
- `TODAY_ACTIVITIES_YYYY-MM-DD.md` — iniciar em branco, atualizar durante o dia

No arquivo `SESSION_RECOVERY_YYYY-MM-DD.md` documentar:
- O que foi recuperado da sessão anterior
- Estado atual do projeto
- Tarefas em aberto
- Próximos passos planejados

---

## 5. Segurança — Proteger Credenciais

1. Varrer o projeto em busca de arquivos com credenciais ou conteúdo sensível:
   - Padrões: passwords, tokens, API keys, connection strings, `.env`, `config*.json`, `secret*`
2. Mover arquivos encontrados para `.secrets/`
3. Confirmar que `.secrets/` está no `.gitignore`

---

## 6. Organizar Raiz do Projeto

- Inspecionar a raiz e mover arquivos para as pastas corretas:
  - Scripts → `scripts/`
  - Documentação → `docs/`
  - Relatórios → `reports/`
  - Dados → `data/`
- **Arquivos permitidos na raiz**: `README.md`, `main.py`, `pyproject.toml`, `migration_plan.json`, `.copilot-*.md`, `.gitignore`

---

## 7. Validação Final

Confirmar que todos os itens abaixo foram executados:

- [ ] Ferramentas Pylance disponíveis
- [ ] Regras Copilot carregadas (3 arquivos)
- [ ] Contexto da sessão anterior recuperado
- [ ] `docs/INDEX.md` e `docs/TODO.md` lidos
- [ ] Pasta `docs/sessions/YYYY-MM-DD/` criada
- [ ] `SESSION_RECOVERY_YYYY-MM-DD.md` criado com contexto resumido
- [ ] `TODAY_ACTIVITIES_YYYY-MM-DD.md` criado
- [ ] Varredura de credenciais executada
- [ ] `.secrets/` no `.gitignore`
- [ ] Raiz do projeto organizada

---

## Notas

- Todos os arquivos de documentação são **incrementais** — nunca sobrescrever sessões anteriores
- Usar formato `YYYY-MM-DD` para datas (data atual: use a data do sistema)
- Após esta ação, o agente deve reportar um resumo do contexto recuperado
