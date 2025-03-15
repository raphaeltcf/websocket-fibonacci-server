import asyncio
import sys
import logging
import signal
import atexit

from client import WebSocketClient
from cli import InteractiveConsole
from config import DEFAULT_URI, LOG_LEVEL, LOG_FORMAT

logging.basicConfig(
    level=LOG_LEVEL,
    format=LOG_FORMAT
)
logger = logging.getLogger('websocket_client')


client = None

def exit_handler():
    if client and client.connected:
        # Criar uma nova tarefa assíncrona que será executada em um novo loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(client.send_disconnect_signal())
            loop.run_until_complete(client.disconnect())
        except Exception as e:
            logger.error(f"Erro durante saída: {str(e)}")
        finally:
            loop.close()

atexit.register(exit_handler)

def handle_shutdown(signum, frame):
    logger.info(f"Sinal recebido {signum}, iniciando desligamento...")
    if client:
        client.running = False
        # Executar aqui uma desconexão rápida
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(client.send_disconnect_signal())
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
    
    # Registrar também o sinal SIGHUP (terminal fechado)
    if hasattr(signal, 'SIGHUP'):  # Não disponível no Windows
        signal.signal(signal.SIGHUP, handle_shutdown)
    
    success = await client.connect()
    if not success:
        print("Não foi possível conectar ao servidor. Tente novamente mais tarde.")
        return

    receive_task = asyncio.create_task(client.receive_messages())
    cli_task = asyncio.create_task(cli.run())

    try:
        await cli_task
    finally:
        # Garantir que tentamos enviar a desconexão mesmo se o cliente for encerrado abruptamente
        await client.send_disconnect_signal()
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
