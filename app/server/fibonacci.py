
import logging

logger = logging.getLogger('websocket_server.fibonacci')

def calculate_fibonacci(n: int) -> int:
    if not isinstance(n, int):
        logger.warning(f"Valor não inteiro recebido: {n}")
        raise TypeError("O valor de n deve ser um inteiro")
    
    if n < 0:
        logger.warning(f"Valor negativo recebido: {n}")
        raise ValueError("O valor de n não pode ser negativo")
    
    if n == 0:
        return 0
    elif n == 1:
        return 1
    
    a, b = 0, 1
    
    if n > 35:
        logger.info(f"Calculando Fibonacci para um valor grande: {n}")
    
    for _ in range(2, n + 1):
        a, b = b, a + b
    
    return b