import asyncio
import logging
import signal

from server import WebSocketServer
from database import init_database
from config import SERVER_HOST, SERVER_PORT, LOG_LEVEL, LOG_FORMAT

logging.basicConfig(
    level=LOG_LEVEL,
    format=LOG_FORMAT
)

logger = logging.getLogger('websocket_server')

server = None

def handle_shutdown(signum, frame):
    logger.info(f"Sinal recebido {signum}, iniciando desligamento gracioso...")
    if server and hasattr(server, 'server') and server.server:
        server.running = False
        server.server.close()
        logger.info("Servidor está sendo encerrado...")

async def main():
    global server

    try:
        init_database()
    except Exception as e:
        logger.error(f"Falha ao inicializar o banco de dados: {str(e)}")
        return

    server = WebSocketServer(host=SERVER_HOST, port=SERVER_PORT)

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
    
    try:
        await server.start()
    except Exception as e:
        logger.error(f"Erro ao iniciar o servidor: {str(e)}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
        logger.info("Servidor encerrado.")
    except KeyboardInterrupt:
        logger.info("Servidor encerrado pelo usuário.")
    except Exception as e:
        logger.error(f"Erro não tratado no servidor: {str(e)}")