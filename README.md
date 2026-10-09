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
- Logs estruturados JSON
- Loki, Tempo, Grafana, dashboard exportado
- k6

## Metricas RED (fase atual)
A API principal expoe metricas RED minimas para acompanhar volume, erros e duracao das requisicoes HTTP sem adicionar alta cardinalidade.

Endpoint de metricas:

- GET /metrics

Metricas publicadas:

- `http_requests_total`
- `http_request_errors_total`
- `http_request_duration_seconds`

Labels utilizadas:

- `method`
- `endpoint`
- `status_code`

Labels deliberadamente evitadas:

- `user_id`
- `movie_id`
- `drm_token`
- query string completa
- URL completa
- credenciais

Nesta etapa, Prometheus e Grafana ainda nao foram adicionados ao Docker Compose.

## 5. Tecnologias atuais
- Python 3
- FastAPI
- Uvicorn
- Pydantic

## Logs estruturados em JSON
A infraestrutura utiliza a biblioteca padrao `logging` do Python e foi mantida como camada central de serializacao e sanitizacao. A API principal e o cliente do provider agora estao instrumentados, mas o formatter central continua sendo o unico ponto em que a estrutura JSON e a remocao de dados sensiveis sao implementadas.

### Separacao de responsabilidades
- O `ProviderClient` registra a comunicacao HTTP com a dependencia externa;
- a rota registra as decisoes de negocio da aplicacao;
- o formatter central registra a estrutura JSON final e sanitiza campos sensiveis;
- nao ha middleware, request_id artificial, trace_id, span_id, OpenTelemetry nem Loki nesta fase.

### Eventos da API
A rota `/stream/authorize` agora produz eventos de negocio para representar o ciclo de autorizacao:

- `stream_authorization_started`
- `stream_authorization_completed`
- `stream_authorization_degraded`

Esses eventos incluem campos como:

- `user_id`;
- `movie_id`;
- `authorized`;
- `resolution`;
- `server_region`;
- `latency_ms`;
- `reason` (quando aplicavel).

### Eventos do provider
O cliente HTTP registra o ciclo de transporte do provider:

- `provider_request_started`
- `provider_request_completed`
- `provider_request_failed`

Esses eventos incluem campos como:

- `provider_mode`;
- `provider_status_code`;
- `server_region`;
- `latency_ms`;
- `error_type`;
- `reason` (quando aplicavel, em contexto da rota).

### Degradacao de qualidade
Quando a autorizacao continua valida, mas a resolucao cai para um nivel funcional, o evento `stream_authorization_degraded` e emitido. Os motivos atuais sao:

- `insufficient_bandwidth`;
- `high_server_load`.

Se ambos os fatores ocorrerem ao mesmo tempo, a representacao continua estavel e estruturada, com a informacao registrada de forma previsivel em `reason` e sem duplicacao de campos arbitrarios.

Assinatura inativa continua sendo tratada como decisao de negocio e nao como degradacao tecnica:

- `authorized` retorna `false`;
- `resolution` retorna `none`;
- o evento `stream_authorization_degraded` nao e emitido.

### Medicao de latencia
A latencia e medida com `time.perf_counter()`, que e usado para calcular `latency_ms` sem depender de `datetime.now()`. A medicao e aplicada em dois niveis:

- no `ProviderClient`, para observar a duracao da chamada externa ao provider;
- na rota, para observar o tempo total do fluxo de autorizacao da API.

`latency_ms` permanece numerico e representa valores em milissegundos, com ponto flutuante quando necessario.

### Falhas externas esperadas
Quando a dependencia externa falha por timeout, conexao ou resposta HTTP com erro, a aplicacao registra o evento `provider_request_failed` com os campos:

- `error_type`;
- `provider_mode`;
- `latency_ms`;
- `provider_status_code`, quando aplicavel.

A resposta da API continua preservando HTTP 503 para indisponibilidade temporaria, sem expor stack trace ou detalhes internos do provider em resposta publica.

### Campos e seguranca
Cada evento JSON inclui obrigatoriamente:

- `timestamp` em UTC no formato ISO 8601;
- `level`;
- `service`;
- `event`;
- `message`.

Campos adicionais preservam seus tipos JSON, incluindo boolean, inteiro, float, null e string. Campos sensiveis conhecidos sao substituidos por `[REDACTED]`.

Campos atualmente protegidos:

- `authorization`;
- `cookie`;
- `password`;
- `secret`;
- `access_token`;
- `refresh_token`;
- `drm_token`;
- `api_key`.

A comparacao dos nomes nao diferencia maiusculas e minusculas. Dicionarios aninhados tambem sao sanitizados. Headers, cookies, variaveis de ambiente e objetos completos de request nao sao coletados automaticamente.

Nao sao registrados:

- `drm_token`;
- `headers`;
- `authorization`;
- `cookies`;
- variaveis de ambiente completas;
- corpo integral do provider;
- credenciais.

### Correlacao distribuida e integrações futuras
Ainda nao existem:

- `request_id` artificial;
- `trace_id`;
- `span_id`;
- OpenTelemetry integrado;
- Loki integrado.

A ausencia desses campos e intencional: a aplicacao nao cria correlação distribuida artificial, nem integra stacks de observabilidade externas nesta fase.

### Exemplo de sucesso
```json
{
  "timestamp": "2026-10-08T19:50:51.541Z",
  "level": "INFO",
  "service": "stream-authorization-api",
  "event": "stream_authorization_completed",
  "message": "stream authorization completed",
  "user_id": "usr_99823",
  "movie_id": "mov_dune_part2",
  "authorized": true,
  "resolution": "4K",
  "server_region": "sa-east-1",
  "latency_ms": 26.19
}
```

Este exemplo representa o fluxo principal de sucesso, com a rota registrando a decisao de negocio e o cliente do provider registrando a comunicacao externa antes da resposta final da API.

## 6. Estrutura de diretorios atual
```text
.
├── app
│   ├── __init__.py
│   ├── main.py
│   ├── schemas.py
│   ├── provider.py
│   └── logging.py
├── mock_provider
│   ├── __init__.py
│   └── main.py
├── scripts
│   └── smoke-test.sh
├── requirements.txt
└── README.md
```

### Organizacao dos modulos
- `app/main.py`: cria a aplicacao FastAPI, expoe os endpoints `GET /health` e `GET /stream/authorize`, aplica a regra de autorizacao, converte falhas externas esperadas para HTTP 503 e registra eventos estruturados de negocio.
- `app/schemas.py`: concentra os contratos Pydantic da API principal e da resposta do provider externo.
- `app/provider.py`: concentra a comunicacao HTTP com o provider, incluindo timeout, configuracao por variaveis de ambiente e logs de transporte.
- `app/logging.py`: centraliza formatter JSON, configuracao de logging e sanitizacao recursiva de campos sensiveis com redacao para `[REDACTED]`.
- `mock_provider/main.py`: implementa o servico externo simulado com modos `success`, `slow` e `error`.

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
- GET /metrics

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

## 16. Integracao do provider de validacao externa

A API principal agora consulta o mock provider antes de decidir a resposta final de `/stream/authorize`. O cliente HTTP acessa a dependencia externa em modo configurado para obter e validar fatores simulados como assinatura, banda e carga do servidor.

A regra de negocio continua sendo aplicada pela API principal, que decide `authorized` e `resolution` com base no retorno do provider. O mock provider continua isolado e a aplicacao converte falhas especificas do cliente HTTP em erro 503 para manter a API principal ativa.

### Variaveis de ambiente

```bash
export MOCK_PROVIDER_URL=http://127.0.0.1:8001
export MOCK_PROVIDER_MODE=success
export PROVIDER_TIMEOUT_SECONDS=1.0
```

- `MOCK_PROVIDER_MODE`: define o comportamento simulado da dependencia externa. Os modos suportados nesta demonstracao sao `success`, `slow` e `error`.
- `MOCK_PROVIDER_MODE` tem valor padrao `success`.
- `PROVIDER_TIMEOUT_SECONDS`: define o tempo maximo de espera da dependencia externa. O valor padrao recomendado e `1.0` segundo.
- `MOCK_PROVIDER_URL`: endereco do mock provider; se nao definido, o cliente usa `http://127.0.0.1:8001`.

### Comportamento de falhas externas

A aplicacao captura somente excecoes especificas do `httpx` para converter indisponibilidade temporaria em resposta HTTP 503 e JSON controlado:

```json
{
  "detail": "External validation service unavailable"
}
```

Esse comportamento foi mantido simples e deliberado: nao ha retry, fallback nem circuit breaker nesta etapa. O objetivo e preservar a API principal funcionando mesmo quando a dependencia externa falha ou responde com erro de rede ou de status.

### Como executar os servicos para teste manual

Terminal 1 - API principal:

```bash
uvicorn app.main:app --reload --port 8000
```

Terminal 2 - Mock provider:

```bash
uvicorn mock_provider.main:app --reload --port 8001
```

Opcionalmente, para testar cenarios de lentidao ou falha de dependencia:

```bash
export MOCK_PROVIDER_MODE=slow
export MOCK_PROVIDER_MODE=error
```

### Exemplo de consulta manual

```bash
curl -i "http://127.0.0.1:8000/stream/authorize?user_id=usr_99823&movie_id=mov_dune_part2"
```

### Comandos de demonstracao manual

Sucesso:

```bash
export MOCK_PROVIDER_MODE=success
curl -i "http://127.0.0.1:8000/stream/authorize?user_id=usr_99823&movie_id=mov_dune_part2"
```

Atraso:

```bash
export MOCK_PROVIDER_MODE=slow
curl -i "http://127.0.0.1:8000/stream/authorize?user_id=usr_99823&movie_id=mov_dune_part2"
```

Erro externo:

```bash
export MOCK_PROVIDER_MODE=error
curl -i "http://127.0.0.1:8000/stream/authorize?user_id=usr_99823&movie_id=mov_dune_part2"
```

Em todos os cenarios de falha externa, a resposta publica e a esperada:

```json
{
  "detail": "External validation service unavailable"
}
```

### Testes automatizados

```bash
python -m pytest -v
```

Resultado esperado nesta etapa:

- 36 testes coletados
- 36 aprovados

## 17. Containerizacao da API principal

Objetivo da imagem: empacotar a API principal em um container reutilizavel, com as mesmas dependencias e versao do Python do projeto, e preparar a base para a orquestracao futura com Docker Compose.

### Build da imagem

```bash
docker build -t desafio-observabilidade-b3:local .
```

### Executar a API principal

```bash
docker run --rm \
  --name desafio-observabilidade-api-validation \
  -p 8000:8000 \
  desafio-observabilidade-b3:local
```

### Validar o endpoint /health

```bash
curl -i http://127.0.0.1:8000/health
```

O mock provider sera executado pelo Compose no proximo incremento.
Ainda nao existe um arquivo compose.yaml nesta etapa.
A stack de observabilidade ainda nao foi adicionada.

## 18. Orquestracao basica com Docker Compose

### Subir os dois servicos

```bash
docker compose up --build -d
```

### Verificar os servicos em execucao

```bash
docker compose ps
```

### Health check da API principal

```bash
curl -i http://127.0.0.1:8000/health
```

### Autorizacao via API principal

```bash
curl -i \
  "http://127.0.0.1:8000/stream/authorize?user_id=usr_99823&movie_id=mov_dune_part2"
```

### Visualizar logs

```bash
docker compose logs api
docker compose logs mock-provider
```

### Encerrar o ambiente

```bash
docker compose down
```

### Healthchecks e dependencia da API

Os healthchecks validam a resposta real de cada servico dentro do proprio container usando Python e a biblioteca padrao do stdlib, sem depender de ferramentas do sistema. A API aguarda o mock provider ficar saudável antes de continuar a inicializacao, usando `depends_on` com `condition: service_healthy` para evitar que a aplicacao comece antes da dependencia externa responder corretamente.

Em `docker compose ps`, o estado `healthy` indica que o servico respondeu ao healthcheck com sucesso. Esse estado e diferente de apenas o processo estar em execucao, porque um container pode estar rodando mesmo sem responder corretamente ao endpoint de monitoramento.

A API acessa o provider via `http://mock-provider:8001` dentro da rede interna do Compose. Esse nome do servico e usado em vez de `localhost` porque a API precisa resolver o outro container da mesma pilha, nao o proprio host. O healthcheck do mock provider utiliza parametros validos para a rota `/validate`, e a observabilidade ainda sera adicionada em uma fase posterior.

## 19. Roadmap resumido das proximas fases
1. Tratamento de falhas da dependencia externa (timeout, retry, fallback e 503)
2. Containerizacao com Docker e orquestracao com Docker Compose
3. Instrumentacao com OpenTelemetry (traces, logs correlacionados, metricas)
4. Exposicao de metricas RED em /metrics
5. Stack LGTM (Prometheus, Loki, Tempo, Grafana)
6. Dashboard Grafana exportado em JSON
7. Teste de carga com k6
