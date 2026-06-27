import pymongo, os
from config import DB_URI, DB_NAME
import time
import uuid

dbclient = pymongo.MongoClient(DB_URI)
database = dbclient[DB_NAME]

# ====================== COLLECTIONS ======================
user_data = database['users']
special_messages = database['special_messages']
scheduled_broadcasts = database['scheduled_broadcasts']
clones = database['clones']   # Clone bots + full config

# ====================== USER FUNCTIONS ======================
async def present_user(user_id: int):
    found = user_data.find_one({'_id': user_id})
    return bool(found)


async def add_user(user_id: int):
    user_data.insert_one({'_id': user_id})
    return


async def full_userbase():
    user_docs = user_data.find()
    user_ids = [doc['_id'] for doc in user_docs]
    return user_ids


async def del_user(user_id: int):
    user_data.delete_one({'_id': user_id})
    return


# ====================== SPECIAL MESSAGES ======================
async def add_special_message(msg_id: int, bot_id: str):
    special_messages.update_one(
        {'_id': f"{bot_id}_special_msg_ids"},
        {'$addToSet': {'msg_ids': msg_id}},
        upsert=True
    )
    return


async def remove_special_message(msg_id: int, bot_id: str):
    special_messages.update_one(
        {'_id': f"{bot_id}_special_msg_ids"},
        {'$pull': {'msg_ids': msg_id}}
    )
    return


async def get_special_messages(bot_id: str):
    doc = special_messages.find_one({'_id': f"{bot_id}_special_msg_ids"})
    return doc.get('msg_ids', []) if doc else []


async def get_all_special_messages():
    return list(special_messages.find())


# ====================== SCHEDULED BROADCAST ======================
async def add_scheduled_broadcast(admin_chat_id: int, chat_id: int, reply_msg_id: int, total_time: int, interval: int, delete_after: int, start_delay: int = 0, bot_id: str = None):
    schedule_id = str(uuid.uuid4())
    scheduled_broadcasts.insert_one({
        '_id': schedule_id,
        'admin_chat_id': admin_chat_id,
        'chat_id': chat_id,
        'reply_msg_id': reply_msg_id,
        'total_time': total_time,
        'interval': interval,
        'delete_after': delete_after,
        'start_delay': start_delay,
        'start_time': time.time(),
        'active': True,
        'bot_id': bot_id
    })
    return schedule_id


async def get_active_scheduled_broadcasts(bot_id: str = None):
    query = {'active': True}
    if bot_id:
        query['bot_id'] = bot_id
    return list(scheduled_broadcasts.find(query))


async def deactivate_scheduled_broadcast(schedule_id: str):
    scheduled_broadcasts.update_one({'_id': schedule_id}, {'$set': {'active': False}})


async def delete_scheduled_broadcast(schedule_id: str):
    scheduled_broadcasts.delete_one({'_id': schedule_id})


async def get_schedule_by_id(schedule_id: str):
    return scheduled_broadcasts.find_one({'_id': schedule_id})


async def update_schedule_start_time(schedule_id: str, start_time: float, start_delay: int = None):
    update = {'start_time': start_time}
    if start_delay is not None:
        update['start_delay'] = start_delay
    scheduled_broadcasts.update_one({'_id': schedule_id}, {'$set': update})


# ====================== CLONE BOT FUNCTIONS (Full Config Support) ======================
async def add_clone(token: str, owner_id: int, force_subs: list = None, config: dict = None):
    if force_subs is None:
        force_subs = []
    if config is None:
        config = {}

    clones.update_one(
        {'token': token},
        {'$set': {
            'owner_id': owner_id,
            'force_subs': force_subs,
            'config': config,           # ← Yeh sab config save hoga (START_MSG, CUSTOM_CAPTION, PROTECT_CONTENT, etc.)
            'added_at': time.time(),
            'added_by': owner_id,
            'status': 'active'
        }},
        upsert=True
    )
    return True


async def get_all_clones():
    return list(clones.find({}))


async def remove_clone(token: str):
    clones.delete_one({'token': token})
    return True


async def get_clone_by_partial_token(partial_token: str):
    """Find clone by last 8 digits"""
    for clone in clones.find({}):
        if clone['token'].endswith(partial_token):
            return clone
    return None


async def update_clone_force_subs(token: str, force_subs: list):
    clones.update_one({'token': token}, {'$set': {'force_subs': force_subs}})
    return True


async def update_clone_config(token: str, new_config: dict):
    """Update clone's config"""
    clones.update_one(
        {'token': token},
        {'$set': {'config': new_config}}
    )
    return True


async def get_clone_config(token: str):
    """Get clone's config"""
    clone = clones.find_one({'token': token})
    return clone.get('config', {}) if clone else {}
