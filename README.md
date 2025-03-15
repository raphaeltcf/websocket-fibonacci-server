# 🧦 WebSocket Fibonacci

Um cliente-servidor WebSocket em Python que permite cálculos de Fibonacci e troca de mensagens em tempo real entre múltiplos usuários. Desenvolvido com asyncio para operações assíncronas, MongoDB para persistência de dados e containerizado com Docker para fácil implantação e execução.

*******
Tabelas de conteúdo 
 1. [Pré requisitos](#prerequisitos)
 2. [Colocando o WebSocket para funcionar:](#funcionando)
 3. [Features](#features)
 4. [Feito Utilizando](#built)


*******
<div id='prerequisitos'/>  

## 🚀 Começo

Estas instruções permitirão que você obtenha uma cópia de trabalho do projeto em sua máquina local para fins de desenvolvimento e teste.

### 📋 Pré-requisitos

Antes de começar, você precisará ter as seguintes ferramentas instaladas em sua máquina:
- [Git](https://git-scm.com)
- [MongoDB](https://www.mongodb.com/)
- [Python](https://www.python.org/) 
- [Docker](https://www.docker.com/)

- Acesso às portas 8765 (para o servidor WebSocket) e 27017 (para o MongoDB) 
- Aproximadamente 1GB de espaço livre em disco para os containers e volume do MongoDB
- Renomear o arquivo .env.example para .env e configurar as variáveis de ambiente necessárias

Também é bom ter um editor para trabalhar com o código como [VSCode](https://code.visualstudio.com/)

*******
<div id='funcionando'/>  

### 🎲 Colocando o WebSocket para funcionar:

```bash
# Clone o repositorio
$ git clone https://github.com/raphaeltcf/websocket-fibonacci-server
```

### No Docker
```bash
# Acesse a pasta do projeto em terminal/cmd
$ cd websocket-fibonacci-server

# Build os containers
$ docker compose build --no-cache     

# Inicie os containers 
$ docker compose up -d          

# Acesse a aplicação 
$ docker exec -it websocket-client python /core/app/client/main.py  


```
### No .sh

```bash
# Acesse a pasta do projeto em terminal/cmd
$ cd websocket-fibonacci-server


# Crie o comando 
$ chmod +x start.sh  

# Acesse a aplicação
$ ./start.sh                            

```

*******
<div id='features'/>  

### ✅ Features

- [x] Conexão em tempo real via WebSocket (client e servidor)
- [x] Suporte a múltiplas conexões simultâneas de clientes
- [x] Broadcast automático de data e hora para todos os clientes a cada segundo
- [x] Persistência de usuários conectados em MongoDB
- [x] Atualização do banco de dados em eventos de conexão/desconexão
- [x] Detecção automática de usuários inativos
- [x] Cálculo de sequências de Fibonacci via comando remoto
- [x] Resposta individual ao solicitante do cálculo de Fibonacci
- [x] Interface de linha de comando interativa com histórico
- [x] Navegação por setas no histórico de comandos
- [x] Atualização de nome de usuário em tempo real
- [x] Listagem de usuários conectados com tempo online
- [x] Tratamento avançado de erros e desconexões
- [x] Programação assíncrona com Python asyncio
- [x] Script shell (start.sh) para inicialização automatizada do ambiente
- [x] Arquitetura cliente-servidor
- [x] Containerização com Docker (Dockerfile customizado)
- [x] Orquestração de múltiplos serviços com Docker Compose
- [x] Banco de dados MongoDB para persistência de dados
 
*******
<div id='built'/>  

## 🛠️ Feito utilizando
<img src="https://icongr.am/devicon/python-original.svg?size=128&color=currentColor" width="40" height="40" /> <img src="https://icongr.am/devicon/mongodb-original.svg?size=128&color=currentColor" width="40" height="40" /> <img src="https://icongr.am/devicon/git-original.svg?size=128&color=currentColor" width="40" height="40" /> <img src="https://icongr.am/devicon/docker-original.svg?size=128&color=currentColor" width="40" height="40" /> 
          
          

