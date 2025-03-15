import asyncio
import json
import websockets
import datetime
import logging
from typing import Dict

from database import (
    add_user_to_db, 
    set_user_offline,
    update_user_activity, 
    update_username,
    get_all_users,
    get_all_connected_users,
    mark_inactive_users_as_offline,
    close_connection
)
from fibonacci import calculate_fibonacci

logger = logging.getLogger('websocket_server.server')

# Função auxiliar para serialização de datetime para JSON
def datetime_serializer(obj):
    if isinstance(obj, datetime.datetime):
        return obj.strftime("%Y-%m-%d %H:%M:%S")
    raise TypeError(f"Tipo não serializável: {type(obj)}")

class WebSocketServer:
    def __init__(self, host="localhost", port=8765):
        self.host = host
        self.port = port
        self.connected_clients: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.server = None
        self.running = True
        # Armazenar a última hora enviada para cada cliente
        self.last_time_sent = {}

    async def check_inactive_users(self):
        """Verifica periodicamente por usuários inativos."""
        logger.info("Iniciando tarefa de verificação de usuários inativos")
        
        while self.running:
            try:
                # Verificar quantos usuários estão marcados como online
                users = get_all_connected_users()
                logger.info(f"Verificando inatividade: {len(users)} usuários online")
                
                # Log dos últimos tempos de atividade
                for user in users:
                    last_active = user.get('last_active')
                    connected_at = user.get('connected_at')
                    user_id = user.get('id')
                    username = user.get('username')
                    
                    if last_active:
                        time_diff = datetime.datetime.now() - last_active
                        minutes_inactive = time_diff.total_seconds() / 60
                        logger.info(f"Usuário {username} ({user_id}) inativo por {minutes_inactive:.2f} minutos")
                
                # Usando 5 minutos como timeout
                inactive_count = mark_inactive_users_as_offline(5)
                logger.info(f"Verificação concluída: {inactive_count} usuários marcados como offline por inatividade")
            except Exception as e:
                logger.error(f"Erro ao verificar usuários inativos: {str(e)}")
            
            # Verificar a cada 1 minuto
            await asyncio.sleep(60)

    async def handle_list_users(self, websocket, client_id):
        try:
            # Obter usuários conectados
            users = get_all_connected_users()

            # Preparar dados para exibir o tempo online
            current_time = datetime.datetime.now()
            serializable_users = []
            
            for user in users:
                # Criar uma cópia do usuário que será serializada
                serializable_user = {}
                
                for key, value in user.items():
                    # Converter objetos datetime para string
                    if isinstance(value, datetime.datetime):
                        serializable_user[key] = value.strftime("%Y-%m-%d %H:%M:%S")
                    else:
                        serializable_user[key] = value
                
                # Calcular tempo online
                if 'connected_at' in user and user['connected_at']:
                    connected_time = current_time - user['connected_at']
                    hours, remainder = divmod(connected_time.total_seconds(), 3600)
                    minutes, seconds = divmod(remainder, 60)
                    serializable_user['online_time'] = f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
                else:
                    serializable_user['online_time'] = "Desconhecido"
                
                serializable_users.append(serializable_user)

            # Enviar mensagem com os dados convertidos
            await websocket.send(json.dumps({
                "type": "users_list",
                "users": serializable_users
            }))
            logger.info(f"Listagem de usuários enviada para {client_id}")
        except Exception as e:
            logger.error(f"Erro ao enviar listagem de usuários: {str(e)}")
            await websocket.send(json.dumps({
                "type": "error",
                "message": f"Erro ao enviar listagem de usuários: {str(e)}"
            }))
    
    async def handle_client(self, websocket):
        client_id = f"client_{id(websocket)}"
        username = f"user_{client_id}"
        
        try:
            self.connected_clients[client_id] = websocket
            add_user_to_db(client_id, username)
            logger.info(f"Novo cliente conectado: {client_id}")
            
            await websocket.send(json.dumps({
                "type": "welcome",
                "message": f"Bem-vindo ao servidor WebSocket! Seu ID é {client_id}",
                "client_id": client_id
            }))
            
            # Enviar hora atual inicial para o cliente
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            await websocket.send(json.dumps({
                "type": "time_update",
                "time": current_time
            }))
            self.last_time_sent[client_id] = current_time
            # Atualizar atividade do usuário quando o cliente se conecta
            update_user_activity(client_id)
            
            async for message in websocket:
                try:
                    data = json.loads(message)
                    logger.info(f"Mensagem recebida de {client_id}: {data}")
                    
                    # Atualizar atividade do usuário a cada mensagem recebida
                    update_user_activity(client_id)
                    
                    if data.get("type") == "fibonacci":
                        try:
                            n = int(data.get("n", 0))
                            result = calculate_fibonacci(n)
                            await websocket.send(json.dumps({
                                "type": "fibonacci_result",
                                "n": n,
                                "result": result
                            }))
                            logger.info(f"Fibonacci({n}) = {result} calculado para {client_id}")
                        except (ValueError, TypeError) as e:
                            await websocket.send(json.dumps({
                                "type": "error",
                                "message": f"Erro ao calcular Fibonacci: {str(e)}"
                            }))
                    
                    elif data.get("type") == "update_username":
                        new_username = data.get("username", username)
                        username = update_username(client_id, new_username)
                        
                        if username:
                            await websocket.send(json.dumps({
                                "type": "username_updated",
                                "username": username
                            }))
                        else:
                            await websocket.send(json.dumps({
                                "type": "error",
                                "message": "Falha ao atualizar nome de usuário"
                            }))

                    elif data.get("type") == "list_users":
                        await self.handle_list_users(websocket, client_id)
                    
                except json.JSONDecodeError:
                    logger.error(f"Mensagem inválida recebida de {client_id}: {message}")
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "Formato JSON inválido."
                    }))
                
                except Exception as e:
                    logger.error(f"Erro ao processar mensagem de {client_id}: {str(e)}")
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": f"Erro ao processar mensagem: {str(e)}"
                    }))
        
        except websockets.exceptions.ConnectionClosed as e:
            logger.info(f"Conexão fechada com {client_id}: {e}")
        
        finally:
            if client_id in self.connected_clients:
                del self.connected_clients[client_id]
            if client_id in self.last_time_sent:
                del self.last_time_sent[client_id]
            set_user_offline(client_id)
            logger.info(f"Cliente {client_id} desconectado.")
    
    async def broadcast_time(self):
        while self.running:
            if self.connected_clients:
                current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                message = json.dumps({
                    "type": "time_update",
                    "time": current_time
                })
                
                disconnected = []
                for client_id, websocket in self.connected_clients.items():
                    try:
                        if client_id not in self.last_time_sent or self.last_time_sent[client_id] != current_time:
                            await websocket.send(message)
                            self.last_time_sent[client_id] = current_time
                            # Atualizar atividade do usuário ao receber atualização de hora
                            update_user_activity(client_id)
                    except websockets.exceptions.ConnectionClosed:
                        disconnected.append(client_id)
                
                for client_id in disconnected:
                    if client_id in self.connected_clients:
                        del self.connected_clients[client_id]
                    if client_id in self.last_time_sent:
                        del self.last_time_sent[client_id]
                    set_user_offline(client_id)
                    logger.info(f"Cliente {client_id} marcado como offline (conexão fechada durante broadcast).")
            
            # Manter intervalo de 1 segundo para atender ao requisito
            await asyncio.sleep(1)
    
    async def start(self):
        broadcast_task = asyncio.create_task(self.broadcast_time())
        # Adicionar a nova tarefa de verificação de inatividade
        inactive_check_task = asyncio.create_task(self.check_inactive_users())

        self.server = await websockets.serve(
            self.handle_client, 
            self.host, 
            self.port
        )
        
        logger.info(f"Servidor WebSocket iniciado em ws://{self.host}:{self.port}")
        
        try:
            await self.server.wait_closed()
        except Exception as e:
            logger.error(f"Erro no servidor: {str(e)}")
        finally:
            self.running = False
            broadcast_task.cancel()
            inactive_check_task.cancel()  # Cancelar a tarefa de verificação
            try:
                await broadcast_task
                await inactive_check_task
            except asyncio.CancelledError:
                pass
            close_connection()