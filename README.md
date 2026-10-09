# Desafio Observabilidade B3 - Stream Authorization API

## 1. Título
API HTTP para autorização de streaming com FastAPI, integração com provider externo simulado e foco em observabilidade operacional.

## 2. Visão geral
Este projeto expõe uma API principal responsável por autorizar streaming com base em dados retornados por um mock provider externo. O fluxo principal recebe `user_id` e `movie_id`, consulta o provider e decide autorização e resolução final (`4K`, `1080p` ou `none`).

O provider simulado suporta modos `success`, `slow` e `error`, permitindo validar cenários de sucesso, lentidão e indisponibilidade. Falhas externas esperadas continuam convertidas para HTTP 503 na API principal, preservando uma resposta pública estável.

A aplicação já publica logs estruturados em JSON com sanitização de dados sensíveis e também expõe métricas RED em `/metrics`. A execução principal em ambiente local de containers ocorre via Docker Compose com healthchecks ativos.

## 3. Arquitetura
```text
Cliente
  |
  v
API FastAPI :8000
  |
  v
Mock Provider :8001
```

No Docker Compose, somente a API principal publica porta para o host. O mock provider permanece na rede interna da stack e é consumido pela API via comunicação entre serviços.

## 4. Estrutura do projeto
```text
.
├── app/
│   ├── __init__.py
│   ├── logging.py
│   ├── main.py
│   ├── provider.py
│   └── schemas.py
├── mock_provider/
│   ├── __init__.py
│   └── main.py
├── tests/
├── scripts/
├── Dockerfile
├── compose.yaml
├── requirements.txt
└── README.md
```

## 5. Funcionalidades
- Autorização de streaming com regras de negócio da API principal.
- Validações de entrada via query params (`user_id`, `movie_id`).
- Decisão de resolução em `4K`, `1080p` ou `none`.
- Timeout e tratamento de falhas do provider externo.
- Conversão de indisponibilidade externa para HTTP 503.
- Logs estruturados em JSON.
- Sanitização de campos sensíveis com `[REDACTED]`.
- Métricas RED expostas em `/metrics`.
- Healthchecks dos serviços na stack Docker Compose.
- Documentação OpenAPI/Swagger em `/docs`.

## 6. Como executar com Docker Compose
Subir a stack:

```bash
docker compose up --build -d
docker compose ps
```

Prometheus (disponível localmente):

- http://127.0.0.1:9090
- coleta métricas da API em `http://api:8000/metrics`
- sem persistência nesta etapa

Grafana (disponível localmente):

- http://127.0.0.1:3000
- credenciais padrão: `admin` / `admin`
- sobrescrita opcional com `GRAFANA_ADMIN_USER` e `GRAFANA_ADMIN_PASSWORD`
- datasource Prometheus provisionado automaticamente com `http://prometheus:9090`
- sem persistência, dashboards e alertas nesta etapa

Validar saúde e targets do Prometheus:

```bash
curl -i http://127.0.0.1:9090/-/healthy
curl -s http://127.0.0.1:9090/api/v1/targets
```

Logs da API principal:

```bash
docker compose logs api
docker compose logs grafana
```

Encerrar ambiente:

```bash
docker compose down
```

Testes rápidos com curl:

```bash
curl -i http://127.0.0.1:8000/health
curl -i "http://127.0.0.1:8000/stream/authorize?user_id=usr_99823&movie_id=mov_dune_part2"
curl -i http://127.0.0.1:8000/metrics
```

## 7. Como executar localmente
Instalação:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Terminal 1 (mock provider):

```bash
uvicorn mock_provider.main:app --host 127.0.0.1 --port 8001
```

Terminal 2 (API principal):

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## 8. Endpoints e exemplos
Endpoints atuais:
- GET `/health`
- GET `/stream/authorize`
- GET `/metrics`
- GET `/docs`
- GET `/openapi.json`

Exemplos:

```bash
curl -i http://127.0.0.1:8000/health
curl -i "http://127.0.0.1:8000/stream/authorize?user_id=usr_99823&movie_id=mov_dune_part2"
curl -i "http://127.0.0.1:8000/stream/authorize?user_id=usr_99823"
curl -i http://127.0.0.1:8000/metrics
curl -i http://127.0.0.1:8000/docs
curl -i http://127.0.0.1:8000/openapi.json
```

## 9. Observabilidade
Logs:
- JSON estruturado.
- Eventos de negócio da API e eventos de transporte do provider.
- Campos sensíveis redigidos com `[REDACTED]`.
- `drm_token` não é registrado nos logs.

Métricas RED:
- `http_requests_total`
- `http_request_errors_total`
- `http_request_duration_seconds`
- Labels: `method`, `endpoint`, `status_code`.
- Rotas desconhecidas normalizadas como `unmatched`.
- Sem `user_id`, `movie_id`, token DRM ou query string nas labels.

## 10. Testes
Executar:

```bash
python -m pytest -q
```

Resultado atual comprovado:
- 63 passed

## 11. Decisões e limitações
- Mock provider local para cenários determinísticos de integração.
- Sem banco de dados.
- Sem retry.
- Sem circuit breaker.
- Sem OpenTelemetry.
- Sem Loki e Tempo.
- Sem k6.

O `prometheus-client` expõe métricas no formato Prometheus em `/metrics`, o Prometheus Server faz a coleta básica e o Grafana recebe um datasource provisionado automaticamente. Nesta etapa não há persistência, dashboards nem regras de alerta.

## 12. Próximos passos
- OpenTelemetry.
- Stack LGTM.
- Dashboards Grafana.
- Teste de carga com k6.
