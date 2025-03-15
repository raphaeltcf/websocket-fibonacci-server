import asyncio
import logging
import os
import sys
import termios
import tty
import select
import time
from typing import List, Dict, Callable, Any

logger = logging.getLogger('websocket_client.cli')

class Command:
    def __init__(self, name, handler, description, usage=None):
        self.name = name
        self.handler = handler
        self.description = description
        self.usage = usage or name

class InteractiveConsole:
    
    def __init__(self, client):
        self.client = client
        self.commands: Dict[str, Command] = {}
        self.command_history = []
        self.history_index = -1
        self.last_input_time = 0
        self.in_command_execution = False

        self._register_default_commands()
    
    def _register_default_commands(self):
        self.register_command(
            "ajuda", 
            self.show_help, 
            "Mostra a lista de comandos disponíveis"
        )
        
        self.register_command(
            "fib", 
            self.fibonacci, 
            "Calcula Fibonacci(n)", 
            "fib <número>"
        )
        
        self.register_command(
            "nome", 
            self.update_username, 
            "Atualiza seu nome de usuário", 
            "nome <novo_nome>"
        )
        
        self.register_command(
            "status", 
            self.show_status, 
            "Verifica status da conexão"
        )
        
        self.register_command(
            "hora", 
            self.show_time, 
            "Mostra a hora atual do servidor"
        )
        
        self.register_command(
            "reconectar", 
            self.reconnect, 
            "Reconecta ao servidor"
        )
        
        self.register_command(
            "sair", 
            self.exit, 
            "Encerra o cliente"
        )
        
        self.register_command(
            "limpar", 
            self.clear_screen, 
            "Limpa a tela"
        )
    
    def register_command(self, name: str, handler: Callable, description: str, usage: str = None):
        self.commands[name] = Command(name, handler, description, usage)
    
    def _clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')
    
    async def show_help(self, args: List[str] = None):
        print("\nComandos disponíveis:")
        
        for name in sorted(self.commands.keys()):
            command = self.commands[name]
            if command.usage:
                print(f"  {command.usage:12} - {command.description}")
            else:
                print(f"  {command.name:12} - {command.description}")
        
        return True
    
    async def fibonacci(self, args: List[str]):
        if not args:
            print("\nUso correto: fib <número>")
            return True
        
        try:
            n = int(args[0])
            await self.client.calculate_fibonacci(n)
        except ValueError:
            print("\nErro: O valor de n deve ser um número inteiro.")
        
        return True
    
    async def update_username(self, args: List[str]):
        if not args:
            print("\nUso correto: nome <novo_nome>")
            return True
        
        new_name = " ".join(args)
        await self.client.update_username(new_name)
        return True
    
    async def show_status(self, args: List[str] = None):
        status = "Conectado" if self.client.connected else "Desconectado"
        print(f"\nStatus: {status}")
        
        if self.client.client_id:
            print(f"ID do cliente: {self.client.client_id}")
            
        if self.client.username:
            print(f"Nome de usuário: {self.client.username}")
            
        return True
    
    async def show_time(self, args: List[str] = None):
        print(f"\nHora do servidor: {self.client.current_time}")
        return True
    
    async def reconnect(self, args: List[str] = None):
        await self.client.disconnect()
        success = await self.client.connect()
        
        if success:
            asyncio.create_task(self.client.receive_messages())
            print("\nReconectado ao servidor com sucesso.")
        else:
            print("\nFalha ao reconectar ao servidor.")
            
        return True
    
    async def clear_screen(self, args: List[str] = None):
        self._clear_screen()
        return True
    
    async def exit(self, args: List[str] = None):
        print("\nEncerrando cliente...")
        self.client.running = False
        return False
    
    async def process_command(self, command_input: str):
        if not command_input.strip():
            return True
        
        # Marcar que estamos executando um comando
        self.in_command_execution = True
        
        # Exibir hora atual ao processar comandos - mantendo comportamento original
        if self.client.current_time:
            print(f"\nHora do servidor: {self.client.current_time}")
            # Resetar flag de atualização pendente
            self.client.time_update_pending = False

        self.command_history.append(command_input)
        if len(self.command_history) > 10:
            self.command_history.pop(0)
        self.history_index = -1

        parts = command_input.strip().split(maxsplit=1)
        command_name = parts[0].lower()
        args = parts[1].split() if len(parts) > 1 else []

        if command_name in self.commands:
            try:
                result = await self.commands[command_name].handler(args)
                self.in_command_execution = False
                return result
            except Exception as e:
                logger.error(f"Erro ao processar comando {command_name}: {str(e)}")
                print(f"\nErro ao processar o comando: {str(e)}")
                self.in_command_execution = False
                return True
        else:
            print(f"\nComando desconhecido: '{command_name}'. Digite 'ajuda' para ver as opções disponíveis.")
            self.in_command_execution = False
            return True

    async def _get_keyboard_input(self):
        buffer = ""
        history_position = -1
        cursor_position = 0
        
        # Variável para controlar quando foi a última verificação de hora
        last_time_check = time.time()
        
        while True:
            # Verificar atualizações de hora apenas a cada 500ms para não sobrecarregar o terminal
            current_time = time.time()
            if current_time - last_time_check > 0.5:
                last_time_check = current_time
                
                # Se há uma atualização de hora pendente e não estamos no meio da execução de um comando
                # e não estamos digitando ativamente (último caractere há mais de 1s)
                if (self.client.time_update_pending and 
                    not self.in_command_execution and 
                    current_time - self.last_input_time > 1.0 and
                    not buffer):  # Não interromper se estiver digitando
                    
                    # Restaurar terminal para imprimir a hora
                    fd = sys.stdin.fileno()
                    old_settings = termios.tcgetattr(fd)
                    try:
                        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                        print(f"\rHora do servidor: {self.client.current_time}")
                        print("> " + buffer, end="", flush=True)  # Restaurar prompt
                        self.client.time_update_pending = False
                    finally:
                        termios.tcsetattr(fd, termios.TCSAFLUSH, old_settings)
            
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                readable, _, _ = select.select([sys.stdin], [], [], 0.1)
                
                if not readable:
                    await asyncio.sleep(0.05)  # Reduzir tempo de espera para melhorar responsividade
                    continue
                
                ch = sys.stdin.read(1)
                self.last_input_time = time.time()  # Registrar último tempo de entrada
                
                if ch == '\r':
                    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                    print("\r")  
                    return buffer
                
                elif ch in ('\x7f', '\b'):
                    if cursor_position > 0:
                        buffer = buffer[:cursor_position-1] + buffer[cursor_position:]
                        cursor_position -= 1

                        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                        sys.stdout.write("\r\033[K") 
                        sys.stdout.write(f"> {buffer}")

                        if cursor_position < len(buffer):
                            sys.stdout.write(f"\033[{len(buffer) - cursor_position}D")
                        sys.stdout.flush()
                
                elif ch == '\x03':
                    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                    print("\r\nOperação cancelada.")
                    return ""
                
                elif ch == '\x1b':
                    next_chars = ""
                    readable, _, _ = select.select([sys.stdin], [], [], 0.1)
                    if readable:
                        next_chars += sys.stdin.read(1)
                        if next_chars == '[':
                            readable, _, _ = select.select([sys.stdin], [], [], 0.1)
                            if readable:
                                next_chars += sys.stdin.read(1)
                                
                                if next_chars == '[A':
                                    if self.command_history and history_position < len(self.command_history) - 1:
                                        history_position += 1
                                        buffer = self.command_history[-(history_position+1)]
                                        cursor_position = len(buffer)
                                        
                                        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                                        sys.stdout.write("\r\033[K") 
                                        sys.stdout.write(f"> {buffer}")
                                        sys.stdout.flush()
                                
                                elif next_chars == '[B':
                                    if history_position > 0:
                                        history_position -= 1
                                        buffer = self.command_history[-(history_position+1)]
                                    else:
                                        history_position = -1
                                        buffer = ""
                                    
                                    cursor_position = len(buffer)
                                    
                                    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                                    sys.stdout.write("\r\033[K")  
                                    sys.stdout.write(f"> {buffer}")
                                    sys.stdout.flush()
                                
                                elif next_chars == '[C':
                                    if cursor_position < len(buffer):
                                        cursor_position += 1
                                        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                                        sys.stdout.write("\033[C")
                                        sys.stdout.flush()
                                
                                elif next_chars == '[D':
                                    if cursor_position > 0:
                                        cursor_position -= 1

                                        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                                        sys.stdout.write("\033[D")
                                        sys.stdout.flush()
                
                elif ch.isprintable():
                    if cursor_position == len(buffer):
                        buffer += ch
                        cursor_position += 1
                        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                        sys.stdout.write(ch)
                        sys.stdout.flush()
                    else:
                        buffer = buffer[:cursor_position] + ch + buffer[cursor_position:]
                        cursor_position += 1

                        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                        sys.stdout.write("\r\033[K") 
                        sys.stdout.write(f"> {buffer}")
                        if cursor_position < len(buffer):
                            sys.stdout.write(f"\033[{len(buffer) - cursor_position}D")
                        sys.stdout.flush()
                
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    
    async def run(self):
        self._clear_screen()
        print("Cliente WebSocket - Digite comandos ou 'ajuda' para ver as opções disponíveis")
        print("Para verificar a hora atual, digite o comando 'hora'")
        print("O servidor envia atualizações de hora a cada segundo")
        
        while self.client.running:
            try:
                print("> ", end="", flush=True)
                
                command = await self._get_keyboard_input()
                
                continue_running = await self.process_command(command)
                
                if not continue_running:
                    break
                    
            except asyncio.CancelledError:
                break
                
            except Exception as e:
                logger.error(f"Erro no console interativo: {str(e)}")
                print(f"Erro inesperado: {str(e)}")
                
                await asyncio.sleep(0.5)