import datetime
import logging
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from config import MONGO_URI, MONGO_DB, MONGO_COLLECTION

logger = logging.getLogger('websocket_server.database')

try:
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    collection = db[MONGO_COLLECTION]
    logger.info(f"Conexão com MongoDB estabelecida: {MONGO_URI}")
except PyMongoError as e:
    logger.error(f"Erro ao conectar com MongoDB: {str(e)}")
    raise

def init_database():
    try:
        collection.create_index('id', unique=True)
        logger.info("Banco de dados MongoDB inicializado.")
    except PyMongoError as e:
        logger.error(f"Erro ao inicializar o banco de dados: {str(e)}")
        raise

def add_user_to_db(user_id, username):
    current_time = datetime.datetime.now()
    user_data = {
        'id': user_id,
        'username': username,
        'connected_at': current_time,
        'last_active': current_time
    }
    
    try:
        result = collection.update_one(
            {'id': user_id}, 
            {'$set': user_data}, 
            upsert=True
        )
        
        if result.upserted_id or result.modified_count > 0:
            logger.info(f"Usuário {username} ({user_id}) adicionado ao banco de dados.")
            return True
        else:
            logger.warning(f"Nenhuma modificação ao adicionar usuário {username} ({user_id}).")
            return False
            
    except PyMongoError as e:
        logger.error(f"Erro ao adicionar usuário ao banco de dados: {str(e)}")
        return False

def remove_user_from_db(user_id):
    try:
        result = collection.delete_one({'id': user_id})
        
        if result.deleted_count > 0:
            logger.info(f"Usuário {user_id} removido do banco de dados.")
            return True
        else:
            logger.warning(f"Usuário {user_id} não encontrado para remoção.")
            return False
            
    except PyMongoError as e:
        logger.error(f"Erro ao remover usuário do banco de dados: {str(e)}")
        return False

def update_user_activity(user_id):
    try:
        result = collection.update_one(
            {'id': user_id},
            {'$set': {'last_active': datetime.datetime.now()}}
        )
        
        if result.modified_count > 0:
            return True
        else:
            logger.warning(f"Usuário {user_id} não encontrado para atualização de atividade.")
            return False
            
    except PyMongoError as e:
        logger.error(f"Erro ao atualizar atividade do usuário: {str(e)}")
        return False

def update_username(user_id, new_username):
    try:
        result = collection.update_one(
            {'id': user_id},
            {'$set': {'username': new_username}}
        )
        
        if result.modified_count > 0:
            logger.info(f"Nome de usuário atualizado para {new_username} ({user_id})")
            return new_username
        else:
            logger.warning(f"Usuário {user_id} não encontrado para atualização de nome.")
            return None
            
    except PyMongoError as e:
        logger.error(f"Erro ao atualizar nome de usuário: {str(e)}")
        return None

def get_all_connected_users():
    try:

        users = list(collection.find({}, {'_id': 0}))  
        return users
        
    except PyMongoError as e:
        logger.error(f"Erro ao recuperar usuários conectados: {str(e)}")
        return []

def close_connection():

    try:
        client.close()
        logger.info("Conexão com MongoDB fechada.")
    except PyMongoError as e:
        logger.error(f"Erro ao fechar conexão com MongoDB: {str(e)}")