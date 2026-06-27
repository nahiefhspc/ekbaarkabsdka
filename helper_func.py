import base64
import asyncio
import time
from pyrogram import filters
from pyrogram.enums import ChatMemberStatus
from config import (
    FORCE_SUB_CHANNEL, FORCE_SUB_CHANNEL2,
    FORCE_SUB_CHANNEL3, FORCE_SUB_CHANNEL4, ADMINS
)
from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant
from pyrogram.errors import FloodWait, ChannelInvalid, ChatAdminRequired

try:
    from pyrogram.errors.exceptions.bad_request_400 import MessageIdsInvalid
except ImportError:
    MessageIdsInvalid = Exception


# ====================== ENCODE ======================
async def encode(string):
    string_bytes = string.encode("ascii")
    base64_bytes = base64.urlsafe_b64encode(string_bytes)
    base64_string = base64_bytes.decode("ascii").strip("=")
    return base64_string


# ====================== DECODE ======================
async def decode(base64_string):
    base64_string = base64_string.strip("=")
    base64_bytes = (base64_string + "=" * (-len(base64_string) % 4)).encode("ascii")
    string_bytes = base64.urlsafe_b64decode(base64_bytes)
    string = string_bytes.decode("ascii")
    return string


# ====================== READABLE TIME ======================
def get_readable_time(seconds: int) -> str:
    result = ""
    (days, remainder) = divmod(seconds, 86400)
    (hours, remainder) = divmod(remainder, 3600)
    (minutes, seconds) = divmod(remainder, 60)
    if days: result += f"{days}d "
    if hours: result += f"{hours}h "
    if minutes: result += f"{minutes}m "
    if seconds: result += f"{seconds}s"
    return result.strip() or "0s"


# ====================== GET MESSAGE ID ======================
async def get_message_id(message):
    if message.forward_from_chat:
        return message.forward_from_message_id
    elif message.forward_from:
        return message.forward_from_message_id
    elif message.reply_to_message:
        return message.reply_to_message.id
    return None


# ====================== DECODE LINK ======================
async def decode_link(encoded_string: str):
    encoded_string = encoded_string + "=" * (-len(encoded_string) % 4)
    try:
        string_bytes = base64.urlsafe_b64decode(encoded_string)
        decoded_string = string_bytes.decode("ascii")
    except Exception:
        raise ValueError("Invalid base64 string")

    parts = decoded_string.split("-")

    if decoded_string.startswith("HACKHEIST-"):
        try:
            user_id = int(parts[1])
            f_msg_id = int(parts[2]) // 43
            channel_id = int(parts[3]) // 43
            return "HACKHEIST", user_id, f_msg_id, channel_id, None
        except Exception:
            raise ValueError("Invalid HACKHEIST link")

    else:  # Batch link
        try:
            channel_id = int(parts[1]) // 43
            f_msg_id = int(parts[2]) // 43
            s_msg_id = int(parts[3]) // 43 if len(parts) > 3 else None
            return "batch", None, f_msg_id, channel_id, s_msg_id
        except Exception as e:
            print(f"Decode error: {decoded_string} | {e}")
            raise ValueError("Invalid link format")


# ====================== ENCODE LINK ======================
async def encode_link(
    user_id: int = None,
    f_msg_id: int = None,
    s_msg_id: int = None,
    channel_id: int = None
) -> str:
    if channel_id is None or f_msg_id is None:
        raise ValueError("channel_id and f_msg_id required")

    channel_id_encoded = channel_id * 43
    f_msg_id_encoded = f_msg_id * 43
    s_msg_id_encoded = s_msg_id * 43 if s_msg_id is not None else None

    if user_id is not None and s_msg_id is None:
        # Individual file link
        raw_string = f"HACKHEIST-{user_id}-{f_msg_id_encoded}-{channel_id_encoded}"
    elif s_msg_id is not None:
        # Batch link
        raw_string = f"get-{channel_id_encoded}-{f_msg_id_encoded}-{s_msg_id_encoded}"
    else:
        raw_string = f"get-{channel_id_encoded}-{f_msg_id_encoded}"

    string_bytes = raw_string.encode("ascii")
    base64_bytes = base64.urlsafe_b64encode(string_bytes)
    base64_string = base64_bytes.decode("ascii").rstrip("=")
    return base64_string


# ====================== IS SUBSCRIBED ======================
async def is_subscribed(filter, client, update):
    """
    Check karo user ne force sub channels join kiye hain ya nahi.
    
    Priority:
    1. ADMINS → always True
    2. Clone config mein FORCE_SUB channels → clone ke channels check karo
    3. clone.force_subs list → unhe check karo  
    4. Global config → main bot ke channels
    """
    # from_user check
    if not update.from_user:
        return False

    user_id = update.from_user.id

    # Admins ko skip
    if user_id in ADMINS:
        return True

    # ─── Force Sub Channels collect karo ───
    force_channels = []

    # 1. Clone config mein directly FORCE_SUB keys hain?
    if hasattr(client, 'clone_config') and client.clone_config:
        cfg = client.clone_config

        # Individual keys check karo
        config_channels = [
            cfg.get('FORCE_SUB_CHANNEL'),
            cfg.get('FORCE_SUB_CHANNEL2'),
            cfg.get('FORCE_SUB_CHANNEL3'),
            cfg.get('FORCE_SUB_CHANNEL4'),
        ]
        config_channels = [ch for ch in config_channels if ch and ch != 0]

        if config_channels:
            force_channels = config_channels

    # 2. Clone ki force_subs list (set_force se add hua)
    if not force_channels and hasattr(client, 'force_subs') and client.force_subs:
        force_channels = [ch for ch in client.force_subs if ch and ch != 0]

    # 3. Global config fallback (main bot)
    if not force_channels:
        force_channels = [
            ch for ch in [
                FORCE_SUB_CHANNEL,
                FORCE_SUB_CHANNEL2,
                FORCE_SUB_CHANNEL3,
                FORCE_SUB_CHANNEL4
            ]
            if ch and ch != 0
        ]

    # Agar koi channel hi nahi toh subscribed hai
    if not force_channels:
        return True

    # ─── Har channel check karo ───
    for channel in force_channels:
        try:
            member = await client.get_chat_member(
                chat_id=channel,
                user_id=user_id
            )
            # Banned ya left hai?
            if member.status in [
                ChatMemberStatus.BANNED,
                ChatMemberStatus.LEFT,
                ChatMemberStatus.RESTRICTED
            ]:
                return False

        except UserNotParticipant:
            # Join nahi kiya
            return False

        except (ChannelInvalid, ChatAdminRequired) as e:
            # Bot admin nahi ya channel invalid - skip
            print(f"Force sub check skip {channel}: {e}")
            continue

        except Exception as e:
            print(f"Force sub error {channel}: {e}")
            continue

    return True


# ====================== GET MESSAGES ======================
async def get_messages(client, message_ids, channel_id):
    messages = []
    if not message_ids or not channel_id:
        return messages

    total = 0
    while total < len(message_ids):
        batch = message_ids[total:total + 200]
        try:
            msgs = await client.get_messages(
                chat_id=channel_id,
                message_ids=batch
            )
            if isinstance(msgs, list):
                valid = [m for m in msgs if m]
            else:
                valid = [msgs] if msgs else []
            messages.extend(valid)

        except FloodWait as e:
            await asyncio.sleep(e.value)

        except MessageIdsInvalid as e:
            print(f"Invalid message IDs {batch}: {e}")

        except Exception as e:
            print(f"Get messages error: {e}")

        total += 200

    return messages


# ====================== SUBSCRIBED FILTER ======================
subscribed = filters.create(is_subscribed)
