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


# ====================== DECODE LINK (ORIGINAL LOGIC) ======================
async def decode_link(encoded_string: str):
    """
    Decode karo base64 string ko.
    
    Formats:
    1. HACKHEIST-{user_id}-{f_msg_id*43}-{channel_id*43}
    2. get-{channel_id*43}-{f_msg_id*43}
    3. get-{channel_id*43}-{f_msg_id*43}-{s_msg_id*43}
    
    Note: channel_id*43 negative ho sakta hai (-1001234... * 43)
          toh split("-") se zyada parts aa sakte hain
    """
    # Padding fix karo
    encoded_string = encoded_string + "=" * (-len(encoded_string) % 4)
    
    try:
        string_bytes = base64.urlsafe_b64decode(encoded_string)
        decoded_string = string_bytes.decode("ascii")
    except Exception:
        raise ValueError("Invalid base64 string")

    print(f"DEBUG decoded_string: {decoded_string}")

    # ─── HACKHEIST Format ───
    if decoded_string.startswith("HACKHEIST-"):
        # HACKHEIST-{user_id}-{f_msg_id*43}-{channel_id*43}
        # Channel ID negative hai toh: HACKHEIST-123-456--5678
        rest = decoded_string[len("HACKHEIST-"):]  # Remove "HACKHEIST-"
        
        try:
            # Smart split - negative numbers handle karo
            numbers = _extract_numbers(rest)
            
            if len(numbers) < 3:
                raise ValueError(f"Expected 3 numbers, got {len(numbers)}")
            
            user_id = numbers[0]
            f_msg_id = numbers[1] // 43
            channel_id = numbers[2] // 43
            
            return "HACKHEIST", user_id, f_msg_id, channel_id, None
            
        except Exception as e:
            raise ValueError(f"Invalid HACKHEIST link: {e}")

    # ─── Batch Format (get-...) ───
    elif decoded_string.startswith("get-"):
        rest = decoded_string[len("get-"):]  # Remove "get-"
        
        try:
            numbers = _extract_numbers(rest)
            
            if len(numbers) < 2:
                raise ValueError(f"Expected at least 2 numbers, got {len(numbers)}")
            
            channel_id = numbers[0] // 43
            f_msg_id = numbers[1] // 43
            s_msg_id = numbers[2] // 43 if len(numbers) > 2 else None
            
            return "batch", None, f_msg_id, channel_id, s_msg_id
            
        except Exception as e:
            raise ValueError(f"Invalid batch link: {e}")

    else:
        raise ValueError(f"Unknown link type: {decoded_string[:20]}...")


def _extract_numbers(text: str) -> list:
    """
    String se numbers extract karo.
    Handles negative numbers properly.
    
    "123-456--5678" → [123, 456, -5678]
    "-5678-123-456" → [-5678, 123, 456]
    "123-456-789" → [123, 456, 789]
    """
    numbers = []
    current = ""
    i = 0
    
    while i < len(text):
        char = text[i]
        
        if char == '-':
            # Check: yeh negative sign hai ya separator?
            if current:
                # Current number complete hai, save karo
                numbers.append(int(current))
                current = ""
                
                # Next char digit hai ya minus hai?
                if i + 1 < len(text) and text[i + 1] == '-':
                    # Double dash = separator + negative number
                    current = "-"
                    i += 2
                    continue
                else:
                    # Single dash = just separator
                    i += 1
                    continue
            else:
                # Start of negative number
                current = "-"
                i += 1
                continue
        else:
            current += char
            i += 1
    
    # Last number
    if current and current != "-":
        numbers.append(int(current))
    
    return numbers


# ====================== ENCODE LINK (ORIGINAL LOGIC) ======================
async def encode_link(
    user_id: int = None,
    f_msg_id: int = None,
    s_msg_id: int = None,
    channel_id: int = None
) -> str:
    """
    Encode karo link ko base64 mein.
    
    Individual: HACKHEIST-{user_id}-{f_msg_id*43}-{channel_id*43}
    Batch:      get-{channel_id*43}-{f_msg_id*43}-{s_msg_id*43}
    """
    if channel_id is None or f_msg_id is None:
        raise ValueError("channel_id and f_msg_id required")

    channel_id_encoded = channel_id * 43
    f_msg_id_encoded = f_msg_id * 43
    s_msg_id_encoded = s_msg_id * 43 if s_msg_id is not None else None

    if user_id is not None and s_msg_id is None:
        # Individual file link (HACKHEIST)
        raw_string = f"HACKHEIST-{user_id}-{f_msg_id_encoded}-{channel_id_encoded}"
    elif s_msg_id is not None:
        # Batch link
        raw_string = f"get-{channel_id_encoded}-{f_msg_id_encoded}-{s_msg_id_encoded}"
    else:
        # Single file batch
        raw_string = f"get-{channel_id_encoded}-{f_msg_id_encoded}"

    string_bytes = raw_string.encode("ascii")
    base64_bytes = base64.urlsafe_b64encode(string_bytes)
    base64_string = base64_bytes.decode("ascii").rstrip("=")
    return base64_string


# ====================== IS SUBSCRIBED ======================
async def is_subscribed(filter, client, update):
    """
    Force sub check.
    Priority:
    1. ADMINS → always True
    2. Clone config FORCE_SUB keys
    3. clone.force_subs list
    4. Global config
    """
    if not update.from_user:
        return False

    user_id = update.from_user.id

    # Admins skip
    if user_id in ADMINS:
        return True

    # ─── Force channels collect karo ───
    force_channels = []

    # 1. Clone config mein FORCE_SUB keys?
    if hasattr(client, 'clone_config') and client.clone_config:
        cfg = client.clone_config
        config_channels = [
            cfg.get('FORCE_SUB_CHANNEL'),
            cfg.get('FORCE_SUB_CHANNEL2'),
            cfg.get('FORCE_SUB_CHANNEL3'),
            cfg.get('FORCE_SUB_CHANNEL4'),
        ]
        config_channels = [ch for ch in config_channels if ch and ch != 0]
        if config_channels:
            force_channels = config_channels

    # 2. Clone ki force_subs list
    if not force_channels:
        if hasattr(client, 'force_subs') and client.force_subs:
            force_channels = [
                ch for ch in client.force_subs if ch and ch != 0
            ]

    # 3. Global config fallback
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

    # Koi channel nahi → subscribed
    if not force_channels:
        return True

    # ─── Check karo ───
    for channel in force_channels:
        try:
            member = await client.get_chat_member(
                chat_id=channel,
                user_id=user_id
            )
            if member.status not in [
                ChatMemberStatus.OWNER,
                ChatMemberStatus.ADMINISTRATOR,
                ChatMemberStatus.MEMBER
            ]:
                return False

        except UserNotParticipant:
            return False

        except (ChannelInvalid, ChatAdminRequired) as e:
            print(f"Force sub skip {channel}: {e}")
            continue

        except Exception as e:
            print(f"Force sub error {channel}: {e}")
            continue

    return True


# ====================== GET MESSAGES ======================
async def get_messages(client, message_ids, channel_id):
    """Messages fetch karo channel se"""
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

        except MessageIdsInvalid:
            print(f"Invalid message IDs: {batch}")

        except Exception as e:
            print(f"Get messages error: {e}")

        total += 200

    return messages


# ====================== FILTER ======================
subscribed = filters.create(is_subscribed)
