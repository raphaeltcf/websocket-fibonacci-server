import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_USER = os.getenv("MONGO_USER", "admin")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "password")
MONGO_HOST = os.getenv("MONGO_HOST", "websocket-mongodb")
MONGO_PORT = int(os.getenv("MONGO_PORT", 27017))
MONGO_DB = os.getenv("MONGO_DB", "websocket_db")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "connected_users")

MONGO_URI = f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}/{MONGO_DB}?authSource=admin"

try:
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    if MONGO_COLLECTION not in db.list_collection_names():
        db.create_collection(MONGO_COLLECTION)
    print("✅ Conectado ao MongoDB com sucesso!")
except Exception as e:
    print(f"❌ Erro ao conectar ao MongoDB: {e}")

SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", 8765))

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"