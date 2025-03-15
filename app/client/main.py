import asyncio
import sys
import logging
import signal

from client import WebSocketClient
from cli import InteractiveConsole
from config import DEFAULT_URI, LOG_LEVEL, LOG_FORMAT

logging.basicConfig(
    level=LOG_LEVEL,
    format=LOG_FORMAT
)
logger = logging.getLogger('websocket_client')


client = None

def handle_shutdown(signum, frame):
    logger.info(f"Sinal recebido {signum}, iniciando desligamento...")
    if client:
        client.running = False
        logger.info("Cliente está sendo encerrado...")

async def main():
    global client
    
    uri = DEFAULT_URI
    if len(sys.argv) > 1:
        uri = sys.argv[1]
    
    client = WebSocketClient(uri)
    cli = InteractiveConsole(client)
    
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
    
    success = await client.connect()
    if not success:
        print("Não foi possível conectar ao servidor. Tente novamente mais tarde.")
        return

    receive_task = asyncio.create_task(client.receive_messages())
    cli_task = asyncio.create_task(cli.run())

    await cli_task

    await client.disconnect()

    receive_task.cancel()
    
    try:
        await receive_task
    except asyncio.CancelledError:
        pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
        logger.info("Cliente encerrado.")
    except KeyboardInterrupt:
        print("\nCliente encerrado pelo usuário.")
    except Exception as e:
        logger.error(f"Erro não tratado no cliente: {str(e)}")
