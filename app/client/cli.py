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
            "usuarios", 
            self.list_users, 
            "Mostra a lista de usuários conectados"
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
            return False  
        
        try:
            n = int(args[0])
            success = await self.client.calculate_fibonacci(n)
            return success  
        except ValueError:
            print("\nErro: O valor de n deve ser um número inteiro.")
            return False 
        
    async def update_username(self, args: List[str]):
        if not args:
            print("\nUso correto: nome <novo_nome>")
            return False 
        
        new_name = " ".join(args)
        success = await self.client.update_username(new_name)
        return success  
        
    async def list_users(self, args: List[str] = None):
        await self.client.list_users()
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
        
        self.in_command_execution = True
        
        if self.client.current_time:
            print(f"\nHora do servidor: {self.client.current_time}")

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
        last_time_check = time.time()
        
        while True:
            current_time = time.time()
            if self._should_update_time_display(current_time, last_time_check, buffer):
                last_time_check = current_time
                self._display_server_time(buffer)
            
            char, action = await self._read_keyboard_input()
            
            if action == "return":
                return buffer
            elif action == "cancel":
                return ""
            elif action == "none":
                continue
                
            buffer, cursor_position, history_position = self._process_input(
                char, action, buffer, cursor_position, history_position
            )
    
    def _should_update_time_display(self, current_time, last_time_check, buffer):
        time_elapsed = current_time - last_time_check > 0.5
        can_interrupt = (self.client.time_update_pending and 
                        not self.in_command_execution and 
                        current_time - self.last_input_time > 1.0 and
                        not buffer)
        return time_elapsed and can_interrupt
    
    def _display_server_time(self, buffer):
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            print(f"\rHora do servidor: {self.client.current_time}")
            print("> " + buffer, end="", flush=True)
            self.client.time_update_pending = False
        finally:
            termios.tcsetattr(fd, termios.TCSAFLUSH, old_settings)
    
    async def _read_keyboard_input(self):
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            readable, _, _ = select.select([sys.stdin], [], [], 0.1)
            
            if not readable:
                await asyncio.sleep(0.05)
                return None, "none"
            
            ch = sys.stdin.read(1)
            self.last_input_time = time.time()
            
            if ch == '\r':  
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                print("\r")
                return None, "return"
            
            elif ch == '\x03': 
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                print("\r\nOperação cancelada.")
                return None, "cancel"
            
            elif ch in ('\x7f', '\b'): 
                return ch, "backspace"
            
            elif ch == '\x1b': 
                return self._read_escape_sequence(fd, old_settings)
                
            elif ch.isprintable():
                return ch, "printable"
                
            return None, "none"
                
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    
    def _read_escape_sequence(self, fd, old_settings):
        next_chars = ""
        readable, _, _ = select.select([sys.stdin], [], [], 0.1)
        
        if not readable:
            return '\x1b', "escape"
            
        next_chars += sys.stdin.read(1)
        if next_chars != '[':
            return '\x1b' + next_chars, "escape_seq"
            
        readable, _, _ = select.select([sys.stdin], [], [], 0.1)
        if not readable:
            return '\x1b[', "escape_seq"
            
        next_chars += sys.stdin.read(1)
        
        if next_chars == '[A':
            return None, "arrow_up"
        elif next_chars == '[B':
            return None, "arrow_down"
        elif next_chars == '[C':
            return None, "arrow_right"
        elif next_chars == '[D':
            return None, "arrow_left"
        else:
            return '\x1b' + next_chars, "escape_seq"
    
    def _process_input(self, char, action, buffer, cursor_position, history_position):
        if action == "backspace":
            return self._handle_backspace(buffer, cursor_position, history_position)
        elif action.startswith("arrow_"):
            return self._handle_arrow_key(action, buffer, cursor_position, history_position)
        elif action == "printable":
            return self._handle_printable_char(char, buffer, cursor_position, history_position)
        else:
            return buffer, cursor_position, history_position
    
    def _handle_backspace(self, buffer, cursor_position, history_position):
        if cursor_position <= 0:
            return buffer, cursor_position, history_position
            
        new_buffer = buffer[:cursor_position-1] + buffer[cursor_position:]
        new_position = cursor_position - 1
        
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        
        sys.stdout.write("\r\033[K")
        sys.stdout.write(f"> {new_buffer}")
        
        if new_position < len(new_buffer):
            sys.stdout.write(f"\033[{len(new_buffer) - new_position}D")
        
        sys.stdout.flush()
        
        return new_buffer, new_position, history_position
    
    def _handle_arrow_key(self, action, buffer, cursor_position, history_position):
        if action == "arrow_up":
            return self._navigate_history_up(buffer, cursor_position, history_position)
        elif action == "arrow_down":
            return self._navigate_history_down(buffer, cursor_position, history_position)
        elif action == "arrow_right":
            return self._move_cursor_right(buffer, cursor_position, history_position)
        elif action == "arrow_left":
            return self._move_cursor_left(buffer, cursor_position, history_position)
        
        return buffer, cursor_position, history_position
    
    def _navigate_history_up(self, buffer, cursor_position, history_position):
        if not self.command_history or history_position >= len(self.command_history) - 1:
            return buffer, cursor_position, history_position
            
        new_history_position = history_position + 1
        new_buffer = self.command_history[-(new_history_position+1)]
        new_position = len(new_buffer)
        
        self._update_display_line(new_buffer)
        
        return new_buffer, new_position, new_history_position
    
    def _navigate_history_down(self, buffer, cursor_position, history_position):
        if history_position <= 0:
            new_history_position = -1
            new_buffer = ""
        else:
            new_history_position = history_position - 1
            new_buffer = self.command_history[-(new_history_position+1)]
        
        new_position = len(new_buffer)
        self._update_display_line(new_buffer)
        
        return new_buffer, new_position, new_history_position
    
    def _move_cursor_right(self, buffer, cursor_position, history_position):
        if cursor_position >= len(buffer):
            return buffer, cursor_position, history_position
            
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        
        sys.stdout.write("\033[C")
        sys.stdout.flush()
        
        return buffer, cursor_position + 1, history_position
    
    def _move_cursor_left(self, buffer, cursor_position, history_position):
        if cursor_position <= 0:
            return buffer, cursor_position, history_position
            
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        
        sys.stdout.write("\033[D")
        sys.stdout.flush()
        
        return buffer, cursor_position - 1, history_position
    
    def _handle_printable_char(self, char, buffer, cursor_position, history_position):
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        
        if cursor_position == len(buffer):
            new_buffer = buffer + char
            new_position = cursor_position + 1
            
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            sys.stdout.write(char)
            sys.stdout.flush()
        else:
            new_buffer = buffer[:cursor_position] + char + buffer[cursor_position:]
            new_position = cursor_position + 1
            
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            sys.stdout.write("\r\033[K")
            sys.stdout.write(f"> {new_buffer}")
            
            if new_position < len(new_buffer):
                sys.stdout.write(f"\033[{len(new_buffer) - new_position}D")
                
            sys.stdout.flush()
        
        return new_buffer, new_position, history_position
    
    def _update_display_line(self, buffer):
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        
        sys.stdout.write("\r\033[K")
        sys.stdout.write(f"> {buffer}")
        sys.stdout.flush()
    
    async def run(self):
        self._clear_screen()
        print("CLIENTE WEBSOCKET INTERATIVO")
        print("")
        print("Bem-vindo ao sistema de comunicação em tempo real via WebSocket!")
        print("")
        print("Funcionalidades principais:")
        print("• O servidor envia atualizações de hora automaticamente a cada segundo")
        print("• Você pode calcular sequências de Fibonacci rapidamente")
        print("• Veja quais usuários estão conectados no momento")
        print("• As setas ↑↓ permitem navegar no histórico de comandos")
        print("• Pressione Ctrl+C para cancelar uma operação em andamento")
        print("")
        print("Comandos disponíveis:")
        
        commands_list = sorted(self.commands.items())
        half = len(commands_list) // 2 + len(commands_list) % 2
        
        for i in range(half):
            left_cmd = commands_list[i]
            left_usage = left_cmd[1].usage
            left_desc = left_cmd[1].description
            
            left_part = f"  {left_usage:14} - {left_desc}"
            
            if i + half < len(commands_list):
                right_cmd = commands_list[i + half]
                right_usage = right_cmd[1].usage
                right_desc = right_cmd[1].description
                right_part = f"  {right_usage:14} - {right_desc}"
                print(f"{left_part:50} {right_part}")
            else:
                print(left_part)
        
        print("")
        print("Inicie digitando um comando ou 'ajuda' para ver estas instruções novamente.")
        print("")
        
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