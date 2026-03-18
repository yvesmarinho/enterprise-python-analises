---
description: Executa o protocolo de início de sessão pela PRIMEIRA VEZ no projeto. Inicializa estrutura de sessão, carrega regras Copilot, cria arquivos base de documentação, protege credenciais e cria branch Git.
---

## Ação: Início de Sessão — Primeira Vez

Este agente executa o protocolo completo de onboarding para a **primeira sessão** no projeto.

---

## 1. Ferramentas e MCP

- Utilizar ferramentas **Pylance** (mcp_pylance_*) para pesquisa e manuseio de arquivos Python
- Iniciar MCP e verificar disponibilidade das ferramentas

---

## 2. Carregar Regras Copilot

Ler e carregar na memória (em ordem de prioridade) todos os arquivos de regras:

1. `.copilot-strict-enforcement.md` — **AUTORIDADE MÁXIMA**
2. `.copilot-strict-rules.md` — **PRIORIDADE MÁXIMA**
3. `.copilot-rules.md` — **ALTA prioridade**

> Todos os arquivos são **incrementais** — não sobrescrever, apenas acumular contexto.

---

## 3. Gerar Arquivos Base do Projeto

### Na raiz do projeto (criar ou atualizar se não existirem)
- `README.md` — Visão geral do projeto
- `docs/INDEX.md` — Índice geral com estado atual
- `docs/TODO.md` — Lista de tarefas pendentes

### Na pasta de sessão `docs/sessions/YYYY-MM-DD/` (data atual)
Criar os seguintes arquivos (todos incrementais):
- `TODAY_ACTIVITIES_YYYY-MM-DD.md` — Atividades do dia
- `SESSION_REPORT_YYYY-MM-DD.md` — Relatório da sessão
- `FINAL_STATUS_YYYY-MM-DD.md` — Status final do dia

---

## 4. Segurança — Proteger Credenciais

1. Varrer **todo** o projeto em busca de arquivos com credenciais ou conteúdo sensível:
   - Padrões: passwords, tokens, API keys, connection strings, `.env`, `config*.json`, `secret*`
2. Mover arquivos encontrados para a pasta `.secrets/`
3. Verificar se `.secrets/` está no `.gitignore` — adicionar se necessário
4. **NUNCA** versionar arquivos movidos para `.secrets/`

---

## 5. Organizar Raiz do Projeto

- Inspecionar a raiz do projeto
- Mover arquivos que não pertencem à raiz para as pastas corretas:
  - Scripts → `scripts/`
  - Documentação → `docs/`
  - Relatórios → `reports/`
  - Dados → `data/`
  - Temporários → `tmp/` (ou deletar se desnecessários)
- **Arquivos permitidos na raiz**: `README.md`, `main.py`, `pyproject.toml`, `migration_plan.json`, `.copilot-*.md`, `.gitignore`

---

## 6. Criar Branch Git

1. Verificar branch atual com `git branch --show-current`
2. Criar nova branch com o padrão: `session/YYYY-MM-DD-descricao-breve`
3. Fazer checkout na nova branch
4. Confirmar criação com `git status`

---

## 7. Validação Final

Confirmar que todos os itens abaixo foram executados:

- [ ] Ferramentas Pylance disponíveis
- [ ] Regras Copilot carregadas (3 arquivos)
- [ ] `README.md`, `docs/INDEX.md`, `docs/TODO.md` existem
- [ ] Pasta `docs/sessions/YYYY-MM-DD/` criada
- [ ] Arquivos de sessão criados (TODAY_ACTIVITIES, SESSION_REPORT, FINAL_STATUS)
- [ ] Varredura de credenciais executada
- [ ] `.secrets/` no `.gitignore`
- [ ] Raiz do projeto organizada
- [ ] Branch `session/YYYY-MM-DD-*` criada

---

## Notas

- Todos os arquivos de documentação são **incrementais** — nunca sobrescrever conteúdo anterior
- Usar formato `YYYY-MM-DD` para datas (data atual: use a data do sistema)
- Relatório final deve incluir o que foi feito, estado do projeto e próximos passos
