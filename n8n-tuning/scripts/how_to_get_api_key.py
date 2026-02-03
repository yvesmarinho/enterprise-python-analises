"""
Guia para Obter API Key do N8N
"""

print("""
╔═══════════════════════════════════════════════════════════════╗
║           🔑 COMO OBTER A API KEY DO N8N                      ║
╚═══════════════════════════════════════════════════════════════╝

📍 URL do seu N8N: https://workflow.vya.digital/

Para obter a API Key do N8N, você precisa:

1️⃣  Acessar o N8N:
   → Abra: https://workflow.vya.digital/
   → Faça login com suas credenciais

2️⃣  Ir para Settings (Configurações):
   → Clique no seu avatar/nome no canto superior direito
   → Selecione "Settings" ou "Configurações"

3️⃣  Acessar API Keys:
   → No menu lateral, procure por "API"
   → Clique em "API Keys" ou "Chaves de API"

4️⃣  Criar Nova API Key:
   → Clique em "Create API Key" ou "Criar Nova Chave"
   → Dê um nome: "n8n-tuning-analysis"
   → Copie a chave gerada (ela aparece apenas uma vez!)

5️⃣  Atualizar o arquivo de credenciais:
   → Edite: n8n-tuning/.secrets/credentials.json
   → Substitua a "api_key" pela chave do N8N

╔═══════════════════════════════════════════════════════════════╗
║                    ⚠️  IMPORTANTE                              ║
╚═══════════════════════════════════════════════════════════════╝

• A chave da OpenAI (sk-proj-...) NÃO funciona para o N8N
• A API Key do N8N tem formato diferente
• Você pode criar múltiplas keys no N8N
• Guarde a key em lugar seguro após gerar

╔═══════════════════════════════════════════════════════════════╗
║              🔄 ALTERNATIVA: Usar Credenciais                  ║
╚═══════════════════════════════════════════════════════════════╝

Se você não conseguir gerar uma API Key, podemos:

1. Usar o acesso SSH ao servidor (wf001.vya.digital)
2. Acessar o PostgreSQL diretamente
3. Fazer consultas no banco de dados do N8N

Você já tem essas credenciais configuradas:
   • SSH: archaris@wf001.vya.digital:5010
   • PostgreSQL: n8n_tuning_read@wfdb02.vya.digital

Quer tentar a abordagem alternativa?
""")
