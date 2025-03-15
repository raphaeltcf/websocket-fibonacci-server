#!/bin/bash

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}==================================================${NC}"
echo -e "${GREEN}  INICIANDO AMBIENTE WEBSOCKET${NC}"
echo -e "${BLUE}==================================================${NC}"

if ! docker info > /dev/null 2>&1; then
  echo -e "${RED}Docker não está rodando. Por favor, inicie o Docker e tente novamente.${NC}"
  exit 1
fi

if ! command -v docker compose &> /dev/null; then
  echo -e "${RED}docker compose não encontrado. Por favor, instale-o e tente novamente.${NC}"
  exit 1
fi

echo -e "${YELLOW}Verificando contêineres existentes...${NC}"
if docker ps -q --filter "name=websocket-" | grep -q .; then
  echo -e "${YELLOW}Parando contêineres existentes...${NC}"
  docker compose down
fi

echo -e "${YELLOW}Criando versão compatível do cliente para Docker...${NC}"

mkdir -p .docker_tmp

cp -r app .docker_tmp/

cat > Dockerfile.client <<EOF
FROM python:3.10

WORKDIR /core

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN apt-get update && \\
    apt-get install -y \\
    netcat-openbsd \\
    net-tools \\
    telnet \\
    && apt-get clean \\
    && rm -rf /var/lib/apt/lists/*

COPY app /core/app

ENV PYTHONUNBUFFERED=1
ENV TERM=xterm-256color

WORKDIR /core/app/client

CMD ["sh", "-c", "sleep infinity"]
EOF

cat > docker compose.yml.new <<EOF
version: "3.8"

services:
  websocket-server:
    build: .
    container_name: websocket-server
    networks:
      - websocket-network
    ports:
      - "8765:8765"
    depends_on:
      - websocket-mongodb
    environment:
      - MONGO_USER=admin
      - MONGO_PASSWORD=password
      - MONGO_DB=websocket_db
      - MONGO_HOST=websocket-mongodb
      - MONGO_PORT=27017
      - SERVER_HOST=0.0.0.0
      - SERVER_PORT=8765
    healthcheck:
      test:
        [
          "CMD-SHELL",
          "if netstat -an | grep 8765 > /dev/null; then exit 0; else exit 1; fi",
        ]
      interval: 5s
      timeout: 5s
      retries: 5
      start_period: 10s

  websocket-mongodb:
    image: mongo:latest
    container_name: websocket-mongodb
    networks:
      - websocket-network
    ports:
      - "27017:27017"
    environment:
      - MONGO_INITDB_ROOT_USERNAME=admin
      - MONGO_INITDB_ROOT_PASSWORD=password
      - MONGO_INITDB_DATABASE=websocket_db
    volumes:
      - mongodb_data:/data/db
    command: mongod --auth
    healthcheck:
      test: echo 'db.runCommand("ping").ok' | mongosh localhost:27017/admin -u admin -p password --quiet
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 10s

  websocket-client:
    build:
      context: .
      dockerfile: Dockerfile.client
    container_name: websocket-client
    networks:
      - websocket-network
    depends_on:
      websocket-server:
        condition: service_healthy
    stdin_open: true
    tty: true

networks:
  websocket-network:
    driver: bridge

volumes:
  mongodb_data:
EOF

cp docker compose.yml docker compose.yml.backup

mv docker compose.yml.new docker compose.yml

echo -e "${YELLOW}Iniciando serviços...${NC}"
docker compose up -d

echo -e "${YELLOW}Aguardando servidor WebSocket iniciar...${NC}"

MAX_RETRIES=30
RETRY_COUNT=0
SERVER_READY=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
  if docker ps --filter "name=websocket-server" --filter "health=healthy" --format "{{.Names}}" | grep -q "websocket-server"; then
    SERVER_READY=true
    break
  fi
  echo -e "${YELLOW}Aguardando servidor iniciar ($(($RETRY_COUNT + 1))/${MAX_RETRIES})...${NC}"
  RETRY_COUNT=$((RETRY_COUNT+1))
  sleep 2
done

if ! $SERVER_READY; then
  echo -e "${RED}O servidor não iniciou corretamente. Verifique os logs:${NC}"
  docker compose logs websocket-server
  echo -e "${RED}Encerrando...${NC}"
  docker compose down
  exit 1
fi

if ! docker ps -q --filter "name=websocket-client" | grep -q .; then
  echo -e "${RED}O cliente WebSocket não está rodando. Verifique os logs:${NC}"
  docker compose logs websocket-client
  echo -e "${YELLOW}Tentando iniciar o cliente...${NC}"
  docker compose up -d websocket-client
  
  sleep 5
  
  if ! docker ps -q --filter "name=websocket-client" | grep -q .; then
    echo -e "${RED}Não foi possível iniciar o cliente. Encerrando...${NC}"
    docker compose down
    exit 1
  fi
fi

echo -e "${GREEN}Ambiente WebSocket iniciado com sucesso!${NC}"
echo -e "${BLUE}==================================================${NC}"
echo -e "${GREEN}Servidor rodando em: ws://localhost:8765${NC}"
echo -e "${GREEN}MongoDB rodando em: localhost:27017${NC}"
echo -e "${BLUE}==================================================${NC}"

echo -e "${YELLOW}Conectando ao terminal interativo do cliente...${NC}"
echo -e "${BLUE}Para sair do cliente, digite 'sair' ou pressione Ctrl+C${NC}"
echo -e "${BLUE}==================================================${NC}"
sleep 2

echo -e "${YELLOW}Aplicando correções no código do cliente...${NC}"
docker exec websocket-client bash -c "grep -q 'send_disconnect_signal' /core/app/client/main.py && sed -i 's/await client\.send_disconnect_signal()//g' /core/app/client/main.py || echo 'Sem necessidade de correção'"

docker exec -it websocket-client python /core/app/client/main.py

echo -e "${YELLOW}Você saiu do terminal do cliente. Deseja parar todos os serviços? (s/n)${NC}"
read -r resposta

if [[ $resposta =~ ^[Ss]$ ]]; then
  echo -e "${YELLOW}Parando serviços...${NC}"
  docker compose down
  mv docker compose.yml.backup docker compose.yml
  echo -e "${GREEN}Serviços parados com sucesso!${NC}"
else
  echo -e "${GREEN}Os serviços continuam rodando em segundo plano.${NC}"
  echo -e "${YELLOW}Para parar os serviços mais tarde, execute:${NC} docker compose down"
  echo -e "${YELLOW}O arquivo docker compose.yml foi modificado. O backup está em docker compose.yml.backup${NC}"
fi

rm -rf .docker_tmp
rm -f Dockerfile.client

exit 0