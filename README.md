# Desafio Observabilidade B3 - Stream Authorization API

## Visão geral
Esta aplicação expõe uma API FastAPI de autorização de streaming. O endpoint `/stream/authorize` recebe `user_id` e `movie_id`, consulta um mock provider e decide se o usuário fica autorizado, qual resolução será entregue (`4K`, `1080p` ou `none`) e quais metadados acompanham a resposta.

Quando a dependência externa falha, a API converte apenas essas falhas em HTTP 503 para manter a resposta pública estável. O projeto também emite métricas RED, logs estruturados em JSON e traces distribuídos, tudo executado com Docker Compose.

## Arquitetura
```text
                         +----------------------+
                         |   Cliente / k6       |
                         +----------+-----------+
                                    |
                                    | HTTP
                                    v
                         +----------+-----------+
                         | API FastAPI :8000    |
                         | /stream/authorize    |
                         | /health              |
                         | /metrics             |
                         +----+-------------+---+
                              |             |
                    HTTPX     |             | Métricas Prometheus
                              v             v
                   +----------+---+   +-----+----------------+
                   | Mock Provider |   | Prometheus :9090     |
                   | interno :8001 |   +----------+-----------+
                   +-------+-------+              |
                           |                      v
                           |             +--------+-----------+
                           |             | Grafana RED :3000  |
                           |             +--------------------+
                           |
                           | Traces OTLP/HTTP
                           v
                +----------+-------------------------+
                | grafana/otel-lgtm :0.36.0          |
                | Collector OTLP :4317/4318          |
                | Tempo                               |
                | Loki                                |
                | Prometheus interno                 |
                | Grafana LGTM :3001                  |
                +-------------------------------------+
```

O `Prometheus` separado em `9090` coleta `/metrics` da API e alimenta o dashboard RED principal. O `Prometheus` interno do `grafana/otel-lgtm` não alimenta esse dashboard; a stack `LGTM` é usada principalmente para OTLP e `Tempo`.

O Grafana em `3000` mostra o dashboard RED. O Grafana em `3001` pertence ao bundle LGTM e serve para investigar traces.

Após o diagrama: os logs permanecem em `stdout` JSON. O `Loki` existe dentro do bundle, mas não recebe os logs da aplicação nesta implementação.

## Componentes
- API FastAPI: implementa o fluxo de autorização e publica `/health`, `/metrics` e `/stream/authorize`.
- Mock provider: simula a dependência externa com cenários de sucesso, lentidão e erro.
- `Prometheus` separado: coleta as métricas RED expostas pela API.
- `Grafana` RED: mostra o dashboard operacional da aplicação.
- `grafana/otel-lgtm:0.36.0`: bundle com Collector, `Tempo`, `Loki`, `Prometheus` interno e `Grafana` LGTM.
- `k6`: executa o teste de carga obrigatório contra a API.

## Como executar
Subir a stack:
```bash
docker compose up --build -d
docker compose ps
```

Encerrar a stack:
```bash
docker compose down
```

Preparar a execução local:
```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Terminal 1, mock provider:

```bash
uvicorn mock_provider.main:app --host 127.0.0.1 --port 8001
```

Terminal 2, API:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Endpoints
- GET `/health`
- GET `/stream/authorize`
- GET `/metrics`
- GET `/docs`
- GET `/openapi.json`

Exemplos:

```bash
curl -i http://127.0.0.1:8000/health
curl -i "http://127.0.0.1:8000/stream/authorize?user_id=usr_99823&movie_id=mov_dune_part2"
curl -i http://127.0.0.1:8000/metrics
```

## Observabilidade
O projeto registra logs estruturados em JSON com sanitização de campos sensíveis, incluindo proteção contra vazamento de `drm_token`. Quando há span válido, os logs carregam `trace_id` e `span_id` reais.

As métricas RED seguem o padrão da aplicação:
- `http_requests_total`
- `http_request_errors_total`
- `http_request_duration_seconds`
- Labels: `method`, `endpoint`, `status_code`
- Rotas sem correspondência usam `unmatched`

`Prometheus` em `9090` coleta as métricas da API em `http://api:8000/metrics`.

## Dashboard
O dashboard principal fica em `http://127.0.0.1:3000`.

Credenciais padrão:
- usuário: `admin`
- senha: `admin`

O arquivo de provisionamento é `grafana-dashboard-red.json` e o UID do dashboard é `stream-authorization-red`.

Painéis do dashboard:
- Requisições por segundo
- Erros por segundo
- Latência p95
- Requisições por endpoint e status HTTP

## Tracing distribuído
O tracing usa OpenTelemetry com exportação OTLP/HTTP para o bundle `grafana/otel-lgtm:0.36.0`.

Esse bundle expõe:
- `OpenTelemetry Collector`
- `Tempo`
- `Loki`
- `Prometheus` interno
- `Grafana` LGTM em `http://127.0.0.1:3001`

O tracing foi validado com um trace que contém `stream-authorization-api` e `mock-provider`, e o `trace_id` dos logs foi localizado no `Tempo`.

## Teste de carga
O teste de carga usa `k6` com o profile `load-test`; ele não sobe na inicialização normal.

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
- `http_req_failed`: `rate<0.01`
- `http_req_duration`: `p(95)<1000`
- `checks`: `rate>0.99`

O script usa `BASE_URL`, `K6_VUS` e `K6_DURATION`, com defaults `http://api:8000`, `50` e `5m`.

Resultado final validado do `k6`:
- `50` VUs
- `5` minutos
- `25.708` requisições
- `85,61 req/s`
- `0` falhas HTTP
- `100%` dos checks
- `p95` de `593,75 ms`

## Testes automatizados
Executar:

```bash
python -m pytest -q
```

Estado validado:
- `64 passed`
- `1 warning` conhecido do ecossistema Starlette/httpx

## Limitações
- Não há persistência de dados.
- Não há alertas operacionais configurados.
- Os logs da aplicação permanecem em `stdout` JSON; o `Loki` existe no bundle LGTM, mas não recebe os logs nesta implementação.
- As credenciais locais de observabilidade permanecem as padrão de desenvolvimento.

## Próximos passos
- Persistência para componentes de observabilidade.
- Alertas operacionais.
- Pipeline OTLP de logs para `Loki`.
- Ambientes distribuídos para validação em staging e produção.
- Endurecimento das credenciais locais.
