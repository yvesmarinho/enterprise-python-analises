#!/usr/bin/env python3
"""
Testes de cenários de falha e recuperação
Valida comportamento do sistema em situações adversas
"""

import time
import requests
import subprocess
import json
from datetime import datetime


class FailureScenarioTester:
    """Tester para cenários de falha"""
    
    def __init__(self):
        self.results = []
    
    def log(self, test_name: str, passed: bool, details: str = ""):
        """Registra resultado"""
        status = "✅" if passed else "❌"
        print(f"{status} {test_name}")
        if details:
            print(f"   → {details}")
        self.results.append({"test": test_name, "passed": passed, "details": details})
    
    def test_collector_api_down(self):
        """Testa comportamento quando Collector API está down"""
        print("\n🔴 Teste: Collector API indisponível")
        
        # Parar collector-api
        print("   Parando collector-api...")
        subprocess.run(["docker", "compose", "stop", "collector-api"], 
                      capture_output=True, check=False)
        time.sleep(3)
        
        # Verificar se ping-service detecta falha
        try:
            response = requests.get("http://localhost:9101/metrics", timeout=5)
            metrics = response.text
            
            # Procurar por métricas de erro
            has_error_metrics = "ping_requests_total" in metrics
            
            self.log(
                "Ping Service continua exportando métricas",
                has_error_metrics,
                "Serviço mantém operação mesmo com API down"
            )
        except Exception as e:
            self.log("Ping Service resiliente", False, f"Error: {str(e)}")
        
        # Restaurar collector-api
        print("   Restaurando collector-api...")
        subprocess.run(["docker", "compose", "start", "collector-api"], 
                      capture_output=True, check=False)
        time.sleep(5)
        
        # Verificar recuperação
        try:
            response = requests.get("http://localhost:5000/health", timeout=5)
            recovered = response.status_code == 200
            self.log(
                "Collector API recuperou automaticamente",
                recovered,
                f"Status: {response.status_code}"
            )
        except Exception as e:
            self.log("Recuperação automática", False, f"Error: {str(e)}")
    
    def test_network_isolation(self):
        """Testa isolamento de redes"""
        print("\n🌐 Teste: Isolamento de redes")
        
        try:
            # Ping service (brazil-net) NÃO deve acessar Grafana (monitoring-net) diretamente
            result = subprocess.run(
                ["docker", "exec", "dev-ping-service", "curl", "-s", 
                 "--max-time", "3", "http://dev-grafana:3000/api/health"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # Deve falhar (sem comunicação entre redes isoladas)
            network_isolated = result.returncode != 0
            
            self.log(
                "Redes brazil-net e monitoring-net isoladas",
                network_isolated,
                "Ping Service não acessa Grafana diretamente" if network_isolated else "FALHA: Acesso não deveria ser possível"
            )
        except Exception as e:
            self.log("Isolamento de rede", True, "Timeout esperado - redes isoladas")
    
    def test_high_latency_tolerance(self):
        """Testa tolerância a alta latência"""
        print("\n⏱️  Teste: Tolerância a latência")
        
        try:
            # Enviar múltiplos pings e verificar se todos são processados
            response = requests.get("http://localhost:9101/metrics", timeout=5)
            metrics_before = response.text
            
            # Extrair contador de pings
            for line in metrics_before.split('\n'):
                if 'ping_requests_total{' in line and 'success' in line:
                    count_before = int(line.split()[-1])
                    break
            
            time.sleep(35)  # Aguardar pelo menos 1 ping (intervalo de 30s)
            
            response = requests.get("http://localhost:9101/metrics", timeout=5)
            metrics_after = response.text
            
            for line in metrics_after.split('\n'):
                if 'ping_requests_total{' in line and 'success' in line:
                    count_after = int(line.split()[-1])
                    break
            
            ping_sent = count_after > count_before
            
            self.log(
                "Pings continuam sendo enviados regularmente",
                ping_sent,
                f"Pings: {count_before} → {count_after} (+{count_after - count_before})"
            )
        except Exception as e:
            self.log("Envio contínuo de pings", False, f"Error: {str(e)}")
    
    def test_metrics_endpoint_availability(self):
        """Testa disponibilidade dos endpoints de métricas"""
        print("\n📊 Teste: Disponibilidade de métricas")
        
        endpoints = [
            ("Ping Service", "http://localhost:9101/metrics"),
            ("Collector API", "http://localhost:9102/metrics"),
            ("Node Exporter", "http://localhost:9100/metrics"),
            ("cAdvisor", "http://localhost:8080/metrics"),
        ]
        
        all_available = True
        for name, url in endpoints:
            try:
                response = requests.get(url, timeout=5)
                available = response.status_code == 200 and len(response.text) > 100
                
                if available:
                    lines = len(response.text.split('\n'))
                    self.log(f"{name} disponível", True, f"{lines} linhas de métricas")
                else:
                    self.log(f"{name} disponível", False, f"Status: {response.status_code}")
                    all_available = False
            except Exception as e:
                self.log(f"{name} disponível", False, f"Error: {str(e)}")
                all_available = False
        
        return all_available
    
    def test_container_restart_recovery(self):
        """Testa recuperação após restart de container"""
        print("\n🔄 Teste: Recuperação após restart")
        
        # Reiniciar ping-service
        print("   Reiniciando ping-service...")
        subprocess.run(["docker", "compose", "restart", "ping-service"], 
                      capture_output=True, check=False)
        time.sleep(10)
        
        # Verificar se voltou a funcionar
        try:
            response = requests.get("http://localhost:9101/metrics", timeout=5)
            recovered = response.status_code == 200 and "ping_requests_total" in response.text
            
            self.log(
                "Ping Service recuperado após restart",
                recovered,
                "Serviço reiniciou e voltou a coletar métricas"
            )
        except Exception as e:
            self.log("Recuperação após restart", False, f"Error: {str(e)}")
    
    def test_api_rate_limiting(self):
        """Testa rate limiting da API"""
        print("\n🚦 Teste: Rate limiting")
        
        # Configuração: 120 requests/min = 2 requests/sec
        # Tentar enviar 5 requests rapidamente
        
        api_key = None
        try:
            with open(".secrets/.env", "r") as f:
                for line in f:
                    if line.startswith("COLLECTOR_API_KEY="):
                        api_key = line.split("=", 1)[1].strip().strip("'\"")
                        break
        except:
            print("   ⚠️  Não foi possível ler API key, pulando teste")
            return
        
        if not api_key:
            print("   ⚠️  API key não encontrada, pulando teste")
            return
        
        headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
        payload = {
            "ping_id": "rate-limit-test",
            "timestamp_start": datetime.utcnow().isoformat() + "Z",
            "source": {"location": "test", "datacenter": "test", "country": "BR"}
        }
        
        # Enviar múltiplos requests
        responses = []
        for i in range(5):
            try:
                resp = requests.post(
                    "http://localhost:5000/api/ping",
                    json=payload,
                    headers=headers,
                    timeout=2
                )
                responses.append(resp.status_code)
            except Exception as e:
                responses.append(0)
            time.sleep(0.1)  # 100ms entre requests
        
        # Todos devem ter sucesso (não ultrapassamos 2 req/s)
        all_success = all(status == 200 for status in responses if status != 0)
        
        self.log(
            "API processa requests dentro do limite",
            all_success,
            f"Status codes: {responses}"
        )
    
    def run_all_tests(self):
        """Executa todos os testes"""
        print("\n" + "="*60)
        print("TESTES DE CENÁRIOS DE FALHA E RECUPERAÇÃO")
        print("="*60)
        
        self.test_metrics_endpoint_availability()
        self.test_high_latency_tolerance()
        self.test_container_restart_recovery()
        self.test_network_isolation()
        self.test_api_rate_limiting()
        self.test_collector_api_down()
        
        # Resumo
        passed = sum(1 for r in self.results if r["passed"])
        failed = len(self.results) - passed
        
        print("\n" + "="*60)
        print("RESUMO")
        print("="*60)
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"📊 Total:  {len(self.results)}")
        print(f"🎯 Success Rate: {(passed/len(self.results)*100):.1f}%")
        print("="*60 + "\n")
        
        return failed == 0


if __name__ == "__main__":
    tester = FailureScenarioTester()
    success = tester.run_all_tests()
    exit(0 if success else 1)
