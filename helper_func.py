import base64
import asyncio
import time
from pyrogram import filters
from pyrogram.enums import ChatMemberStatus
from config import FORCE_SUB_CHANNEL, FORCE_SUB_CHANNEL2, FORCE_SUB_CHANNEL3, FORCE_SUB_CHANNEL4, ADMINS
from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant
from pyrogram.errors import FloodWait, ChannelInvalid, ChatAdminRequired

# Fallback imports
try:
    from pyrogram.errors.exceptions.bad_request_400 import MessageIdsInvalid
except ImportError:
    MessageIdsInvalid = Exception

# ====================== ORIGINAL HELPER FUNCTIONS ======================

async def encode(string):
    string_bytes = string.encode("ascii")
    base64_bytes = base64.urlsafe_b64encode(string_bytes)
    base64_string = base64_bytes.decode("ascii").strip("=")
    return base64_string


async def decode(base64_string):
    base64_string = base64_string.strip("=")
    base64_bytes = (base64_string + "=" * (-len(base64_string) % 4)).encode("ascii")
    string_bytes = base64.urlsafe_b64decode(base64_bytes)
    string = string_bytes.decode("ascii")
    return string


def get_readable_time(seconds: int) -> str:
    """Convert seconds into readable time format"""
    result = ""
    (days, remainder) = divmod(seconds, 86400)
    (hours, remainder) = divmod(remainder, 3600)
    (minutes, seconds) = divmod(remainder, 60)
    if days:
        result += f"{days}d "
    if hours:
        result += f"{hours}h "
    if minutes:
        result += f"{minutes}m "
    if seconds:
        result += f"{seconds}s"
    return result.strip() or "0s"


async def get_message_id(message):
    """Extract message id"""
    if message.forward_from_chat:
        return message.forward_from_message_id
    elif message.forward_from:
        return message.forward_from_message_id
    elif message.reply_to_message:
        return message.reply_to_message.id
    else:
        return None


# ====================== CLONE DEEP LINK FUNCTIONS ======================
async def encode_link(user_id: int = None, f_msg_id: int = None, s_msg_id: int = None, channel_id: int = None) -> str:
    if channel_id is None or f_msg_id is None:
        raise ValueError("channel_id and f_msg_id are required")
    
    channel_id_encoded = channel_id * 43
    f_msg_id_encoded = f_msg_id * 43
    s_msg_id_encoded = s_msg_id * 43 if s_msg_id is not None else None

    if user_id is not None and s_msg_id is None:
        raw_string = f"HACKHEIST-{user_id}-{f_msg_id_encoded}-{channel_id_encoded}"
    elif s_msg_id is not None:
        raw_string = f"get-{channel_id_encoded}-{f_msg_id_encoded}-{s_msg_id_encoded}"
    else:
        raw_string = f"get-{channel_id_encoded}-{f_msg_id_encoded}"
    
    string_bytes = raw_string.encode("ascii")
    base64_bytes = base64.urlsafe_b64encode(string_bytes)
    base64_string = base64_bytes.decode("ascii").rstrip("=")
    return base64_string


async def decode_link(encoded_string: str):
    encoded_string = encoded_string + "=" * (-len(encoded_string) % 4)
    try:
        string_bytes = base64.urlsafe_b64decode(encoded_string)
        decoded_string = string_bytes.decode("ascii")
    except Exception:
        raise ValueError("Invalid base64 string")

    parts = decoded_string.split("-")
    
    if decoded_string.startswith("HACKHEIST-"):
        user_id = int(parts[1])
        f_msg_id = int(parts[2]) // 43
        channel_id = int(parts[3]) // 43
        return "HACKHEIST", user_id, f_msg_id, channel_id, None
    else:
        channel_id = int(parts[1]) // 43
        f_msg_id = int(parts[2]) // 43
        s_msg_id = int(parts[3]) // 43 if len(parts) > 3 else None
        return "batch", None, f_msg_id, channel_id, s_msg_id


# ====================== FORCE SUB FOR CLONES ======================
async def is_subscribed(filter, client, update):
    user_id = update.from_user.id
    if user_id in ADMINS:
        return True

    force_list = getattr(client, 'force_subs', [])
    if not force_list or len(force_list) == 0:
        force_list = [ch for ch in [FORCE_SUB_CHANNEL, FORCE_SUB_CHANNEL2, FORCE_SUB_CHANNEL3, FORCE_SUB_CHANNEL4] if ch and ch != 0]

    if not force_list:
        return True

    for fsub in force_list:
        if not fsub or fsub == 0:
            continue
        try:
            member = await client.get_chat_member(chat_id=fsub, user_id=user_id)
            if member.status not in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.MEMBER]:
                return False
        except UserNotParticipant:
            return False
        except Exception:
            continue
    return True


# ====================== GET MESSAGES ======================
async def get_messages(client, message_ids, channel_id):
    messages = []
    if not message_ids or not channel_id:
        return messages

    total_messages = 0
    while total_messages < len(message_ids):
        temb_ids = message_ids[total_messages:total_messages + 200]
        try:
            msgs = await client.get_messages(chat_id=channel_id, message_ids=temb_ids)
            valid_msgs = [msg for msg in (msgs if isinstance(msgs, list) else [msgs]) if msg is not None]
            messages.extend(valid_msgs)
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except MessageIdsInvalid:
            print(f"Invalid message IDs: {temb_ids}")
        except (ChannelInvalid, ChatAdminRequired) as e:
            print(f"Channel access error: {e}")
            return messages
        except Exception as e:
            print(f"Error in get_messages: {e}")
        
        total_messages += 200
    return messages


# Final Filter
subscribed = filters.create(is_subscribed)
