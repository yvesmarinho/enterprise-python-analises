"""
Credentials Helper
Módulo para carregar credenciais de forma segura
"""

import json
import os
from pathlib import Path
from typing import Dict, Optional


class CredentialsManager:
    """Gerenciador de credenciais do projeto"""
    
    def __init__(self, secrets_file: Optional[Path] = None):
        """
        Inicializa o gerenciador de credenciais
        
        Args:
            secrets_file: Caminho para o arquivo de credenciais
                         Se None, usa o caminho padrão
        """
        if secrets_file is None:
            # Caminho padrão: .secrets/credentials.json
            self.secrets_file = Path(__file__).parent.parent / ".secrets" / "credentials.json"
        else:
            self.secrets_file = Path(secrets_file)
        
        self._credentials = None
    
    def load(self) -> Dict:
        """
        Carrega credenciais do arquivo JSON
        
        Returns:
            Dicionário com as credenciais
            
        Raises:
            FileNotFoundError: Se o arquivo não existir
            json.JSONDecodeError: Se o JSON for inválido
        """
        if self._credentials is not None:
            return self._credentials
        
        if not self.secrets_file.exists():
            raise FileNotFoundError(
                f"Arquivo de credenciais não encontrado: {self.secrets_file}\n"
                f"Copie o template e configure:\n"
                f"  cp {self.secrets_file.parent}/credentials.template.json {self.secrets_file}"
            )
        
        with open(self.secrets_file) as f:
            self._credentials = json.load(f)
        
        return self._credentials
    
    def get(self, key: str, default=None):
        """
        Obtém uma credencial específica
        
        Args:
            key: Chave da credencial (ex: 'n8n.api_key')
            default: Valor padrão se não encontrado
            
        Returns:
            Valor da credencial ou default
            
        Example:
            >>> creds = CredentialsManager()
            >>> api_key = creds.get('n8n.api_key')
            >>> db_host = creds.get('postgresql.host')
        """
        credentials = self.load()
        
        # Suporta keys aninhadas (ex: 'n8n.api_key')
        keys = key.split('.')
        value = credentials
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_n8n_config(self) -> Dict:
        """
        Retorna configuração completa do N8N
        
        Returns:
            Dicionário com url e api_key
        """
        return self.get('n8n', {})
    
    def get_postgresql_config(self) -> Dict:
        """
        Retorna configuração completa do PostgreSQL
        
        Returns:
            Dicionário com host, port, database, user, password
        """
        return self.get('postgresql', {})
    
    def get_grafana_config(self) -> Dict:
        """
        Retorna configuração completa do Grafana
        
        Returns:
            Dicionário com url e api_key
        """
        return self.get('grafana', {})
    
    def get_prometheus_config(self) -> Dict:
        """
        Retorna configuração do Prometheus
        
        Returns:
            Dicionário com url
        """
        return self.get('prometheus', {})
    
    def get_server_config(self) -> Dict:
        """
        Retorna configuração do servidor
        
        Returns:
            Dicionário com host, ssh_user, ssh_key_path
        """
        return self.get('server', {})
    
    def validate(self) -> bool:
        """
        Valida se todas as credenciais necessárias estão presentes
        
        Returns:
            True se válido, False caso contrário
        """
        credentials = self.load()
        
        required_keys = [
            ('n8n', 'url'),
            ('n8n', 'api_key'),
        ]
        
        for keys in required_keys:
            value = credentials
            for key in keys:
                if not isinstance(value, dict) or key not in value:
                    print(f"❌ Credencial faltando: {'.'.join(keys)}")
                    return False
                value = value[key]
            
            # Verificar se não é valor de exemplo
            if isinstance(value, str) and ('SUBSTITUA' in value or 'sua-' in value or 'exemplo' in value):
                print(f"⚠️  Credencial não configurada: {'.'.join(keys)} = {value}")
                return False
        
        print("✅ Credenciais validadas com sucesso!")
        return True
    
    def export_env_vars(self) -> Dict[str, str]:
        """
        Exporta credenciais como variáveis de ambiente
        
        Returns:
            Dicionário com variáveis de ambiente
            
        Example:
            >>> creds = CredentialsManager()
            >>> env_vars = creds.export_env_vars()
            >>> os.environ.update(env_vars)
        """
        credentials = self.load()
        
        env_vars = {
            'N8N_URL': credentials.get('n8n', {}).get('url', ''),
            'N8N_API_KEY': credentials.get('n8n', {}).get('api_key', ''),
            'PGHOST': credentials.get('postgresql', {}).get('host', ''),
            'PGPORT': str(credentials.get('postgresql', {}).get('port', 5432)),
            'PGDATABASE': credentials.get('postgresql', {}).get('database', ''),
            'PGUSER': credentials.get('postgresql', {}).get('user', ''),
            'PGPASSWORD': credentials.get('postgresql', {}).get('password', ''),
            'GRAFANA_URL': credentials.get('grafana', {}).get('url', ''),
            'GRAFANA_API_KEY': credentials.get('grafana', {}).get('api_key', ''),
            'PROMETHEUS_URL': credentials.get('prometheus', {}).get('url', ''),
        }
        
        # Remover valores vazios
        return {k: v for k, v in env_vars.items() if v}


def load_credentials(secrets_file: Optional[Path] = None) -> Dict:
    """
    Função helper para carregar credenciais rapidamente
    
    Args:
        secrets_file: Caminho para o arquivo (opcional)
        
    Returns:
        Dicionário com credenciais
    """
    manager = CredentialsManager(secrets_file)
    return manager.load()


def main():
    """Função principal para testar o módulo"""
    print("🔐 Testando Credentials Manager\n")
    
    try:
        manager = CredentialsManager()
        
        # Validar
        print("Validando credenciais...")
        is_valid = manager.validate()
        print()
        
        if not is_valid:
            print("⚠️  Configure o arquivo credentials.json antes de usar")
            return
        
        # Mostrar configurações (sem expor senhas)
        print("Configurações carregadas:")
        print(f"  N8N URL: {manager.get('n8n.url')}")
        print(f"  N8N API Key: {'*' * 20} (oculto)")
        print(f"  PostgreSQL Host: {manager.get('postgresql.host')}")
        print(f"  PostgreSQL Database: {manager.get('postgresql.database')}")
        print()
        
        # Exportar variáveis de ambiente
        print("Variáveis de ambiente disponíveis:")
        env_vars = manager.export_env_vars()
        for key in env_vars.keys():
            if 'PASSWORD' in key or 'KEY' in key:
                print(f"  {key}={'*' * 20} (oculto)")
            else:
                print(f"  {key}={env_vars[key]}")
        
    except FileNotFoundError as e:
        print(f"❌ Erro: {e}")
    except json.JSONDecodeError as e:
        print(f"❌ Erro ao parsear JSON: {e}")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")


if __name__ == "__main__":
    main()
