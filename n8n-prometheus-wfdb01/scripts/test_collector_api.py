#!/usr/bin/env python3
"""
Script de testes de homologação da Collector API
Testa todos os endpoints e valida respostas
"""

import json
import requests
from datetime import datetime, timezone
from typing import Dict, Any
import uuid


class CollectorAPITester:
    """Tester para validação da Collector API"""
    
    def __init__(self, base_url: str = "http://localhost:5000", api_key: str = None):
        self.base_url = base_url
        self.api_key = api_key
        self.session = requests.Session()
        self.results = {
            "passed": 0,
            "failed": 0,
            "tests": []
        }
    
    def log_test(self, test_name: str, passed: bool, details: str = ""):
        """Registra resultado de um teste"""
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} | {test_name}")
        if details:
            print(f"    → {details}")
        
        self.results["tests"].append({
            "name": test_name,
            "passed": passed,
            "details": details
        })
        
        if passed:
            self.results["passed"] += 1
        else:
            self.results["failed"] += 1
    
    def test_root_endpoint(self) -> bool:
        """Testa endpoint raiz /"""
        try:
            response = self.session.get(f"{self.base_url}/")
            data = response.json()
            
            passed = (
                response.status_code == 200 and
                data.get("service") == "N8N Collector API" and
                data.get("status") == "running"
            )
            
            self.log_test(
                "GET /", 
                passed,
                f"Status: {response.status_code}, Service: {data.get('service')}"
            )
            return passed
            
        except Exception as e:
            self.log_test("GET /", False, f"Error: {str(e)}")
            return False
    
    def test_health_endpoint(self) -> bool:
        """Testa endpoint /health"""
        try:
            response = self.session.get(f"{self.base_url}/health")
            data = response.json()
            
            passed = (
                response.status_code == 200 and
                data.get("status") == "healthy" and
                "services" in data
            )
            
            self.log_test(
                "GET /health",
                passed,
                f"Status: {data.get('status')}, Services: {list(data.get('services', {}).keys())}"
            )
            return passed
            
        except Exception as e:
            self.log_test("GET /health", False, f"Error: {str(e)}")
            return False
    
    def test_metrics_endpoint(self) -> bool:
        """Testa endpoint /metrics"""
        try:
            response = self.session.get(f"{self.base_url}/metrics")
            
            # Prometheus metrics são text/plain
            passed = (
                response.status_code == 200 and
                "api_request_duration_seconds" in response.text
            )
            
            lines = len(response.text.split('\n'))
            self.log_test(
                "GET /metrics",
                passed,
                f"Status: {response.status_code}, Lines: {lines}"
            )
            return passed
            
        except Exception as e:
            self.log_test("GET /metrics", False, f"Error: {str(e)}")
            return False
    
    def test_ping_without_auth(self) -> bool:
        """Testa POST /api/ping sem autenticação (deve falhar)"""
        try:
            payload = {
                "ping_id": str(uuid.uuid4()),
                "timestamp_start": datetime.now(timezone.utc).isoformat(),
                "source": {
                    "location": "test_no_auth",
                    "datacenter": "local",
                    "country": "BR"
                }
            }
            
            response = self.session.post(
                f"{self.base_url}/api/ping",
                json=payload
            )
            
            # Deve retornar 422 (missing header) ou 401 (unauthorized)
            passed = response.status_code in [422, 401]
            
            self.log_test(
                "POST /api/ping (sem auth)",
                passed,
                f"Status: {response.status_code} (esperado 422 ou 401)"
            )
            return passed
            
        except Exception as e:
            self.log_test("POST /api/ping (sem auth)", False, f"Error: {str(e)}")
            return False
    
    def test_ping_with_invalid_auth(self) -> bool:
        """Testa POST /api/ping com API key inválida"""
        try:
            payload = {
                "ping_id": str(uuid.uuid4()),
                "timestamp_start": datetime.now(timezone.utc).isoformat(),
                "source": {
                    "location": "test_invalid_auth",
                    "datacenter": "local",
                    "country": "BR"
                }
            }
            
            headers = {"X-API-Key": "invalid-key-12345"}
            
            response = self.session.post(
                f"{self.base_url}/api/ping",
                json=payload,
                headers=headers
            )
            
            # Deve retornar 401 Unauthorized
            passed = response.status_code == 401
            
            self.log_test(
                "POST /api/ping (auth inválida)",
                passed,
                f"Status: {response.status_code} (esperado 401)"
            )
            return passed
            
        except Exception as e:
            self.log_test("POST /api/ping (auth inválida)", False, f"Error: {str(e)}")
            return False
    
    def test_ping_with_valid_auth(self) -> bool:
        """Testa POST /api/ping com autenticação válida"""
        if not self.api_key:
            self.log_test("POST /api/ping (auth válida)", False, "API key não fornecida")
            return False
        
        try:
            ping_id = str(uuid.uuid4())
            timestamp_start = datetime.now(timezone.utc)
            
            payload = {
                "ping_id": ping_id,
                "timestamp_start": timestamp_start.isoformat(),
                "source": {
                    "location": "test_valid_auth",
                    "datacenter": "homolog",
                    "country": "BR"
                }
            }
            
            headers = {"X-API-Key": self.api_key}
            
            response = self.session.post(
                f"{self.base_url}/api/ping",
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                passed = (
                    data.get("status") == "success" and
                    data.get("ping_id") == ping_id and
                    "network_rtt_ms" in data and
                    "processing_time_ms" in data
                )
                
                self.log_test(
                    "POST /api/ping (auth válida)",
                    passed,
                    f"RTT: {data.get('network_rtt_ms'):.2f}ms, Processing: {data.get('processing_time_ms'):.2f}ms"
                )
                return passed
            else:
                self.log_test(
                    "POST /api/ping (auth válida)",
                    False,
                    f"Status: {response.status_code}, Response: {response.text[:100]}"
                )
                return False
            
        except Exception as e:
            self.log_test("POST /api/ping (auth válida)", False, f"Error: {str(e)}")
            return False
    
    def test_ping_invalid_payload(self) -> bool:
        """Testa POST /api/ping com payload inválido"""
        if not self.api_key:
            self.log_test("POST /api/ping (payload inválido)", False, "API key não fornecida")
            return False
        
        try:
            # Payload faltando campos obrigatórios
            payload = {
                "ping_id": str(uuid.uuid4())
                # Faltando timestamp_start e source
            }
            
            headers = {"X-API-Key": self.api_key}
            
            response = self.session.post(
                f"{self.base_url}/api/ping",
                json=payload,
                headers=headers
            )
            
            # Deve retornar 422 (Unprocessable Entity)
            passed = response.status_code == 422
            
            self.log_test(
                "POST /api/ping (payload inválido)",
                passed,
                f"Status: {response.status_code} (esperado 422)"
            )
            return passed
            
        except Exception as e:
            self.log_test("POST /api/ping (payload inválido)", False, f"Error: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Executa todos os testes"""
        print("\n" + "="*60)
        print("TESTES DE HOMOLOGAÇÃO - COLLECTOR API")
        print("="*60 + "\n")
        
        # Testes de endpoints públicos
        print("📋 Endpoints Públicos:")
        self.test_root_endpoint()
        self.test_health_endpoint()
        self.test_metrics_endpoint()
        
        # Testes de segurança
        print("\n🔒 Segurança e Autenticação:")
        self.test_ping_without_auth()
        self.test_ping_with_invalid_auth()
        
        # Testes funcionais
        print("\n⚡ Funcionalidade:")
        self.test_ping_with_valid_auth()
        self.test_ping_invalid_payload()
        
        # Relatório final
        print("\n" + "="*60)
        print("RESUMO DOS TESTES")
        print("="*60)
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        print(f"📊 Total:  {self.results['passed'] + self.results['failed']}")
        
        success_rate = (self.results['passed'] / (self.results['passed'] + self.results['failed'])) * 100
        print(f"🎯 Success Rate: {success_rate:.1f}%")
        print("="*60 + "\n")
        
        return self.results


def main():
    """Função principal"""
    # Ler API key do arquivo .env
    api_key = None
    try:
        with open(".secrets/.env", "r") as f:
            for line in f:
                if line.startswith("COLLECTOR_API_KEY="):
                    # Remove aspas simples
                    api_key = line.split("=", 1)[1].strip().strip("'\"")
                    break
    except FileNotFoundError:
        print("⚠️  Arquivo .secrets/.env não encontrado")
        print("    Alguns testes serão ignorados\n")
    
    # Executar testes
    tester = CollectorAPITester(api_key=api_key)
    results = tester.run_all_tests()
    
    # Retornar código de saída apropriado
    exit(0 if results["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
