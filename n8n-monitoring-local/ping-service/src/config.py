"""Configuração do Ping Service"""
import os
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Configurações do serviço"""
    
    # API Configuration
    target_url: str = Field(default="http://collector-api:5000/api/ping")
    collector_api_key: str = Field(default="dev-secret-key-12345", alias="COLLECTOR_API_KEY")
    
    # Ping Configuration
    ping_interval: int = Field(default=30, description="Intervalo entre pings em segundos")
    request_timeout: int = Field(default=10, description="Timeout de requisição em segundos")
    
    # Source Information
    source_location: str = Field(default="local_dev_brazil")
    source_datacenter: str = Field(default="local")
    source_country: str = Field(default="BR")
    
    # Victoria Metrics
    victoria_metrics_url: str = Field(default="http://victoria-metrics:8428")
    push_metrics_interval: int = Field(default=60, description="Intervalo de push de métricas em segundos")
    
    # Metrics Server
    metrics_port: int = Field(default=9101)
    
    # Logging
    log_level: str = Field(default="INFO")
    environment: str = Field(default="development")
    
    class Config:
        env_file = ".secrets/.env"
        case_sensitive = False
        populate_by_name = True


# Global settings instance
settings = Settings()
