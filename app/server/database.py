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
        'last_active': current_time,
        'online': True,
        'disconnected_at': None
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
    
def set_user_offline(user_id):
    try:
        current_time = datetime.datetime.now()
        result = collection.update_one(
            {'id': user_id},
            {'$set': {'online': False, 'disconnected_at': current_time}}
        )
        
        if result.modified_count > 0:
            logger.info(f"Usuário {user_id} atualizado para offline.")
            return True
        else:
            logger.warning(f"Usuário {user_id} não encontrado para atualização de status.")
            return False
            
    except PyMongoError as e:
        logger.error(f"Erro ao atualizar status do usuário: {str(e)}")
        return False

def update_user_activity(user_id):
    try:
        # Verificar se o usuário existe
        user = collection.find_one({'id': user_id})
        if not user:
            logger.warning(f"Usuário {user_id} não encontrado para atualização de atividade.")
            return False
            
        # Registrar o timestamp antigo para diagnóstico
        old_timestamp = user.get('last_active')
        current_time = datetime.datetime.now()
        
        # Atualizar a atividade
        result = collection.update_one(
            {'id': user_id},
            {'$set': {
                'last_active': current_time,
                'online': True
            }}
        )
        
        if result.modified_count > 0:
            logger.info(f"Atividade do usuário {user_id} atualizada: {old_timestamp} -> {current_time}")
            return True
        else:
            logger.warning(f"Atualização de atividade para {user_id} não modificou nenhum documento.")
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
        users = list(collection.find({'online': True}, {'_id': 0}))  
        return users
        
    except PyMongoError as e:
        logger.error(f"Erro ao recuperar usuários conectados: {str(e)}")
        return []
    
def get_all_users():
    try:
        users = list(collection.find({}, {'_id': 0}))  
        return users
        
    except PyMongoError as e:
        logger.error(f"Erro ao recuperar usuários: {str(e)}")
        return []

def mark_inactive_users_as_offline(inactive_minutes=5):
    """Marca usuários que não tiveram atividade recente como offline."""
    try:
        cutoff_time = datetime.datetime.now() - datetime.timedelta(minutes=inactive_minutes)
        
        # Log para debug
        logger.info(f"Procurando usuários inativos desde: {cutoff_time}")
        
        # Encontrar usuários inativos que ainda estão marcados como online
        inactive_users = list(collection.find({
            'online': True,
            'last_active': {'$lt': cutoff_time}
        }))
        
        if inactive_users:
            for user in inactive_users:
                logger.info(f"Usuário inativo encontrado: {user['username']} ({user['id']}), último ativo: {user['last_active']}")
        
        result = collection.update_many(
            {
                'online': True,
                'last_active': {'$lt': cutoff_time}
            },
            {
                '$set': {
                    'online': False,
                    'disconnected_at': datetime.datetime.now()
                }
            }
        )
        
        count = result.modified_count
        if count > 0:
            logger.info(f"Marcados {count} usuários inativos como offline")
        return count
    except PyMongoError as e:
        logger.error(f"Erro ao marcar usuários inativos: {str(e)}")
        return 0

def close_connection():
    try:
        client.close()
        logger.info("Conexão com MongoDB fechada.")
    except PyMongoError as e:
        logger.error(f"Erro ao fechar conexão com MongoDB: {str(e)}")