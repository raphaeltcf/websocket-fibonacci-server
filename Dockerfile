FROM python:3.10

WORKDIR /app

COPY requirements.txt docker-compose.yml Dockerfile .env /app/
COPY websocket_project /app/websocket_project

RUN pip install --no-cache-dir -r requirements.txt

WORKDIR /app/websocket_project/server

EXPOSE 8765

CMD ["python", "main.py"]
