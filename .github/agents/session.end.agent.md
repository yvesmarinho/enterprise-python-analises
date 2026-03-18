---
description: Executa o protocolo de encerramento de sessão. Atualiza regras Copilot, gera/atualiza documentação da sessão (TODAY_ACTIVITIES, SESSION_REPORT, FINAL_STATUS), atualiza README/INDEX/TODO, protege credenciais, organiza a raiz e faz push para o repositório Git.
---

## Ação: Término de Sessão

Este agente executa o protocolo completo de **encerramento e documentação** da sessão de trabalho.

---

## 1. Ferramentas e MCP

- Utilizar ferramentas **Pylance** (mcp_pylance_*) para pesquisa e manuseio de arquivos Python
- Confirmar disponibilidade das ferramentas antes de prosseguir

---

## 2. Atualizar Regras Copilot (se necessário)

Revisar e atualizar, **incrementalmente**, se houver novas descobertas ou padrões identificados durante a sessão:

1. `.copilot-strict-rules.md`
2. `.copilot-strict-enforcement.md`
3. `.copilot-rules.md`

> **Regra**: Apenas adicionar novas entradas — nunca remover ou sobrescrever regras existentes.

---

## 3. Atualizar Documentação da Sessão

Na pasta `docs/sessions/YYYY-MM-DD/` (data de hoje):

### 3.1 `TODAY_ACTIVITIES_YYYY-MM-DD.md` (incremental)
Atualizar com todas as atividades realizadas hoje:
- Tarefas concluídas
- Decisões técnicas tomadas
- Problemas encontrados e soluções
- Comandos executados relevantes
- Arquivos criados/modificados

### 3.2 `SESSION_REPORT_YYYY-MM-DD.md` (incremental)
Atualizar com relatório detalhado da sessão:
- Resumo executivo
- Objetivos da sessão e status (concluído/parcial/pendente)
- Detalhamento técnico das atividades
- Obstáculos e resoluções
- Métricas (se aplicável): arquivos modificados, scripts criados, etc.
- Dependências criadas ou resolvidas

### 3.3 `FINAL_STATUS_YYYY-MM-DD.md` (incremental)
Atualizar com o estado final do projeto ao encerrar:
- Estado geral do projeto
- Tarefas concluídas hoje
- Tarefas em andamento (com % progresso)
- Tarefas pendentes / backlog
- Blockers ativos
- Próximos passos recomendados para a próxima sessão

---

## 4. Atualizar Arquivos Principais do Projeto

### `README.md` (incremental — apenas se houver mudanças relevantes)
- Atualizar seção de estado/status se o projeto evoluiu
- Adicionar novas funcionalidades documentadas
- Não remover conteúdo histórico

### `docs/INDEX.md` (incremental)
- Atualizar data de última modificação
- Atualizar estado atual do projeto
- Adicionar referência à sessão de hoje

### `docs/TODO.md` (incremental)
- Marcar tarefas concluídas hoje como `[x]`
- Adicionar novas tarefas identificadas
- Reorganizar prioridades se necessário
- Atualizar data de última revisão

---

## 5. Segurança — Verificação Final de Credenciais

1. Executar varredura final em busca de credenciais ou dados sensíveis expostos
2. Mover qualquer arquivo sensível encontrado para `.secrets/`
3. Confirmar que `.secrets/` está no `.gitignore`
4. Verificar que nenhum arquivo em `.secrets/` está no staging do Git

---

## 6. Organizar Arquivos do Projeto

- Inspecionar toda a estrutura de pastas
- Mover arquivos que estejam na raiz sem justificativa para as pastas corretas:
  - Scripts → `scripts/`
  - Documentação → `docs/`
  - Relatórios → `reports/`
  - Dados → `data/`
  - Temporários → `tmp/`
- **Arquivos permitidos na raiz**: `README.md`, `main.py`, `pyproject.toml`, `migration_plan.json`, `.copilot-*.md`, `.gitignore`

---

## 7. Atualizar Repositório Git

1. Verificar status com `git status`
2. Verificar branch atual com `git branch --show-current`
3. Adicionar arquivos ao staging: `git add -A`
4. Revisar o que será commitado: `git diff --cached --stat`
5. Criar commit descritivo:
   ```
   git commit -m "session(YYYY-MM-DD): <resumo das atividades principais>"
   ```
6. Push para o repositório remoto:
   ```
   git push origin <branch-atual>
   ```
7. Confirmar push bem-sucedido

> **⛔ NUNCA** fazer commit de arquivos em `.secrets/`
> **⚠️ SEMPRE** verificar `git status` antes do commit

---

## 8. Validação Final de Encerramento

Confirmar que todos os itens abaixo foram executados:

- [ ] Regras Copilot revisadas e atualizadas (se necessário)
- [ ] `TODAY_ACTIVITIES_YYYY-MM-DD.md` atualizado
- [ ] `SESSION_REPORT_YYYY-MM-DD.md` criado/atualizado com detalhes
- [ ] `FINAL_STATUS_YYYY-MM-DD.md` criado/atualizado com estado do projeto
- [ ] `docs/INDEX.md` atualizado
- [ ] `docs/TODO.md` atualizado
- [ ] `README.md` atualizado (se necessário)
- [ ] Varredura de credenciais executada
- [ ] `.secrets/` no `.gitignore` confirmado
- [ ] Raiz do projeto organizada
- [ ] Git commit criado
- [ ] Git push executado com sucesso

---

## Notas

- Todos os arquivos são **incrementais** — nunca sobrescrever conteúdo de sessões anteriores
- Usar formato `YYYY-MM-DD` para datas (data atual: use a data do sistema)
- O `SESSION_REPORT` deve ser suficientemente detalhado para recuperar o contexto na próxima sessão sem precisar de memória adicional
- Mensagem de commit deve ser clara e descritiva no formato convencional
