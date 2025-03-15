"""
Implementação do cliente WebSocket.
"""
import asyncio
import json
import websockets
import logging
from typing import Optional, Dict, Any, Callable

logger = logging.getLogger('websocket_client.client')

class WebSocketClient:
    """Cliente WebSocket para conexão com o servidor"""
    
    def __init__(self, uri: str = "ws://localhost:8765"):
        """
        Inicializa o cliente WebSocket
        
        Args:
            uri: Endereço do servidor WebSocket
        """
        self.uri = uri
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.client_id: Optional[str] = None
        self.username: Optional[str] = None
        self.connected = False
        self.running = True
        self.current_time = ""
        
        # Dicionário para manipuladores de mensagens
        self.message_handlers: Dict[str, Callable] = {
            "welcome": self._handle_welcome,
            "time_update": self._handle_time_update,
            "fibonacci_result": self._handle_fibonacci_result,
            "username_updated": self._handle_username_updated,
            "error": self._handle_error
        }
    
    async def connect(self):
        """Estabelece conexão com o servidor WebSocket"""
        try:
            self.websocket = await websockets.connect(self.uri)
            self.connected = True
            logger.info(f"Conectado ao servidor: {self.uri}")
            return True
        except Exception as e:
            logger.error(f"Erro ao conectar: {str(e)}")
            return False
    
    async def disconnect(self):
        """Desconecta do servidor WebSocket"""
        if self.websocket and self.connected:
            await self.websocket.close()
            self.connected = False
            logger.info("Desconectado do servidor")
    
    async def send_message(self, message_data: dict):
        """Envia uma mensagem para o servidor"""
        if not self.connected or not self.websocket:
            logger.error("Não conectado ao servidor")
            return False
        
        try:
            message = json.dumps(message_data)
            await self.websocket.send(message)
            logger.info(f"Mensagem enviada: {message}")
            return True
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {str(e)}")
            return False
    
    async def calculate_fibonacci(self, n: int):
        """Solicita o cálculo de Fibonacci ao servidor"""
        return await self.send_message({"type": "fibonacci", "n": n})
    
    async def update_username(self, new_username: str):
        """Atualiza o nome de usuário no servidor"""
        return await self.send_message({"type": "update_username", "username": new_username})
    
    # Manipuladores de mensagens
    async def _handle_welcome(self, data: Dict[str, Any]):
        """Processa mensagem de boas-vindas"""
        self.client_id = data.get("client_id")
        print(f"\n{data.get('message')}")

    async def _handle_time_update(self, data: Dict[str, Any]):
        """Apenas armazena a hora do servidor sem exibir imediatamente"""
        self.current_time = data.get("time", "")

    async def _handle_fibonacci_result(self, data: Dict[str, Any]):
        """Processa resultado do cálculo de Fibonacci"""
        print(f"\nFibonacci({data.get('n')}) = {data.get('result')}")
    
    async def _handle_username_updated(self, data: Dict[str, Any]):
        """Processa atualização de nome de usuário"""
        self.username = data.get("username")
        print(f"\nNome de usuário atualizado para: {self.username}")
    
    async def _handle_error(self, data: Dict[str, Any]):
        """Processa mensagem de erro"""
        print(f"\nErro: {data.get('message', 'Erro desconhecido')}")

    async def _handle_unknown(self, data: Dict[str, Any]):
        """Processa mensagens de tipo desconhecido"""
        print(f"\nMensagem recebida: {data}")
    
    async def receive_messages(self):
        """Recebe e processa mensagens do servidor"""
        if not self.connected or not self.websocket:
            logger.error("Não conectado ao servidor")
            return
        
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    handler = self.message_handlers.get(data.get("type", ""), self._handle_unknown)
                    await handler(data)
                except json.JSONDecodeError:
                    logger.error(f"Mensagem inválida recebida: {message}")
                except Exception as e:
                    logger.error(f"Erro ao processar mensagem: {str(e)}")
        except websockets.exceptions.ConnectionClosed as e:
            logger.info(f"Conexão fechada: {e}")
            self.connected = False
            print("\nConexão com o servidor perdida.")
