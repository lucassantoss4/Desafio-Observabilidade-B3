# Desafio Observabilidade B3 - Stream Authorization API

## 1. Titulo do projeto
Desafio Observabilidade B3 - API de autorizacao de streaming (fase inicial).

## 2. Objetivo
Implementar uma API HTTP minima em Python/FastAPI para o cenario de autorizacao de streaming.
Nesta fase, o foco e validar contrato de endpoint, entrada/saida e fluxo basico de execucao local.

## 3. Cenario escolhido
Cenario 2: Blockbuster Premiere Rush (Filmes e Streaming).

Endpoint principal do cenario:

- GET /stream/authorize?user_id={user_id}&movie_id={movie_id}

## 4. Estado atual do projeto
Implementado nesta branch:

- API minima com FastAPI
- Endpoint GET /health
- Endpoint GET /stream/authorize
- Validacao de query params (obrigatorios, sem string vazia, maximo 100 caracteres)
- Modelo de resposta com Pydantic
- OpenAPI/Swagger disponivel em /docs
- Script de smoke test em scripts/smoke-test.sh

Ainda nao implementado:

- Integracao externa simulada
- Resiliencia avancada (retry, circuit breaker etc.)
- Docker e Docker Compose
- OpenTelemetry
- Metricas Prometheus (/metrics)
- Logs estruturados JSON
- Loki, Tempo, Grafana, dashboard exportado
- k6

## 5. Tecnologias atuais
- Python 3
- FastAPI
- Uvicorn
- Pydantic

## 6. Estrutura de diretorios atual
```text
.
├── app
│   ├── __init__.py
│   ├── main.py
│   ├── models
│   │   ├── __init__.py
│   │   └── streaming.py
│   └── routes
│       ├── __init__.py
│       └── streaming.py
├── scripts
│   └── smoke-test.sh
├── requirements.txt
└── README.md
```

## 7. Pre-requisitos
- Linux (ou ambiente shell compativel com bash/sh)
- Python 3 com modulo venv habilitado
- curl

## 8. Como criar e ativar o ambiente virtual
No diretorio raiz do projeto:

```bash
python -m venv .venv
source .venv/bin/activate
```

## 9. Como instalar dependencias
Com o ambiente virtual ativo:

```bash
pip install -r requirements.txt
```

## 10. Como executar a API com Uvicorn
No diretorio raiz do projeto:

```bash
uvicorn app.main:app --reload
```

Servidor local padrao:

- http://127.0.0.1:8000

## 11. Endpoints disponiveis
- GET /health
- GET /stream/authorize

### Regras de validacao de /stream/authorize
- user_id: obrigatorio, nao vazio, maximo 100 caracteres
- movie_id: obrigatorio, nao vazio, maximo 100 caracteres

## 12. Exemplos individuais usando curl
### Health check
```bash
curl -i http://127.0.0.1:8000/health
```

### Autorizacao valida
```bash
curl -i "http://127.0.0.1:8000/stream/authorize?user_id=usr_99823&movie_id=mov_dune_part2"
```

### Parametro ausente (deve retornar 422)
```bash
curl -i "http://127.0.0.1:8000/stream/authorize?user_id=usr_99823"
```

### String vazia (deve retornar 422)
```bash
curl -i "http://127.0.0.1:8000/stream/authorize?user_id=&movie_id=mov_dune_part2"
```

## 13. Como acessar a documentacao Swagger
Com a API em execucao:

- http://127.0.0.1:8000/docs

OpenAPI JSON:

- http://127.0.0.1:8000/openapi.json

## 14. Como executar scripts/smoke-test.sh
Com a API em execucao e a partir da raiz do projeto:

```bash
bash scripts/smoke-test.sh
```

Opcional (para executar diretamente):

```bash
chmod +x scripts/smoke-test.sh
./scripts/smoke-test.sh
```

## 15. Resultados esperados dos testes
- /health retorna HTTP 200
- /stream/authorize com user_id e movie_id validos retorna HTTP 200 com JSON
- /stream/authorize sem movie_id retorna HTTP 422
- /stream/authorize com user_id vazio retorna HTTP 422
- /docs retorna HTTP 200
- /openapi.json contem /health e /stream/authorize

Testes automatizados (pytest):

```bash
python -m pytest -v
```

Resultado esperado:

- colecao dos testes da API
- execucao sem falhas (exemplo: 13 passed)

Resposta temporaria atual de /stream/authorize:

```json
{
  "user_id": "usr_99823",
  "movie_id": "mov_dune_part2",
  "authorized": true,
  "resolution": "4K",
  "drm_token": "mock-token-usr_99823-mov_dune_part2",
  "server_region": "sa-east-1"
}
```

## 16. Roadmap resumido das proximas fases
1. Integracao externa simulada para autorizacao
2. Tratamento de falhas da dependencia externa (sem crash da API)
3. Containerizacao com Docker e orquestracao com Docker Compose
4. Instrumentacao com OpenTelemetry (traces, logs correlacionados, metricas)
5. Exposicao de metricas RED em /metrics
6. Stack LGTM (Prometheus, Loki, Tempo, Grafana)
7. Dashboard Grafana exportado em JSON
8. Teste de carga com k6
