import random
import os
import asyncio
import humanize
import time
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import (
    Message, InlineKeyboardMarkup,
    InlineKeyboardButton, CallbackQuery
)
from pyrogram.errors import (
    FloodWait, UserIsBlocked,
    InputUserDeactivated, ChannelInvalid,
    PeerIdInvalid, ChatAdminRequired
)
from pyrogram.errors.exceptions.bad_request_400 import BadRequest
from bot import Bot
from config import (
    ADMINS, FILE_AUTO_DELETE, CUSTOM_CAPTION,
    PROTECT_CONTENT, DISABLE_CHANNEL_BUTTON,
    FORCE_MSG, START_MSG, CHANNEL_ID
)
from helper_func import subscribed, encode_link, decode_link, get_messages
from database.database import (
    add_user, del_user, full_userbase, present_user,
    add_special_message, remove_special_message,
    get_special_messages, get_all_special_messages,
    add_scheduled_broadcast, get_active_scheduled_broadcasts,
    deactivate_scheduled_broadcast, delete_scheduled_broadcast,
    get_schedule_by_id, update_schedule_start_time
)

# Delete times
BULK_DELETE_TIME = FILE_AUTO_DELETE
try:
    from config import INDIVIDUAL_AUTO_DELETE
    INDIVIDUAL_DELETE_TIME = INDIVIDUAL_AUTO_DELETE
except ImportError:
    INDIVIDUAL_DELETE_TIME = FILE_AUTO_DELETE

# Scheduled broadcast tasks tracker
scheduled_broadcast_tasks = {}


# ====================== CONFIG HELPER ======================
def get_cfg(client, key, default=None):
    """
    Priority: Clone Config > Global Config
    """
    if hasattr(client, 'clone_config') and client.clone_config:
        val = client.clone_config.get(key)
        if val is not None:
            return val
    # Global config se
    import config as cfg
    return getattr(cfg, key, default)


# ====================== DB CHANNEL HELPER ======================
async def get_db_channel(client):
    """
    Clone bots ka db_channel main bot se lo
    """
    # Agar client ka apna db_channel hai
    if hasattr(client, 'db_channel') and client.db_channel:
        return client.db_channel

    # Clone hai - main bot ka channel use karo
    try:
        from bot import CLONE_BOTS
        main_bot = CLONE_BOTS.get("main")
        if main_bot and hasattr(main_bot, 'db_channel') and main_bot.db_channel:
            return main_bot.db_channel
    except Exception:
        pass

    # Direct fetch karo
    try:
        channel = await client.get_chat(CHANNEL_ID)
        return channel
    except Exception as e:
        print(f"DB Channel fetch failed: {e}")
        return None


# ====================== SPECIAL MESSAGE ======================
async def send_random_special_message(client: Client, chat_id: int):
    bot_id = getattr(client, 'username', 'unknown')
    special_msg_ids = await get_special_messages(bot_id)

    if not special_msg_ids:
        print(f"No special messages for bot {bot_id}")
        return None

    db_channel = await get_db_channel(client)
    if not db_channel:
        print("DB Channel not available for special message")
        return None

    random_msg_id = random.choice(special_msg_ids)
    try:
        special_msg = await client.get_messages(db_channel.id, random_msg_id)
        if not special_msg:
            return None

        caption = f"<b>{special_msg.caption.html}</b>" if special_msg.caption else None

        if special_msg.sticker:
            return await client.send_sticker(chat_id=chat_id, sticker=special_msg.sticker.file_id)
        elif special_msg.photo:
            return await client.send_photo(chat_id=chat_id, photo=special_msg.photo.file_id, caption=caption, parse_mode=ParseMode.HTML)
        elif special_msg.video:
            return await client.send_video(chat_id=chat_id, video=special_msg.video.file_id, caption=caption, parse_mode=ParseMode.HTML)
        elif special_msg.document:
            return await client.send_document(chat_id=chat_id, document=special_msg.document.file_id, caption=caption, parse_mode=ParseMode.HTML)
        elif special_msg.audio:
            return await client.send_audio(chat_id=chat_id, audio=special_msg.audio.file_id, caption=caption, parse_mode=ParseMode.HTML)
        elif special_msg.animation:
            return await client.send_animation(chat_id=chat_id, animation=special_msg.animation.file_id, caption=caption, parse_mode=ParseMode.HTML)
        elif special_msg.text:
            return await client.send_message(chat_id=chat_id, text=special_msg.text, parse_mode=ParseMode.HTML)
        else:
            return None
    except Exception as e:
        print(f"Special message failed {random_msg_id} for {bot_id}: {e}")
        return None


# ====================== DELETE FILES ======================
async def delete_files(msgs, client, message, info_msg, delete_time=None):
    if delete_time is None:
        delete_time = FILE_AUTO_DELETE
    await asyncio.sleep(delete_time)
    for msg in msgs:
        try:
            await client.delete_messages(
                chat_id=msg.chat.id,
                message_ids=[msg.id]
            )
        except Exception as e:
            print(f"Delete failed msg {msg.id}: {e}")


# ====================== SEND CONTENT HELPER ======================
async def send_content_to_user(client, message, messages_list, delete_time, is_individual=False, original_channel_id=None):
    """
    User ko messages bhejo aur delete schedule karo.
    
    Parameters:
        client: Pyrogram client
        message: original incoming message (for user context)
        messages_list: list of messages to send
        delete_time: seconds ke baad auto-delete
        is_individual: True for HACKHEIST (individual file), False for batch
        original_channel_id: batch link se decode kiya gaya channel_id (save button ke liye)
    """
    db_channel = await get_db_channel(client)
    if not db_channel:
        await message.reply_text("❌ Server error. Try again later.")
        return

    codeflix_msgs = []
    user_id = message.from_user.id

    for msg in messages_list:
        if not msg:
            continue

        # File info nikalna
        filename = "Unknown"
        media_type = "Unknown"

        if msg.video:
            media_type = "Video"
            filename = msg.video.file_name or "Unnamed Video"
        elif msg.document:
            filename = msg.document.file_name or "Unnamed Document"
            media_type = "PDF" if str(filename).endswith(".pdf") else "Document"
        elif msg.photo:
            media_type = "Image"
            filename = "Image"
        elif msg.text:
            media_type = "Text"
            filename = "Text Content"

        # Custom caption
        custom_caption = get_cfg(client, 'CUSTOM_CAPTION', CUSTOM_CAPTION)
        if custom_caption:
            try:
                caption = custom_caption.format(
                    previouscaption=(msg.caption.html if msg.caption else "🔥 HIDDENS 🔥"),
                    filename=filename,
                    mediatype=media_type,
                )
            except Exception:
                caption = msg.caption.html if msg.caption else ""
        else:
            caption = msg.caption.html if msg.caption else ""

        # ✅ Protect content – individual aur batch ke liye alag setting
        if is_individual:
            protect = get_cfg(client, 'PROTECT_CONTENT_INDIVIDUAL', PROTECT_CONTENT)
        else:
            protect = get_cfg(client, 'PROTECT_CONTENT_BATCH', PROTECT_CONTENT)

        disable_btn = get_cfg(client, 'DISABLE_CHANNEL_BUTTON', DISABLE_CHANNEL_BUTTON)

        # Buttons set karna
        reply_markup = None
        if not disable_btn:
            if is_individual:
                # Individual files ke liye original reply_markup rakho (ya kuch aur custom)
                reply_markup = msg.reply_markup if msg.reply_markup else None
            else:
                # Batch messages ke liye "Click to Save" button add karo
                bot_username = getattr(client, 'username', 'bot')
                # ✅ Original channel_id use karo (deep link se aaya hua), nahi to db_channel.id
                base64_string2 = await encode_link(
                    user_id=user_id,
                    f_msg_id=msg.id,
                    channel_id=original_channel_id if original_channel_id else db_channel.id
                )
                individual_button = InlineKeyboardButton(
                    "😁 𝗖𝗟𝗜𝗖𝗞 𝗧𝗢 𝗦𝗔𝗩𝗘 📥",
                    url=f"https://t.me/{bot_username}?start={base64_string2}"
                )
                if msg.reply_markup and hasattr(msg.reply_markup, 'inline_keyboard'):
                    new_kb = msg.reply_markup.inline_keyboard.copy()
                    new_kb.append([individual_button])
                    reply_markup = InlineKeyboardMarkup(new_kb)
                else:
                    reply_markup = InlineKeyboardMarkup([[individual_button]])

        # Message copy karna
        try:
            copied = await msg.copy(
                chat_id=user_id,
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup,
                protect_content=protect,
            )
            if copied:
                codeflix_msgs.append(copied)
        except FloodWait as e:
            await asyncio.sleep(e.x)
            try:
                copied = await msg.copy(
                    chat_id=user_id,
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup,
                    protect_content=protect,
                )
                if copied:
                    codeflix_msgs.append(copied)
            except Exception as e2:
                print(f"Send failed after flood: {e2}")
        except Exception as e:
            print(f"Send failed: {e}")

    return codeflix_msgs

# ====================== START COMMAND (SUBSCRIBED) ======================
@Bot.on_message(filters.command('start') & filters.private & subscribed)
async def start_command(client: Client, message: Message):
    user_id = message.from_user.id

    # User add karo database mein
    if not await present_user(user_id):
        try:
            await add_user(user_id)
        except Exception as e:
            print(f"Add user error {user_id}: {e}")

    text = message.text

    # Deep link hai?
    if len(text) > 7:
        try:
            base64_string = text.split(" ", 1)[1]
        except IndexError:
            return

        try:
            link_type, link_user_id, f_msg_id, channel_id, s_msg_id = await decode_link(base64_string)
        except ValueError as e:
            await message.reply_text(f"❌ Invalid link: {str(e)}")
            return

        db_channel = await get_db_channel(client)
        if not db_channel:
            await message.reply_text("❌ Server error. Try again.")
            return

        # ── HACKHEIST (Individual file) ──
        if link_type == "HACKHEIST":
            if user_id != link_user_id:
                await message.reply_text("❌ You are not authorized!")
                return

            temp_msg = await message.reply("𝗥𝘂𝗸 𝗘𝗸 𝗦𝗲𝗰 👽..")
            try:
                messages = await get_messages(client, [f_msg_id], channel_id)
                if not messages or all(m is None for m in messages):
                    await temp_msg.edit("❌ Message not found or deleted.")
                    return
            except Exception as e:
                await temp_msg.edit(f"❌ Error: {str(e)}")
                return
            finally:
                try:
                    await temp_msg.delete()
                except Exception:
                    pass

            codeflix_msgs = await send_content_to_user(
                client, message, messages,
                INDIVIDUAL_DELETE_TIME, is_individual=True,
                original_channel_id=channel_id
            )

            if not codeflix_msgs:
                return

            special = await send_random_special_message(client, user_id)
            if special:
                codeflix_msgs.append(special)

            info_msg = await client.send_message(
                chat_id=user_id,
                text=(
                    "<b>‼️ 𝐓𝐡𝐢𝐬 𝐋𝐄𝐂𝐓𝐔𝐑𝐄/𝐏𝐃𝐅 𝐰𝐢𝐥𝐥 𝐛𝐞 "
                    "<u>𝗮𝘂𝘁𝗼-𝗱𝗲𝗹𝗲𝘁𝗲𝗱 𝗶𝗻 𝟯 𝗱𝗮𝘆𝘀</u> 💀</b>\n\n"
                    "<b>⚡ Watch now or Save it before time runs out!</b>\n\n"
                    "<b>🤝 Share with friends ❣️</b>\n\n"
                    "<b><a href='https://yashyasag.github.io/hiddens_officials'>"
                    "✨ 𝗘𝘅𝗽𝗹𝗼𝗿𝗲 𝗠𝗼𝗿𝗲 𝗪𝗲𝗯𝘀𝗶𝘁𝗲𝘀 ✨</a></b>"
                ),
            )
            codeflix_msgs.append(info_msg)
            asyncio.create_task(
                delete_files(codeflix_msgs, client, message, info_msg, INDIVIDUAL_DELETE_TIME)
            )
            return

        # ── BATCH ──
        elif link_type == "batch":
            if s_msg_id is not None:
                ids = list(range(f_msg_id, s_msg_id + 1)) if f_msg_id <= s_msg_id \
                    else list(range(f_msg_id, s_msg_id - 1, -1))
            else:
                ids = [f_msg_id]

            temp_msg = await message.reply("𝗥𝘂𝗸 𝗘𝗸 𝗦𝗲𝗰 👽..")
            try:
                messages = await get_messages(client, ids, channel_id)
                if not messages or all(m is None for m in messages):
                    await temp_msg.edit("❌ Messages not found or deleted.")
                    return
            except Exception as e:
                await temp_msg.edit(f"❌ Error: {str(e)}")
                return
            finally:
                try:
                    await temp_msg.delete()
                except Exception:
                    pass

            codeflix_msgs = await send_content_to_user(
                client, message, messages,
                BULK_DELETE_TIME, is_individual=False
            )

            if not codeflix_msgs:
                return

            special = await send_random_special_message(client, user_id)
            if special:
                codeflix_msgs.append(special)

            info_msg = await client.send_message(
                chat_id=user_id,
                text=(
                    "<b>🔥 Hurry! These will be "
                    "<u>deleted in 4 hours</u> ⏳</b>\n\n"
                    "<b>Click (😁 𝗖𝗟𝗜𝗖𝗞 𝗧𝗢 𝗦𝗔𝗩𝗘 📥) to save!</b>\n\n"
                    "<b>😎 Re-access anytime on our websites!</b>\n\n"
                    "<b><a href='https://yashyasag.github.io/hiddens_officials'>"
                    "🌟 𝗩𝗶𝘀𝗶𝘁 𝗠𝗼𝗿𝗲 𝗪𝗲𝗯𝘀𝗶𝘁𝗲𝘀 🌟</a></b>"
                ),
            )
            codeflix_msgs.append(info_msg)
            asyncio.create_task(
                delete_files(codeflix_msgs, client, message, info_msg, BULK_DELETE_TIME)
            )
            return

    # ── Normal /start ──
    start_msg = get_cfg(client, 'START_MSG', START_MSG)
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔥 𝗠𝗔𝗜𝗡 𝗪𝗘𝗕𝗦𝗜𝗧𝗘 🔥",
                              url="https://yashyasag.github.io/hiddens_officials")],
        [InlineKeyboardButton("‼️ 𝗕𝗔𝗖𝗞𝗨𝗣 𝗖𝗛𝗔𝗡𝗡𝗘𝗟 ‼️",
                              url="https://t.me/+Sk3pfX_PWTQ3NmI1")],
        [InlineKeyboardButton("👻 ᴄᴏɴᴛᴀᴄᴛ ᴜs 👻",
                              url="https://t.me/TEAM_HIDDENS_BOT")]
    ])

    try:
        await message.reply_text(
            text=start_msg.format(
                first=message.from_user.first_name,
                last=message.from_user.last_name or "",
                username=f"@{message.from_user.username}" if message.from_user.username else "",
                mention=message.from_user.mention,
                id=message.from_user.id
            ),
            reply_markup=reply_markup,
            disable_web_page_preview=True,
            quote=True
        )
    except Exception as e:
        print(f"Start message error: {e}")
        await message.reply_text("Welcome! 👋", quote=True)


# ====================== NOT JOINED ======================
@Bot.on_message(filters.command('start') & filters.private)
async def not_joined(client: Client, message: Message):
    user_id = message.from_user.id

    if not await present_user(user_id):
        try:
            await add_user(user_id)
        except Exception as e:
            print(f"Add user error: {e}")

    bot_username = getattr(client, 'username', None)
    if not bot_username:
        try:
            me = await client.get_me()
            bot_username = me.username
        except Exception:
            bot_username = "bot"

    # Invite links - clone ya main
    inv1 = getattr(client, 'invitelink', "https://t.me/+channel1")
    inv2 = getattr(client, 'invitelink2', "https://t.me/+channel2")
    inv3 = getattr(client, 'invitelink3', "https://t.me/+channel3")
    inv4 = getattr(client, 'invitelink4', "https://t.me/+something")

    buttons = [
        [InlineKeyboardButton("😈 𝗢𝗣𝗠𝗔𝗦𝗧𝗘𝗥𝗦 💀", url=inv4)],
        [
            InlineKeyboardButton("🌟 𝗝𝗼𝗶𝗻 𝟭𝘀𝘁 🌟", url=inv1),
            InlineKeyboardButton("💝 𝗝𝗼𝗶𝗻 𝟮𝗻𝗱 💝", url=inv2),
        ],
        [InlineKeyboardButton("🕊 𝗝𝗼𝗶𝗻 𝟯𝗿𝗱 🕊", url=inv3)]
    ]

    try:
        buttons.append([
            InlineKeyboardButton(
                '♻️ 𝐓𝐑𝐘 𝐀𝐆𝐀𝐈𝐍 ♻️',
                url=f"https://t.me/{bot_username}?start={message.command[1]}"
            )
        ])
    except IndexError:
        pass

    force_msg = get_cfg(client, 'FORCE_MSG', FORCE_MSG)

    try:
        await message.reply(
            text=force_msg.format(
                first=message.from_user.first_name,
                last=message.from_user.last_name or "",
                username=f"@{bot_username}" if bot_username else "",
                mention=message.from_user.mention,
                id=user_id
            ),
            reply_markup=InlineKeyboardMarkup(buttons),
            quote=True,
            disable_web_page_preview=True
        )
    except Exception as e:
        print(f"Force msg error: {e}")
        await message.reply("Please join our channels first!", quote=True)


# ====================== USERS COUNT ======================
@Bot.on_message(filters.command('users') & filters.private & filters.user(ADMINS))
async def get_users(client: Bot, message: Message):
    msg = await client.send_message(chat_id=message.chat.id, text="Processing...")
    users = await full_userbase()
    await msg.edit(f"<b>{len(users)} Users</b> are using this bot.")


# ====================== SPECIAL MESSAGES ======================
@Bot.on_message(filters.command('add_random_message') & filters.private & filters.user(ADMINS))
async def add_random_message(client: Bot, message: Message):
    bot_id = client.username
    try:
        msg_id = int(message.text.split(" ", 1)[1])
        await add_special_message(msg_id, bot_id)
        await message.reply_text(f"✅ Added ID `{msg_id}` for `{bot_id}`")
    except IndexError:
        await message.reply_text("❌ Usage: `/add_random_message <msg_id>`")
    except ValueError:
        await message.reply_text("❌ Msg ID number hona chahiye.")


@Bot.on_message(filters.command('remove_random_message') & filters.private & filters.user(ADMINS))
async def remove_random_message(client: Bot, message: Message):
    bot_id = client.username
    try:
        msg_id = int(message.text.split(" ", 1)[1])
        await remove_special_message(msg_id, bot_id)
        await message.reply_text(f"✅ Removed ID `{msg_id}` from `{bot_id}`")
    except IndexError:
        await message.reply_text("❌ Usage: `/remove_random_message <msg_id>`")
    except ValueError:
        await message.reply_text("❌ Msg ID number hona chahiye.")


@Bot.on_message(filters.command('list_random_messages') & filters.private & filters.user(ADMINS))
async def list_random_messages(client: Bot, message: Message):
    bot_id = client.username
    msg_ids = await get_special_messages(bot_id)

    response = f"<b>📩 Special Messages for `{bot_id}`:</b>\n\n"
    if msg_ids:
        response += f"IDs: `{', '.join(map(str, msg_ids))}`\n\n"
    else:
        response += "Koi message nahi hai.\n\n"

    all_msgs = await get_all_special_messages()
    others = [d for d in all_msgs if d['_id'] != f"{bot_id}_special_msg_ids"]
    if others:
        response += "<b>Other Bots (Read-Only):</b>\n"
        for doc in others:
            other_id = doc['_id'].replace("_special_msg_ids", "")
            ids = doc.get('msg_ids', [])
            response += f"• `{other_id}`: `{', '.join(map(str, ids)) if ids else 'None'}`\n"

    await message.reply(response)


# ====================== BROADCAST ======================
@Bot.on_message(filters.private & filters.command('broadcast') & filters.user(ADMINS))
async def send_text(client: Bot, message: Message):
    if not message.reply_to_message:
        msg = await message.reply("❌ Kisi message ko reply karo broadcast ke liye.")
        await asyncio.sleep(8)
        return await msg.delete()

    try:
        seconds = int(message.text.split(maxsplit=1)[1])
    except (IndexError, ValueError):
        seconds = None

    query = await full_userbase()
    broadcast_msg = message.reply_to_message
    total = successful = blocked = deleted = unsuccessful = 0
    sent_messages = []

    pls_wait = await message.reply("<i>Broadcast processing...</i>")

    for chat_id in query:
        try:
            sent = await broadcast_msg.copy(chat_id)
            sent_messages.append((chat_id, sent.id))
            successful += 1
        except FloodWait as e:
            await asyncio.sleep(e.x)
            try:
                sent = await broadcast_msg.copy(chat_id)
                sent_messages.append((chat_id, sent.id))
                successful += 1
            except Exception:
                unsuccessful += 1
        except UserIsBlocked:
            await del_user(chat_id)
            blocked += 1
        except InputUserDeactivated:
            await del_user(chat_id)
            deleted += 1
        except Exception:
            unsuccessful += 1
        total += 1

    await pls_wait.edit(
        f"<b>✅ Broadcast Done!\n\n"
        f"Total: {total}\n"
        f"Success: {successful}\n"
        f"Blocked: {blocked}\n"
        f"Deleted: {deleted}\n"
        f"Failed: {unsuccessful}</b>"
    )

    if seconds:
        await asyncio.sleep(seconds)
        for chat_id, msg_id in sent_messages:
            try:
                await client.delete_messages(chat_id, msg_id)
            except Exception:
                pass


# ====================== SCHEDULED BROADCAST ======================
async def perform_broadcast_cycle(client, chat_id, msg_id, delete_after, schedule_id, admin_chat_id):
    query = await full_userbase()
    sent_messages = []
    total = successful = blocked = deleted = unsuccessful = 0

    try:
        broadcast_msg = await client.get_messages(chat_id, msg_id)
    except Exception as e:
        print(f"Fetch error {msg_id}: {e}")
        return

    for user_id in query:
        try:
            sent = await broadcast_msg.copy(user_id)
            sent_messages.append((user_id, sent.id))
            successful += 1
        except FloodWait as e:
            await asyncio.sleep(e.x)
            try:
                sent = await broadcast_msg.copy(user_id)
                sent_messages.append((user_id, sent.id))
                successful += 1
            except Exception:
                unsuccessful += 1
        except UserIsBlocked:
            await del_user(user_id)
            blocked += 1
        except InputUserDeactivated:
            await del_user(user_id)
            deleted += 1
        except Exception:
            unsuccessful += 1
        total += 1

    try:
        await client.send_message(
            admin_chat_id,
            f"<b>📊 Broadcast Cycle: {schedule_id}</b>\n\n"
            f"Total: {total} | Success: {successful}\n"
            f"Blocked: {blocked} | Deleted: {deleted} | Failed: {unsuccessful}"
        )
    except Exception:
        pass

    if delete_after > 0:
        await asyncio.sleep(delete_after)
        for uid, mid in sent_messages:
            try:
                await client.delete_messages(uid, mid)
            except Exception:
                pass


async def start_scheduled_broadcast(client, schedule_id):
    schedule = await get_schedule_by_id(schedule_id)
    if not schedule:
        return

    admin_chat_id = schedule['admin_chat_id']
    chat_id = schedule['chat_id']
    reply_msg_id = schedule['reply_msg_id']
    total_time = schedule['total_time']
    interval = schedule['interval']
    delete_after = schedule['delete_after']
    start_time = schedule['start_time']
    start_delay = schedule.get('start_delay', 0)

    if start_delay > 0:
        try:
            await client.send_message(
                admin_chat_id,
                f"⏳ Broadcast `{schedule_id}` starts in {humanize.naturaldelta(start_delay)}."
            )
        except Exception:
            pass
        await asyncio.sleep(start_delay)

    while True:
        current = await get_schedule_by_id(schedule_id)
        if not current or not current.get('active', False):
            break

        elapsed = time.time() - start_time - start_delay
        if elapsed >= total_time:
            await deactivate_scheduled_broadcast(schedule_id)
            try:
                await client.send_message(admin_chat_id, f"✅ Broadcast `{schedule_id}` ended.")
            except Exception:
                pass
            break

        await perform_broadcast_cycle(
            client, chat_id, reply_msg_id,
            delete_after, schedule_id, admin_chat_id
        )
        await asyncio.sleep(interval)


@Bot.on_message(filters.private & filters.command('broadcast_add') & filters.user(ADMINS))
async def broadcast_add(client: Bot, message: Message):
    if not message.reply_to_message:
        await message.reply("❌ Reply to a message first.")
        return

    try:
        parts = message.text.split(" ", 1)[1].split(":")
        if len(parts) not in [3, 4]:
            await message.reply(
                "❌ Usage: `/broadcast_add total:interval:delete[:{delay}]`\n"
                "Example: `/broadcast_add 86400:3600:600:3600`"
            )
            return

        total_time, interval, delete_after = map(int, parts[:3])
        start_delay = int(parts[3]) if len(parts) == 4 else 0

    except (ValueError, IndexError):
        await message.reply("❌ Invalid format.")
        return

    bot_id = client.username
    schedule_id = await add_scheduled_broadcast(
        admin_chat_id=message.chat.id,
        chat_id=message.chat.id,
        reply_msg_id=message.reply_to_message.id,
        total_time=total_time,
        interval=interval,
        delete_after=delete_after,
        start_delay=start_delay,
        bot_id=bot_id
    )

    task = asyncio.create_task(start_scheduled_broadcast(client, schedule_id))
    scheduled_broadcast_tasks[schedule_id] = task

    await message.reply(
        f"✅ **Scheduled!**\n"
        f"ID: `{schedule_id}`\n"
        f"Total: {humanize.naturaldelta(total_time)}\n"
        f"Interval: {humanize.naturaldelta(interval)}\n"
        f"Delete After: {humanize.naturaldelta(delete_after)}\n"
        f"Delay: {humanize.naturaldelta(start_delay) if start_delay else 'Immediate'}"
    )


@Bot.on_message(filters.private & filters.command('broadcast_remove') & filters.user(ADMINS))
async def broadcast_remove(client: Bot, message: Message):
    bot_id = client.username
    try:
        schedule_id = message.text.split(" ", 1)[1]
        schedule = await get_schedule_by_id(schedule_id)

        if not schedule:
            await message.reply(f"❌ ID `{schedule_id}` not found.")
            return
        if schedule.get('bot_id') != bot_id:
            await message.reply("❌ Yeh schedule is bot ka nahi hai.")
            return

        await deactivate_scheduled_broadcast(schedule_id)
        task = scheduled_broadcast_tasks.get(schedule_id)
        if task and not task.done():
            task.cancel()
        scheduled_broadcast_tasks.pop(schedule_id, None)

        await message.reply(f"✅ Removed `{schedule_id}`")

    except IndexError:
        schedules = await get_active_scheduled_broadcasts(bot_id)
        if not schedules:
            await message.reply("❌ Koi active broadcast nahi.")
            return

        text = f"<b>Active Broadcasts for {bot_id}:</b>\n\n"
        for s in schedules:
            text += f"• ID: `{s['_id']}` | {humanize.naturaldelta(s['total_time'])}\n"
        text += "\nUse: `/broadcast_remove <id>`"
        await message.reply(text)


@Bot.on_message(filters.private & filters.command('resume') & filters.user(ADMINS))
async def resume_broadcast(client: Bot, message: Message):
    bot_id = client.username
    try:
        parts = message.text.split(" ", 1)[1].split(":")
        schedule_id = parts[0]
        start_delay = int(parts[1]) if len(parts) > 1 else None
    except (IndexError, ValueError):
        await message.reply("❌ Usage: `/resume <id>[:{delay}]`")
        return

    schedule = await get_schedule_by_id(schedule_id)
    if not schedule:
        await message.reply(f"❌ `{schedule_id}` not found.")
        return
    if schedule.get('bot_id') != bot_id:
        await message.reply("❌ Yeh schedule is bot ka nahi.")
        return
    if schedule.get('active'):
        await message.reply("⚠️ Already active hai.")
        return

    from database.database import scheduled_broadcasts
    new_start = time.time()
    update_data = {'active': True, 'start_time': new_start}
    if start_delay is not None:
        update_data['start_delay'] = start_delay

    scheduled_broadcasts.update_one({'_id': schedule_id}, {'$set': update_data})

    task = asyncio.create_task(start_scheduled_broadcast(client, schedule_id))
    scheduled_broadcast_tasks[schedule_id] = task

    await message.reply(f"✅ Resumed `{schedule_id}`!")
