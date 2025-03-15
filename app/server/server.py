import asyncio
import json
import websockets
import datetime
import logging
from typing import Dict

from database import (
    add_user_to_db, 
    remove_user_from_db, 
    update_user_activity, 
    update_username,
    close_connection
)
from fibonacci import calculate_fibonacci

logger = logging.getLogger('websocket_server.server')

class WebSocketServer:
    def __init__(self, host="localhost", port=8765):
        self.host = host
        self.port = port
        self.connected_clients: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.server = None
        self.running = True
        # Armazenar a última hora enviada para cada cliente
        self.last_time_sent = {}
    
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
            
            async for message in websocket:
                try:
                    data = json.loads(message)
                    logger.info(f"Mensagem recebida de {client_id}: {data}")
                    
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
            remove_user_from_db(client_id)
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
                        # Enviar apenas se a hora mudou desde a última vez
                        if client_id not in self.last_time_sent or self.last_time_sent[client_id] != current_time:
                            await websocket.send(message)
                            self.last_time_sent[client_id] = current_time
                    except websockets.exceptions.ConnectionClosed:
                        disconnected.append(client_id)
                
                for client_id in disconnected:
                    if client_id in self.connected_clients:
                        del self.connected_clients[client_id]
                    if client_id in self.last_time_sent:
                        del self.last_time_sent[client_id]
                    remove_user_from_db(client_id)
                    logger.info(f"Cliente {client_id} removido (conexão fechada durante broadcast).")
            
            # Manter intervalo de 1 segundo para atender ao requisito
            await asyncio.sleep(1)
    
    async def start(self):
        broadcast_task = asyncio.create_task(self.broadcast_time())

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
            try:
                await broadcast_task
            except asyncio.CancelledError:
                pass
            close_connection()