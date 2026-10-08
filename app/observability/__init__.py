"""Infraestrutura centralizada de logging estruturado em JSON.

Os logs em JSON permitem ingestão simples em ferramentas de observabilidade, filtros
mais confiáveis em consultas e uma correlação mais clara entre eventos do sistema.
Esta camada centraliza o formato e evita que cada módulo reimplemente a serialização
manual de registros.
"""

from app.observability.logging import JsonFormatter, configure_json_logging

__all__ = ["JsonFormatter", "configure_json_logging"]
