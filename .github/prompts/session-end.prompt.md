---
mode: agent
description: Ritual de encerramento de sessão. Execute ao finalizar o trabalho do dia.
---

# 🏁 Session End — Ritual de Encerramento de Sessão

> Execute este ritual **ao final de cada sessão** antes de sair do editor.
> Garante rastreabilidade, preserva contexto e mantém o repositório sincronizado.

---

## ▶️ Execução do Ritual

---

### Passo 1 — Consolidar Atividades do Dia

Atualizar `docs/SESSIONS/[YYYY-MM-DD]/DAILY_ACTIVITIES_[YYYY-MM-DD].md` com:

- Todas as tarefas executadas nesta sessão (concluídas e abandonadas)
- Decisões tomadas (com justificativa)
- Problemas encontrados e como foram resolvidos
- Artefatos criados ou modificados (com caminho)

**Formato recomendado para cada atividade:**
```markdown
### ✅ [IMP-XX] — [Título]

**Artefatos criados/modificados**:
| Arquivo | O que mudou |
|---------|-------------|
| `caminho/arquivo.py` | [descrição] |

**Destaques**: [pontos importantes para a próxima sessão]
```

---

### Passo 2 — Atualizar TODO.md

Em `docs/TODO.md`:

1. **Marcar concluídos**: `[ ]` → `[x]` para tudo finalizado nesta sessão
2. **Adicionar pendentes novos**: itens descobertos durante o trabalho
3. **Atualizar prioridades**: reordenar se necessário
4. **Atualizar o cabeçalho**:

```markdown
**Last Updated**: [YYYY-MM-DD] — [IMP-XX] ✅ Concluído
```

---

### Passo 3 — Criar FINAL_STATUS (se encerramento de sprint/milestone)

Se esta sessão encerrar uma fase importante, criar:
`docs/SESSIONS/[YYYY-MM-DD]/FINAL_STATUS_[YYYY-MM-DD].md`

```markdown
# 📊 Final Status — [YYYY-MM-DD]

**Branch**: [nome]
**Sessão**: [início] → [fim]

## IMPs Concluídos Esta Sessão
- ✅ IMP-XX: [descrição]

## Estado Geral dos IMPs
| IMP | Título | Status |
|-----|--------|--------|
| IMP-01 | ... | ✅ Concluído |
| IMP-02 | ... | 🔄 Em progresso |
| IMP-03 | ... | 🔵 Pendente |

## Próximas Ações (P0 para próxima sessão)
1. [ação]

## Decisões Técnicas desta Sessão
- D-XX: [decisão]

## Contexto para Recuperação
[o que a próxima sessão precisa saber para continuar sem fricção]
```

---

### Passo 4 — Verificar Qualidade do Código (se modo PROGRAMMING)

Antes de commitar código:

```bash
# Python
uv run pytest                          # testes passando?
uv run black --check src/             # formatação OK?
uv run flake8 src/                    # lint OK?
uv run mypy src/                      # types OK?

# TypeScript
npm test && npx tsc --noEmit && npm run lint

# Go
go test ./... && go vet ./... && golangci-lint run
```

Se houver falhas: corrigir antes de commitar ou documentar como `TODO` rastreado.

---

### Passo 5 — Verificar Infraestrutura (se modo INFRASTRUCTURE)

Antes de commitar IaC:

```bash
terraform fmt -recursive && terraform validate   # se Terraform
helm lint charts/*/                              # se Helm
ansible-lint playbooks/                          # se Ansible
hadolint Dockerfile                              # se Docker
```

---

### Passo 6 — Scan de Segurança Final

Último check antes do commit:

```
Padrões: *.env, .env*, *.key, *.pem, *secret*, *password*, *token*, *.log
Excluir: .git/, .secrets/
```

**Se encontrar algo**: remover do staging, adicionar ao `.gitignore`, corrigir antes de prosseguir.

Verificar também:
- Nenhum `print()` / `console.log()` de debug deixado
- Nenhuma URL de ambiente de produção hardcodada
- Nenhum token/key em variáveis que serão commitadas

---

### Passo 7 — Preparar Commit

**Regra P0**: usar arquivo de mensagem com ≥6 linhas. Nunca `git commit -m "..."`.

```bash
# Verificar o que vai ser commitado
git status
git diff --staged          # revisar mudanças staged

# Preparar mensagem de commit
cat > /tmp/git-msg.txt << 'EOF'
[tipo]: [descrição curta em inglês ou português]

[IMP-XX] [Título da implementação]

Artefatos criados/modificados:
- caminho/arquivo1.py: [o que mudou]
- caminho/arquivo2.md: [o que mudou]

Decisões: [se houver]
Pendente: [o que ficou para próxima sessão]
EOF

# Revisar a mensagem antes de commitar
cat /tmp/git-msg.txt
```

**Tipos de commit** (Conventional Commits):
| Tipo | Quando usar |
|------|-------------|
| `feat:` | Nova funcionalidade |
| `fix:` | Correção de bug |
| `docs:` | Apenas documentação |
| `refactor:` | Refatoração sem mudança de comportamento |
| `chore:` | Tarefas de manutenção (deps, config) |
| `test:` | Adição ou correção de testes |

---

### Passo 8 — Commitar e Fazer Push

```bash
# Adicionar e commitar
git add -A
git commit -F /tmp/git-msg.txt

# Verificar o commit
git log --oneline -3

# Push (D-17: git push é parte obrigatória do encerramento)
git push origin [branch]

# Confirmar push bem-sucedido
git status   # deve mostrar "Your branch is up to date with 'origin/[branch]'"
```

**Se o push falhar:**
```bash
git pull --rebase origin [branch]   # resolver conflitos se houver
git push origin [branch]
```

---

### Passo 9 — Atualizar INDEX.md (se novos arquivos foram criados)

Se novos arquivos importantes foram criados nesta sessão, atualizar `docs/INDEX.md`:

```markdown
## [Seção relevante]
- [`caminho/arquivo.ext`](../caminho/arquivo.ext) — [descrição de 1 linha]
```

---

### Passo 10 — Limpar Diretório Temporário

Remover arquivos temporários gerados durante a sessão:

```bash
# Verificar o que será removido (dry run)
./scripts/cleanup-tmp.sh --dry-run

# Limpar tmp/ (preserva tmp/README.md)
./scripts/cleanup-tmp.sh --verbose
```

**O script remove**:
- Todos os arquivos em `tmp/` exceto `README.md`
- Todos os subdiretórios em `tmp/`

**Quando NÃO limpar**:
- Se há arquivos temporários que serão usados na próxima sessão imediata
- Nesse caso, documente em `FINAL_STATUS` quais arquivos e por quê

---

## ✅ Checklist de Encerramento

### Documentação
- [ ] `DAILY_ACTIVITIES_[data].md` completo com todos os artefatos
- [ ] `docs/TODO.md` atualizado (concluídos marcados, novos adicionados)
- [ ] `FINAL_STATUS_[data].md` criado (se encerramento de fase)
- [ ] `docs/INDEX.md` atualizado (se novos arquivos criados)

### Limpeza
- [ ] `./scripts/cleanup-tmp.sh` executado (ou motivo documentado para não executar)

### Qualidade
- [ ] Testes passando (se código foi modificado)
- [ ] Lint/formatter aplicado (se código foi modificado)
- [ ] IaC validado (se infra foi modificada)
- [ ] Scan de segurança final: 🟢 LIMPO

### Git
- [ ] `git status` revisado — nada inesperado no staging
- [ ] Arquivo de mensagem preparado em `/tmp/git-msg.txt`
- [ ] `git commit -F /tmp/git-msg.txt` executado com sucesso
- [ ] `git push` executado com sucesso
- [ ] `git status` pós-push: "up to date"

---

## 🔄 Contexto para Próxima Sessão

Ao encerrar, deixar registrado em `FINAL_STATUS` ou `DAILY_ACTIVITIES`:

1. **Onde parou**: arquivo + linha se possível
2. **Próximo passo imediato**: o que fazer ao abrir na próxima sessão
3. **Decisões pendentes**: o que precisa de confirmação do usuário
4. **Riscos/bloqueios**: o que pode impedir progresso
5. **Comandos úteis**: se há setup não óbvio para retomar

---

## ⚠️ Anti-Patterns de Encerramento

| ❌ Proibido | ✅ Correto |
|------------|-----------|
| `git commit -m "wip"` | Mensagem descritiva com arquivo ≥6 linhas |
| Fechar sem fazer push | Push é obrigatório (D-17) |
| TODO.md desatualizado | Sempre atualizar antes de fechar |
| Código com testes falhando commitado | Corrigir ou documentar como known issue |
| Secrets/tokens no commit | Scan obrigatório antes de `git add` |
| "Vou lembrar o contexto" | Sempre escrever em FINAL_STATUS |

---

*Session End Prompt v1.0 | IMP-04 | 2026-03-01*
