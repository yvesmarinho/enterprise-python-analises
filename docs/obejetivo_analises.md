# Objetivo de 17/03/2026

## Descrição

Analisar dados armazenados no prometheus/victoria metrics objetivando encontrar
o problema de desempenho do N8N.

Principais sintomas são a lentidão na execução de processos pequenos, como coleta de dados por API.
Definição de lentidão é cada etapa do workflow usar 1 segundo ou mais para ser executado.

Coletar log de erros do N8N, que não sei se está configurado no Container Collector.

Para analises e coleta de dados não há restrição de horário.

Só está restrito ao horário das 8:00 hs às 20:30 hs qualquer execução de restart ou algo nessse sentido.

Após esse horário é possível fazer alterações nos container do N8N.

As principais conexões utilizadas pelo N8N são o Chatwoot e Whatsapp. É possivel outras conexões não documentadas nos vários fluxos de dados.

O problema não está relacionado a consumo de memória ou processamento. **Nosso foco é a lentidão enfrentada pelos fluxo de trabalho.**

## Data de incio do problema.
Foi reportado a lentidão no inicio de Janeiro/2026.

## Acessos Stack Prometheus
vide doc em `docs/Prometheus/docker-compose.yaml` e `docs/Prometheus/PROMETHEUS_SETUP.md`

## Informações sobre o coletor de dados está na pasta abaixo
O Coletor está sendo executado em dois servidores diferente.
1 - wf001 - coleta dados do N8N, latencia de rede, delay na execução de querys, etc.
2 - wf008 (VPS - Brasil) tem as mesmas coletas do wf001.

`docs/Prometheus/collector-api`

## Cenário

### Docker Host
  - host_name = wf001.vya.digital
  - host_ip = 31.220.103.208
  - host_nbr_cpu = 10
  - host_mem = 32GB
  - host_dsh = 500GB
  - host_os = Linux Debian 12
  - host_type = VPS
  - host_region = US EAST (New York)
  - ssh_type = SPA
  - ssh_script = ~/.local/bin/ssh-wf001
  - ssh_alternative = "fwknop --rc-file ~/.fwknoprc -n wf001 && sleep 3 && <command>"
  - ssh_connection = ssh key (configurado para acesso em qualquer pasta do computador)
  - ssh_user = archaris
  - user_type = sudo
  - user_information = no password user
  - docker_user = docker_user
  - docker_folder = /opt/docker_user/
  - docker_version = 28.0.2
  - docker_compose = plugin
  - N8N_host_dns = https://workflow.vya.digital
  - N8N_services_related = Rabbitrmq (para serviços relacionados, verificar nos WF) e Redis (como Broker)
  - N8N_version = 2.6.4 (em analise atualizações para as versões mais recentes)
  - N8N_details = veja no arquivo `docs/N8N/debug_information.txt`
  - N8N_database_type = PostgreSQL

## Servidor Brasil
  - host_name = wf008.vya.digital
  - host_ip = 151.242.149.22
  - host_nbr_cpu = 16
  - host_mem = 31GB
  - host_dsh = 350GB
  - host_os = Linux Debian 12
  - host_type = VPS
  - host_region = Brasil (São Paulo)
  - ssh_type = SPA
  - ssh_script = ~/.local/bin/ssh-wf008
  - ssh_alternative = "fwknop --rc-file ~/.fwknoprc -n wf008 && sleep 3 && <command>"
  - ssh_connection = ssh key (configurado para acesso em qualquer pasta do computador)
  - ssh_user = archaris
  - user_type = sudo
  - user_information = no password user

### Databasase Server
  - host_name = wfdb02.vya.digital
  - host_ip = 82.197.64.145
  - host_nbr_cpu = 12
  - host_mem = 48GB
  - host_dsh = 1.6TB
  - host_os = Linux Debian 12
  - host_type = VPS
  - host_region = US EAST (New York)
  - ssh_type = SPA
  - ssh_script = ~/.local/bin/ssh-wfdb02
  - ssh_alternative = "fwknop --rc-file ~/.fwknoprc -n wfdb02 && sleep 3 && <command>"
  - ssh_connection = ssh key (configurado para acesso em qualquer pasta do computador)
  - ssh_user = archaris
  - user_type = sudo
  - user_information = no password user
  - database_type = MySQL (8.4.6 Community) e PostgreSQL (16.10)


### Docker Container
**ATENÇÃO - SERVIDOR EM PRODUÇÃO, NÃO EXECUTAR NENHUMA AÇÃO QUE INTERROMPA O SERVIÇO!!!**
Coleta de dados sem perigo para os serviços estão liberados
Containers ativos:
CONTAINER ID   NAMES                         PORTS
acc6f594f456   evolution_api_wea004          0.0.0.0:8088->8080/tcp
acfe0bd020ab   prod-collector-api            0.0.0.0:9102->9102/tcp, 0.0.0.0:5001->5000/tcp
e50edf5fb302   chatwoot-vya-digital-base-1   INATIVO
e3a377f1ced3   chat-vya-digital-sidekiq      3000/tcp
599b71d0f287   chat-vya-digital              3000/tcp
c6db384c6c31   chatwoot-synchat-base-1       INATIVO
92685a4d2260   synChatSidekiq                3000/tcp
e4d641cd3d78   synChat                       0.0.0.0:3008->3000/tcp
1e68f7893eb9   n8n-n8n_worker-3              5678/tcp
89d21f592a9b   n8n-n8n_worker-2              5678/tcp
7f8ab508bef5   n8n-n8n_webhook-3             5678/tcp
8ba59916367a   n8n-n8n_webhook-2             5678/tcp
eed22c19b653   n8n-n8n_worker-1              5678/tcp
bfdd6ccbb7c3   n8n-n8n_webhook-1             5678/tcp
36cab9e9fd83   n8n-n8n_mcp-1                 5678/tcp
4dd8f4d124eb   n8n-n8n_editor-1              5678/tcp
d196090b92c6   kutt-link-vya-digital         0.0.0.0:3003->3000/tcp
91fdf94c7c2d   dashboard                     0.0.0.0:3002->3000/tcp
a63299888a12   traefik                       0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp, 0.0.0.0:9090->9090/tcp
8b25ed009647   api013.vya.digital            3034/tcp
3084d9b26616   api012.vyadigital             0.0.0.0:3033->3033/tcp
07f3db72201f   pgadmin                       INATIVO
6cbf216223f3   dashy                         0.0.0.0:8083->8080/tcp
aa5455ef753d   dbmgnt002.vya.digital         8080/tcp
ac7f60be9d42   code_store                    0.0.0.0:5000->5000/tcp
7ca3a2ed1467   perfexcrm                     0.0.0.0:8001->80/tcp
4fea6cf06322   ajuda                         443/tcp, 0.0.0.0:8002->80/tcp
84863e29114b   passbolt                      0.0.0.0:8090->80/tcp, 0.0.0.0:8091->443/tcp
4fbe5603ab6a   rabbitmq                      4369/tcp, 5671/tcp, 15671/tcp, 15691-15692/tcp, 25672/tcp, 0.0.0.0:5673->5672/tcp, 0.0.0.0:15673->15672/tcp
374a44aec132   redis                         0.0.0.0:6379->6379/tcp
2c1bb216162f   portainer                     8000/tcp, 9443/tcp, 0.0.0.0:9000->9000/tcp

