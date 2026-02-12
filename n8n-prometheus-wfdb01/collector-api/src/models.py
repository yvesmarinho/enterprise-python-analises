"""Modelos de dados Pydantic"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class SourceInfo(BaseModel):
    """Informações da origem do ping"""
    location: str = Field(..., description="Nome da localização (ex: wf008_brazil)")
    datacenter: str = Field(..., description="Nome do datacenter")
    country: str = Field(..., description="Código do país (ex: BR, US)")


class PingRequest(BaseModel):
    """Request de ping recebido"""
    timestamp_start: str = Field(..., description="Timestamp ISO 8601 de início do ping")
    source: SourceInfo = Field(..., description="Informações da origem")
    ping_id: str = Field(..., description="ID único do ping")


class PingResponse(BaseModel):
    """Response de ping"""
    status: str = Field(..., description="Status da resposta: success ou error")
    ping_id: str = Field(..., description="ID do ping recebido")
    timestamp_received: str = Field(..., description="Timestamp de recebimento")
    timestamp_processed: str = Field(..., description="Timestamp de processamento completo")
    processing_time_ms: float = Field(..., description="Tempo de processamento em ms")
    network_rtt_ms: Optional[float] = Field(None, description="RTT calculado em ms")
    message: str = Field(default="Ping received successfully")


class HealthResponse(BaseModel):
    """Response de health check"""
    status: str
    version: str
    timestamp: str
    services: dict


class ErrorResponse(BaseModel):
    """Response de erro"""
    error: str
    detail: Optional[str] = None
    timestamp: str
