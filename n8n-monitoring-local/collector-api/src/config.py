"""Configuração do Collector API"""
import os
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Configurações do serviço"""
    
    # API Configuration
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=5000)
    api_key: str = Field(default="dev-secret-key-12345", alias="COLLECTOR_API_KEY")
    
    # N8N Configuration
    n8n_url: str = Field(default="https://workflow.vya.digital/")
    n8n_api_key: str = Field(default="")
    
    # PostgreSQL Configuration (External Server)
    postgres_host: str = Field(default="wfdb02.vya.digital", alias="POSTGRES_HOSTNAME")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_user: str = Field(default="monitor_user", alias="POSTGRES_USER")
    postgres_password: str = Field(default="", alias="POSTGRES_PASSWORD")
    postgres_db: str = Field(default="monitor_db", alias="POSTGRES_DB")
    
    # MySQL Configuration (External Server)
    mysql_host: str = Field(default="wfdb02.vya.digital", alias="MYSQL_HOSTNAME")
    mysql_port: int = Field(default=3306, alias="MYSQL_PORT")
    mysql_user: str = Field(default="monitor_user", alias="MYSQL_USER")
    mysql_password: str = Field(default="", alias="MYSQL_PASSWORD")
    mysql_db: str = Field(default="monitor_db", alias="MYSQL_DB")
    
    # Victoria Metrics
    victoria_metrics_url: str = Field(default="http://victoria-metrics:8428")
    
    # Metrics Server
    metrics_port: int = Field(default=9102)
    
    # Database Probe Configuration
    db_probe_interval: int = Field(default=60, description="Intervalo de probe de DB em segundos")
    db_query_timeout: int = Field(default=5, description="Timeout de query em segundos")
    
    # Rate Limiting
    rate_limit_requests: int = Field(default=120, description="Requests por minuto")
    
    # Logging
    log_level: str = Field(default="INFO")
    environment: str = Field(default="development")
    
    class Config:
        env_file = ".secrets/.env"
        case_sensitive = False
        populate_by_name = True


# Global settings instance
settings = Settings()
