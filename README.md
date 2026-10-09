# Desafio Observabilidade B3 - Stream Authorization API

## Visão geral
API FastAPI para autorização de streaming com integração a um mock provider. O endpoint principal recebe user_id e movie_id, consulta o provider e retorna autorização, resolução e metadados da resposta.

## Arquitetura
```text
Cliente
  |
  v
API FastAPI :8000
  |
  v
Mock Provider :8001
```

No Docker Compose, a API publica porta no host e consome o mock provider pela rede interna.

## Execução com Docker Compose
Subir stack:

```bash
docker compose up --build -d
docker compose ps
```

Encerrar:

```bash
docker compose down
```

## Observabilidade
Prometheus:
- URL: http://127.0.0.1:9090
- Coleta métricas da API em http://api:8000/metrics

Grafana principal (dashboard RED):
- URL: http://127.0.0.1:3000
- Credenciais padrão: admin / admin
- Dashboard: Stream Authorization - RED

LGTM (Grafana + Tempo + Loki no bundle):
- URL: http://127.0.0.1:3001
- Traces distribuídos disponíveis no Tempo
- Loki está disponível no bundle, mas os logs da aplicação seguem em stdout JSON nesta implementação

Logs:
- JSON estruturado
- Sanitização de campos sensíveis com [REDACTED]
- trace_id e span_id reais quando há span válido
- drm_token ausente dos logs

Métricas RED da API:
- http_requests_total
- http_request_errors_total
- http_request_duration_seconds
- Labels: method, endpoint, status_code
- Rotas sem match normalizadas como unmatched

## Endpoints
- GET /health
- GET /stream/authorize
- GET /metrics
- GET /docs
- GET /openapi.json

Exemplos:

```bash
curl -i http://127.0.0.1:8000/health
curl -i "http://127.0.0.1:8000/stream/authorize?user_id=usr_99823&movie_id=mov_dune_part2"
curl -i http://127.0.0.1:8000/metrics
```

## Teste de carga com k6
A stack deve estar ativa antes do teste:

```bash
docker compose up -d
```

Execução rápida:

```bash
K6_VUS=5 K6_DURATION=30s \
docker compose --profile load-test run --rm k6-load-test
```

Execução final do desafio:

```bash
K6_VUS=50 K6_DURATION=5m \
docker compose --profile load-test run --rm k6-load-test
```

Thresholds:
- http_req_failed: rate<0.01
- http_req_duration: p(95)<1000
- checks: rate>0.99

## Execução local sem Compose
```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
uvicorn mock_provider.main:app --host 127.0.0.1 --port 8001
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Testes
```bash
python -m pytest -q
```

Estado validado:
- 64 passed
- 1 warning conhecido do ecossistema Starlette/httpx

## Limitações atuais
- Sem persistência de dados
- Sem alertas configurados
- Sem pipeline OTLP de logs para Loki
- Credenciais locais de observabilidade em modo de desenvolvimento

## Próximos passos
- Persistência para componentes de observabilidade
- Alertas operacionais
- Pipeline OTLP de logs para Loki
- Ambientes distribuídos (staging/produção)
- Endurecimento de credenciais locais
