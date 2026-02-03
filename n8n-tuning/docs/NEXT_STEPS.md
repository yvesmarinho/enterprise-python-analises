# Próximos Passos - N8N Performance Monitoring

## 1. Preparar Stack Grafana/Victoria Metrics para Migração

### 1.1 Exportar Dados Coletados
- Exportar dados do VictoriaMetrics (formato snapshot ou backup)
- Documentar período de coleta e volume de dados
- Validar integridade dos dados exportados

### 1.2 Configurar Volumes Persistentes
- Alterar docker-compose.yml para usar volumes nomeados ou bind mounts específicos
- Definir estrutura de diretórios no servidor de destino:
  - `/opt/monitoring/victoria-data` - Dados do VictoriaMetrics
  - `/opt/monitoring/grafana-data` - Dados do Grafana (dashboards, configurações)
  - `/opt/monitoring/scripts` - Scripts de coleta Python
- Configurar permissões adequadas (UID 472 para Grafana)

### 1.3 Containerizar Scripts de Coleta
- Criar Dockerfile para ambiente Python com dependências (requests, prometheus_client)
- Configurar cron dentro do container para executar coleta a cada 3 minutos
- Implementar health check e logging adequado
- Montar volumes para logs e credenciais
- Integrar ao docker-compose.yml da stack

## 2. Instalação do Node Exporter no Servidor N8N

### 2.1 Análise de Riscos
**Riscos durante horário de utilização:**
- ✅ **Baixo risco**: Node Exporter é processo read-only, não modifica sistema
- ⚠️ **Consumo de recursos**: ~10-20MB RAM, CPU negligível (<0.1%)
- ✅ **Sem downtime**: Instalação não requer reinicialização do N8N
- ⚠️ **Exposição de porta**: Porta 9100 deve ser protegida (firewall/VPN)

**Recomendação**: Pode ser instalado em horário comercial com impacto mínimo

### 2.2 Coleta de Métricas de Containers
Para coletar métricas dos containers Docker (incluindo N8N):
- **Opção 1 (Recomendada)**: cAdvisor
  - Container dedicado que expõe métricas de todos os containers
  - Porta padrão: 8080
  - Acesso aos sockets Docker: `/var/run/docker.sock:/var/run/docker.sock:ro`
  
- **Opção 2**: Docker Daemon Metrics
  - Habilitar metrics-addr no daemon.json
  - Expõe métricas nativas do Docker engine
  
- **Node Exporter Completo**:
  ```bash
  docker run -d \
    --name node-exporter \
    --net="host" \
    --pid="host" \
    -v "/:/host:ro,rslave" \
    prom/node-exporter:latest \
    --path.rootfs=/host
  ```

## 3. Métricas de Desempenho do Servidor

### 3.1 Métricas do Sistema (Node Exporter)
- **CPU**: Utilização por core, load average, context switches
- **Memória**: Total, disponível, cache, swap
- **Disco**: I/O, latência, espaço disponível, inodes
- **Rede**: Throughput, pacotes, erros, conexões TCP

### 3.2 Dashboards Grafana
- Dashboard "System Overview" com painéis principais
- Alertas para:
  - CPU > 80% por 5min
  - Memória disponível < 10%
  - Disco > 85% de uso
  - Load average > número de cores

## 4. Métricas de Desempenho dos Containers

### 4.1 Métricas do cAdvisor
- **Por container**:
  - CPU usage e throttling
  - Memória (working set, RSS, cache)
  - Network I/O (bytes tx/rx)
  - Disk I/O (read/write ops e bytes)
  - Restarts e health status

### 4.2 Dashboard Container Performance
- Tabela comparativa de todos os containers
- Gráficos de tendência de recursos
- Alertas para containers com comportamento anômalo:
  - Uso de CPU > 80%
  - Memória > 90% do limit
  - Restarts frequentes

## 5. Ordem de Execução Recomendada

1. **Semana 1**: Preparar stack para migração (volumes, container de coleta)
2. **Semana 2**: Instalar Node Exporter e cAdvisor no servidor N8N
3. **Semana 3**: Criar dashboards de servidor e containers
4. **Semana 4**: Configurar alertas e documentação final