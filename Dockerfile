FROM python:3.10

WORKDIR /core

COPY requirements.txt docker-compose.yml Dockerfile .env /core/
COPY app /core/app

RUN pip install --no-cache-dir -r requirements.txt

WORKDIR /core/app/server

EXPOSE 8765

CMD ["python", "main.py"]
