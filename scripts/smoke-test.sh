#!/usr/bin/env bash
set -euo pipefail

# Aplicação saudável
curl -i http://127.0.0.1:8000/health

# Autorização válida
curl -i \
  "http://127.0.0.1:8000/stream/authorize?user_id=usr_99823&movie_id=mov_dune_part2"

# movie_id ausente
curl -i \
  "http://127.0.0.1:8000/stream/authorize?user_id=usr_99823"

# user_id vazio
curl -i \
  "http://127.0.0.1:8000/stream/authorize?user_id=&movie_id=mov_dune_part2"

# Documentação
curl -I http://127.0.0.1:8000/docs

# Especificação OpenAPI
curl -s http://127.0.0.1:8000/openapi.json | grep -E '"/health"|"/stream/authorize"'