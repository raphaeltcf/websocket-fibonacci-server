FROM python:3.10

WORKDIR /core

COPY requirements.txt docker-compose.yml Dockerfile .env /core/
COPY app /core/app

RUN pip install --no-cache-dir -r requirements.txt && \
    apt-get update && \
    apt-get install -y netcat-openbsd net-tools && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /core/app/server

EXPOSE 8765

CMD ["python", "main.py"]