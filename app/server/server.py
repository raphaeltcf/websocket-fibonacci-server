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
        self.last_time_sent = {}

    async def check_inactive_users(self):
        logger.info("Iniciando tarefa de verificação de usuários inativos")
        
        while self.running:
            try:
                users = get_all_connected_users()
                logger.info(f"Verificando inatividade: {len(users)} usuários online")
                
                for user in users:
                    last_active = user.get('last_active')
                    connected_at = user.get('connected_at')
                    user_id = user.get('id')
                    username = user.get('username')
                    
                    if last_active:
                        time_diff = datetime.datetime.now() - last_active
                        minutes_inactive = time_diff.total_seconds() / 60
                        logger.info(f"Usuário {username} ({user_id}) inativo por {minutes_inactive:.2f} minutos")
                
                inactive_count = mark_inactive_users_as_offline(5)
                logger.info(f"Verificação concluída: {inactive_count} usuários marcados como offline por inatividade")
            except Exception as e:
                logger.error(f"Erro ao verificar usuários inativos: {str(e)}")
            
            await asyncio.sleep(60)

    async def handle_list_users(self, websocket, client_id):
        try:
            users = get_all_connected_users()

            current_time = datetime.datetime.now()
            serializable_users = []
            
            for user in users:
                serializable_user = {}
                
                for key, value in user.items():
                    if isinstance(value, datetime.datetime):
                        serializable_user[key] = value.strftime("%Y-%m-%d %H:%M:%S")
                    else:
                        serializable_user[key] = value
                
                if 'connected_at' in user and user['connected_at']:
                    connected_time = current_time - user['connected_at']
                    hours, remainder = divmod(connected_time.total_seconds(), 3600)
                    minutes, seconds = divmod(remainder, 60)
                    serializable_user['online_time'] = f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
                else:
                    serializable_user['online_time'] = "Desconhecido"
                
                serializable_users.append(serializable_user)

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
            self._initialize_client(client_id, username, websocket)
            
            await self._send_welcome_message(websocket, client_id)
            await self._send_initial_time(websocket, client_id)
            
            await self._process_client_messages(websocket, client_id, username)
        
        except websockets.exceptions.ConnectionClosed as e:
            logger.info(f"Conexão fechada com {client_id}: {e}")
        
        finally:
            self._cleanup_client(client_id)

    def _initialize_client(self, client_id, username, websocket):
        self.connected_clients[client_id] = websocket
        add_user_to_db(client_id, username)
        logger.info(f"Novo cliente conectado: {client_id}")

    async def _send_welcome_message(self, websocket, client_id):
        await websocket.send(json.dumps({
            "type": "welcome",
            "message": f"Bem-vindo ao servidor WebSocket! Seu ID é {client_id}",
            "client_id": client_id
        }))

    async def _send_initial_time(self, websocket, client_id):
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await websocket.send(json.dumps({
            "type": "time_update",
            "time": current_time
        }))
        self.last_time_sent[client_id] = current_time
        update_user_activity(client_id)

    async def _process_client_messages(self, websocket, client_id, username):
        async for message in websocket:
            try:
                data = json.loads(message)
                logger.info(f"Mensagem recebida de {client_id}: {data}")
                update_user_activity(client_id)
                
                await self._handle_message_by_type(websocket, client_id, username, data)
                
            except json.JSONDecodeError:
                await self._send_error(websocket, f"Mensagem inválida recebida de {client_id}: {message}", 
                                    "Formato JSON inválido.")
            
            except Exception as e:
                await self._send_error(websocket, f"Erro ao processar mensagem de {client_id}: {str(e)}",
                                    f"Erro ao processar mensagem: {str(e)}")

    async def _handle_message_by_type(self, websocket, client_id, username, data):
        msg_type = data.get("type", "")
        
        if msg_type == "fibonacci":
            await self._handle_fibonacci_request(websocket, client_id, data)
        
        elif msg_type == "update_username":
            await self._handle_username_update(websocket, client_id, data, username)
        
        elif msg_type == "list_users":
            await self.handle_list_users(websocket, client_id)

    async def _handle_fibonacci_request(self, websocket, client_id, data):
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
            await self._send_error(websocket, f"Erro de Fibonacci para {client_id}: {str(e)}",
                                f"Erro ao calcular Fibonacci: {str(e)}")

    async def _handle_username_update(self, websocket, client_id, data, current_username):
        new_username = data.get("username", current_username)
        username = update_username(client_id, new_username)
        
        if username:
            await websocket.send(json.dumps({
                "type": "username_updated",
                "username": username
            }))
        else:
            await self._send_error(websocket, f"Falha ao atualizar nome para {client_id}",
                                "Falha ao atualizar nome de usuário")

    async def _send_error(self, websocket, log_message, client_message):
        logger.error(log_message)
        await websocket.send(json.dumps({
            "type": "error",
            "message": client_message
        }))

    def _cleanup_client(self, client_id):
        if client_id in self.connected_clients:
            del self.connected_clients[client_id]
        if client_id in self.last_time_sent:
            del self.last_time_sent[client_id]
        set_user_offline(client_id)
        logger.info(f"Cliente {client_id} desconectado.")
    
    async def broadcast_time(self):
        while self.running:
            if self.connected_clients:
                current_time = self._get_formatted_current_time()
                message = self._create_time_update_message(current_time)
                disconnected = await self._send_time_updates(current_time, message)
                self._handle_disconnected_clients(disconnected)
            
            await asyncio.sleep(1)

    def _get_formatted_current_time(self):
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _create_time_update_message(self, current_time):
        return json.dumps({
            "type": "time_update",
            "time": current_time
        })

    async def _send_time_updates(self, current_time, message):
        disconnected = []
        
        for client_id, websocket in self.connected_clients.items():
            try:
                if self._should_send_update(client_id, current_time):
                    await websocket.send(message)
                    self.last_time_sent[client_id] = current_time
                    update_user_activity(client_id)
            except websockets.exceptions.ConnectionClosed:
                disconnected.append(client_id)
        
        return disconnected

    def _should_send_update(self, client_id, current_time):
        return (client_id not in self.last_time_sent or 
                self.last_time_sent[client_id] != current_time)

    def _handle_disconnected_clients(self, disconnected):
        for client_id in disconnected:
            self._remove_client(client_id)
            set_user_offline(client_id)
            logger.info(f"Cliente {client_id} marcado como offline (conexão fechada durante broadcast).")

    def _remove_client(self, client_id):
        if client_id in self.connected_clients:
            del self.connected_clients[client_id]
        
        if client_id in self.last_time_sent:
            del self.last_time_sent[client_id]
    async def start(self):
        broadcast_task = asyncio.create_task(self.broadcast_time())
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
            inactive_check_task.cancel() 
            try:
                await broadcast_task
                await inactive_check_task
            except asyncio.CancelledError:
                pass
            close_connection()