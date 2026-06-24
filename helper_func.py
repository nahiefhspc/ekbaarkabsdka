#(©)CodeFlix_Bots

import base64
import re
import asyncio
from pyrogram import filters
from pyrogram.enums import ChatMemberStatus
from config import FORCE_SUB_CHANNEL, FORCE_SUB_CHANNEL2, FORCE_SUB_CHANNEL3, FORCE_SUB_CHANNEL4, ADMINS
from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant
from pyrogram.errors import FloodWait, MessageIdsInvalid, ChannelInvalid, ChatAdminRequired
from typing import Tuple, Union

# ====================== UPDATED FOR CLONE SYSTEM ======================
async def is_subscribed(filter, client, update):
    """Dynamic Force Subscribe checker for both Main Bot and Clones"""
    user_id = update.from_user.id
    
    # Admins ko hamesha allow
    if user_id in ADMINS:
        return True

    # Get force subs list (clone ke liye client.force_subs, main bot ke liye config se)
    force_list = getattr(client, 'force_subs', [])
    
    # Agar clone nahi hai toh default config wale channels use karo
    if not force_list or len(force_list) == 0:
        force_list = [ch for ch in [FORCE_SUB_CHANNEL, FORCE_SUB_CHANNEL2, FORCE_SUB_CHANNEL3, FORCE_SUB_CHANNEL4] if ch and ch != 0]

    if not force_list:
        return True  # Koi force sub nahi hai

    for fsub in force_list:
        if not fsub or fsub == 0:
            continue
        try:
            member = await client.get_chat_member(chat_id=fsub, user_id=user_id)
            if member.status not in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.MEMBER]:
                return False
        except UserNotParticipant:
            return False
        except Exception as e:
            print(f"Force Sub Check Error for {fsub}: {e}")
            continue  # Agar koi channel error de to agla check karo

    return True


# ====================== ENCODE / DECODE FUNCTIONS (Original) ======================
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


async def encode_new(string):
    string_bytes = string.encode("ascii")
    base64_bytes = base64.urlsafe_b64encode(string_bytes)
    base64_string2 = base64_bytes.decode("ascii").strip("=")
    return base64_string2


async def decode_new(base64_string2):
    try:
        base64_string2 = base64_string2.strip("=")
        base64_bytes = (base64_string2 + "=" * (-len(base64_string2) % 4)).encode("ascii")
        string_bytes = base64.urlsafe_b64decode(base64_bytes)
        string = string_bytes.decode("ascii")
        return string
    except Exception as e:
        print(f"Decode_new error: {e}")
        raise


async def encode_link(user_id: int = None, f_msg_id: int = None, s_msg_id: int = None, channel_id: int = None) -> str:
    """
    Encode a Telegram bot deep link for batch or HACKHEIST access with *43 multiplication.
    """
    if channel_id is None or f_msg_id is None:
        raise ValueError("channel_id and f_msg_id are required")
    
    if not all(isinstance(x, int) for x in [user_id, f_msg_id, s_msg_id, channel_id] if x is not None):
        raise ValueError("All IDs must be integers")
    
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
    
    return f"{base64_string}"


async def decode_link(encoded_string: str) -> Tuple[str, Union[int, None], int, int, Union[int, None]]:
    """
    Decode a base64 string from a Telegram bot deep link.
    """
    encoded_string = encoded_string + "=" * (-len(encoded_string) % 4)
    
    try:
        string_bytes = base64.urlsafe_b64decode(encoded_string)
        decoded_string = string_bytes.decode("ascii")
    except (base64.binascii.Error, UnicodeDecodeError):
        raise ValueError("Invalid base64 encoded string")
    
    parts = decoded_string.split("-")
    
    if decoded_string.startswith("HACKHEIST-"):
        if len(parts) not in [4, 5]:
            raise ValueError("Invalid HACKHEIST string structure")
        try:
            user_id = int(parts[1])
            f_msg_id = int(parts[2]) // 43
            if len(parts) == 5 and parts[3] == "":
                channel_id = int(f"-{parts[4]}") // 43
            else:
                channel_id = int(parts[3]) // 43
            return "HACKHEIST", user_id, f_msg_id, channel_id, None
        except ValueError:
            raise ValueError("Invalid number format in HACKHEIST string")
    
    elif decoded_string.startswith("get-"):
        if len(parts) not in [3, 4, 5]:
            raise ValueError("Invalid batch string structure")
        try:
            if len(parts) == 5 and parts[1] == "":
                channel_id = int(f"-{parts[2]}") // 43
                f_msg_id = int(parts[3]) // 43
                s_msg_id = int(parts[4]) // 43
            elif len(parts) == 4 and parts[1] != "":
                channel_id = int(parts[1]) // 43
                f_msg_id = int(parts[2]) // 43
                s_msg_id = int(parts[3]) // 43
            elif len(parts) == 4 and parts[1] == "":
                channel_id = int(f"-{parts[2]}") // 43
                f_msg_id = int(parts[3]) // 43
                s_msg_id = None
            elif len(parts) == 3:
                channel_id = int(parts[1]) // 43
                f_msg_id = int(parts[2]) // 43
                s_msg_id = None
            else:
                raise ValueError("Invalid batch string structure")
            return "batch", None, f_msg_id, channel_id, s_msg_id
        except ValueError:
            raise ValueError("Invalid number format in batch string")
    
    else:
        raise ValueError("Invalid encoded string format")


async def get_messages(client, message_ids, channel_id):
    """
    Fetch messages from a specified channel by message IDs.
    """
    messages = []
    total_messages = 0

    if not message_ids:
        print("No message IDs provided")
        return messages
    if not channel_id:
        print("No channel ID provided")
        return messages

    try:
        await client.get_chat(channel_id)
    except (ChannelInvalid, ChatAdminRequired) as e:
        print(f"Channel access error {channel_id}: {e}")
        return messages
    except Exception as e:
        print(f"Error accessing channel {channel_id}: {e}")
        return messages

    while total_messages < len(message_ids):
        temb_ids = message_ids[total_messages:total_messages+200]
        try:
            msgs = await client.get_messages(
                chat_id=channel_id,
                message_ids=temb_ids
            )
            valid_msgs = [msg for msg in (msgs if isinstance(msgs, list) else [msgs]) if msg is not None]
            messages.extend(valid_msgs)
        except FloodWait as e:
            print(f"FloodWait: Waiting {e.value} seconds")
            await asyncio.sleep(e.value)
            try:
                msgs = await client.get_messages(chat_id=channel_id, message_ids=temb_ids)
                valid_msgs = [msg for msg in (msgs if isinstance(msgs, list) else [msgs]) if msg is not None]
                messages.extend(valid_msgs)
            except Exception as ex:
                print(f"Error after FloodWait: {ex}")
        except MessageIdsInvalid:
            print(f"Invalid message IDs: {temb_ids}")
        except Exception as e:
            print(f"Error fetching messages: {e}")
        
        total_messages += 200

    return messages


# Final Filter
subscribed = filters.create(is_subscribed)
