FROM python:3.13-slim

# A imagem slim mantém a base mínima necessária para executar a API sem o peso
# de dependências extras, o que facilita a construção e a manutenção da imagem.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copiar primeiro o arquivo de dependências maximiza o cache do Docker e evita
# reinstalar pacotes sempre que o código da aplicação muda.
COPY requirements.txt ./requirements.txt

RUN python -m pip install --no-cache-dir -r requirements.txt

# O restante do código só entra depois da instalação para manter o processo de
# build previsível e reduzir a quantidade de camadas alteradas.
COPY . .

# Execução como usuário não root reduz os riscos de escalar privilégios dentro do
# container e é mais seguro para ambientes compartilhados.
RUN groupadd --system appgroup && useradd --system --gid appgroup --create-home --home-dir /home/appuser appuser \
    && chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

# Não usamos --reload porque o objetivo deste container é reproduzir a execução
# da aplicação em ambiente de produção, sem reinicialização automática e sem
# dependência do ciclo de desenvolvimento local.
# O healthcheck fica no compose.yaml para que cada serviço defina seu endpoint
# específico de monitoramento sem acoplar a regra de negócio à imagem.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
