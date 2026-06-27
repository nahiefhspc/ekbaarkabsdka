from pyrogram import filters
from pyrogram.types import Message
from bot import Bot, CLONE_BOTS
from config import OWNER_ID
from database.database import (
    add_clone,
    remove_clone,
    get_all_clones,
    update_clone_config,
    update_clone_force_subs,
    get_clone_by_partial_token
)
import asyncio

# Pending configs - jo bots abhi config wait kar rahe hain
# Structure: { token: { 'config': {}, 'step': 'waiting_config' } }
PENDING_BOTS = {}


# ====================== ADD CLONE ======================
@Bot.on_message(filters.command("add_bot") & filters.user(OWNER_ID) & filters.private)
async def add_clone_bot(client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            "❌ **Usage:** `/add_bot <token>`",
            quote=True
        )

    token = message.command[1].strip()

    # Token valid hai?
    if ":" not in token:
        return await message.reply_text(
            "❌ **Invalid Token!**\nFormat: `123456:ABC-DEF...`",
            quote=True
        )

    # Database mein pehle se hai?
    existing = None
    all_clones = await get_all_clones()
    for c in all_clones:
        if c['token'] == token:
            existing = c
            break

    if existing:
        # Already hai - config bhi hai?
        existing_config = existing.get('config', {})

        if existing_config:
            # Config hai - seedha start karo
            if token in CLONE_BOTS:
                return await message.reply_text(
                    f"⚠️ **Yeh bot already running hai!**\n"
                    f"Token: `{token[-8:]}`\n\n"
                    f"Config dekhne ke liye: `/clone_info {token[-8:]}`",
                    quote=True
                )

            await message.reply_text(
                f"✅ **Bot DB mein already hai!**\n"
                f"Saved config ke saath start ho raha hai...\n\n"
                f"**Config ({len(existing_config)} keys):**\n" +
                "\n".join([f"• `{k}` = `{v}`" for k, v in existing_config.items()]),
                quote=True
            )
            await _start_clone_now(client, message, token, existing)
        else:
            # Config nahi hai - config maango
            PENDING_BOTS[token] = {'config': {}, 'step': 'waiting_config'}
            await message.reply_text(
                f"⚠️ **Bot DB mein hai lekin config nahi hai!**\n\n"
                f"**Config bhejo is format mein:**\n"
                f"`PROTECT_CONTENT=True`\n"
                f"`FORCE_SUB_CHANNEL=-100xxx`\n"
                f"`START_MSG=Hello Welcome`\n\n"
                f"Ya skip karna ho toh likhो: `skip`\n"
                f"_(Skip karne par main bot ka config use hoga)_",
                quote=True
            )
    else:
        # Naya bot - save karo aur config maango
        await add_clone(token, OWNER_ID, force_subs=[], config={})
        PENDING_BOTS[token] = {'config': {}, 'step': 'waiting_config'}

        await message.reply_text(
            f"✅ **Token Saved!** `{token[-8:]}`\n\n"
            f"**Ab config bhejo** (ek message mein):\n\n"
            f"`PROTECT_CONTENT=True`\n"
            f"`FORCE_SUB_CHANNEL=-100356565653`\n"
            f"`START_MSG=Hello Welcome!`\n\n"
            f"Ya skip karna ho toh likhो: `skip`\n"
            f"_(Skip karne par main bot ka config use hoga)_",
            quote=True
        )


# ====================== CONFIG RECEIVE HANDLER ======================
@Bot.on_message(filters.user(OWNER_ID) & filters.private & filters.text)
async def handle_pending_config(client, message: Message):
    """Pending bot ka config receive karna"""
    text = message.text.strip()

    # Check karo koi pending bot hai?
    if not PENDING_BOTS:
        return  # Koi pending nahi

    # Commands ignore karo
    if text.startswith('/'):
        return

    # Find karo pending bot
    pending_token = None
    for token, data in PENDING_BOTS.items():
        if data.get('step') == 'waiting_config':
            pending_token = token
            break

    if not pending_token:
        return

    clone = None
    all_clones = await get_all_clones()
    for c in all_clones:
        if c['token'] == pending_token:
            clone = c
            break

    if not clone:
        del PENDING_BOTS[pending_token]
        return

    # Skip check
    if text.lower() == 'skip':
        del PENDING_BOTS[pending_token]
        await message.reply_text(
            f"⏭️ **Config Skip Kiya!**\n"
            f"Token: `{pending_token[-8:]}`\n\n"
            f"Main bot ka config use hoga.\n"
            f"Bot start ho raha hai...",
            quote=True
        )
        await _start_clone_now(client, message, pending_token, clone)
        return

    # Config parse karo
    lines = text.strip().split('\n')
    parsed_config = {}
    failed_keys = []

    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        if '=' not in line:
            failed_keys.append(f"`{line}` (= missing)")
            continue

        key, value = line.split('=', 1)
        key = key.strip().upper()
        value = value.strip()

        if not key:
            continue

        # Type conversion
        if value.lower() == 'true':
            parsed_config[key] = True
        elif value.lower() == 'false':
            parsed_config[key] = False
        elif value.lower() in ['none', 'null', '']:
            parsed_config[key] = None
        else:
            try:
                parsed_config[key] = int(value)
            except ValueError:
                try:
                    parsed_config[key] = float(value)
                except ValueError:
                    parsed_config[key] = value

    if not parsed_config and not text.lower() == 'skip':
        return await message.reply_text(
            f"❌ **Koi valid config nahi mili!**\n\n"
            f"**Format:**\n"
            f"`KEY=VALUE`\n`KEY2=VALUE2`\n\n"
            f"Ya `skip` likhो.",
            quote=True
        )

    # Database mein save karo
    await update_clone_config(pending_token, parsed_config)

    # Pending se hatao
    del PENDING_BOTS[pending_token]

    # Response
    config_text = "\n".join([f"• `{k}` = `{v}`" for k, v in parsed_config.items()])
    response = (
        f"✅ **Config Saved!**\n\n"
        f"**Keys ({len(parsed_config)}):**\n{config_text}\n\n"
    )

    if failed_keys:
        response += f"⚠️ **Failed:**\n" + "\n".join(failed_keys) + "\n\n"

    response += "🚀 **Bot start ho raha hai...**"
    await message.reply_text(response, quote=True)

    # Clone start karo updated config ke saath
    updated_clone = clone.copy()
    updated_clone['config'] = parsed_config
    await _start_clone_now(client, message, pending_token, updated_clone)


# ====================== INTERNAL: START CLONE ======================
async def _start_clone_now(client, message, token: str, clone_data: dict):
    """Actually clone start karo"""
    force_subs = clone_data.get('force_subs', [])
    config = clone_data.get('config', {})

    try:
        clone_bot = Bot(
            bot_token=token,
            is_clone=True,
            force_subs=force_subs,
            clone_config=config
        )
        await clone_bot.start()
        CLONE_BOTS[token] = clone_bot

        await client.send_message(
            message.chat.id,
            f"✅ **Clone Bot Started!**\n\n"
            f"**Token:** `{token[-8:]}`\n"
            f"**Username:** @{clone_bot.username}\n"
            f"**Config Keys:** `{len(config)}`\n\n"
            f"Config update: `/set_config {token[-8:]}`\n"
            f"Info dekhna: `/clone_info {token[-8:]}`"
        )
        print(f"✅ Clone started: {token[-8:]}")

    except Exception as e:
        await client.send_message(
            message.chat.id,
            f"❌ **Clone Start Failed!**\n\n"
            f"Token: `{token[-8:]}`\n"
            f"Error: `{str(e)}`"
        )
        print(f"❌ Clone failed: {token[-8:]} → {e}")


# ====================== SET CONFIG + CLONE RESTART ======================
@Bot.on_message(filters.command("set_config") & filters.user(OWNER_ID) & filters.private)
async def set_clone_config(client, message: Message):
    """
    /set_config <last8>
    KEY1=VALUE1
    KEY2=VALUE2
    """
    full_text = message.text or message.caption or ""
    lines = full_text.strip().split('\n')

    if len(lines) < 2:
        return await message.reply_text(
            "❌ **Format:**\n\n"
            "`/set_config <last8>`\n"
            "`KEY1=VALUE1`\n"
            "`KEY2=VALUE2`\n\n"
            "**Example:**\n"
            "`/set_config abcdefgh`\n"
            "`PROTECT_CONTENT=True`\n"
            "`FORCE_SUB_CHANNEL=-100356565653`",
            quote=True
        )

    first_line_parts = lines[0].strip().split()
    if len(first_line_parts) < 2:
        return await message.reply_text("❌ **Token missing!**", quote=True)

    partial = first_line_parts[1].strip()

    clone = await get_clone_by_partial_token(partial)
    if not clone:
        return await message.reply_text(
            f"❌ **Clone `{partial}` not found!**\n`/list_bots`",
            quote=True
        )

    current_config = clone.get('config', {})
    updated_keys = []
    failed_keys = []

    for line in lines[1:]:
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        if '=' not in line:
            failed_keys.append(f"`{line}`")
            continue

        key, value = line.split('=', 1)
        key = key.strip().upper()
        value = value.strip()

        if not key:
            continue

        if value.lower() == 'true':
            current_config[key] = True
        elif value.lower() == 'false':
            current_config[key] = False
        elif value.lower() in ['none', 'null', '']:
            current_config[key] = None
        else:
            try:
                current_config[key] = int(value)
            except ValueError:
                try:
                    current_config[key] = float(value)
                except ValueError:
                    current_config[key] = value

        updated_keys.append(f"✅ `{key}` = `{current_config[key]}`")

    if not updated_keys:
        return await message.reply_text(
            "❌ **Koi valid config nahi!**\n" +
            ("\n".join(failed_keys) if failed_keys else ""),
            quote=True
        )

    # Save to database
    await update_clone_config(clone['token'], current_config)

    response = (
        f"✅ **Config Updated! `{partial}`**\n\n"
        f"**Updated:**\n" + "\n".join(updated_keys)
    )

    if failed_keys:
        response += "\n\n**⚠️ Failed:**\n" + "\n".join(failed_keys)

    response += f"\n\n**Total:** `{len(current_config)}` keys"

    token = clone['token']

    if token in CLONE_BOTS:
        response += "\n\n🔄 **Clone restart ho raha hai...**"
        await message.reply_text(response, quote=True)

        try:
            # Stop old
            old_clone = CLONE_BOTS[token]
            await old_clone.stop()
            del CLONE_BOTS[token]
            await asyncio.sleep(3)

            # Start new
            new_clone = Bot(
                bot_token=token,
                is_clone=True,
                force_subs=clone.get('force_subs', []),
                clone_config=current_config
            )
            await new_clone.start()
            CLONE_BOTS[token] = new_clone

            await client.send_message(
                message.chat.id,
                f"✅ **Clone Restarted!**\n"
                f"@{new_clone.username} naye config ke saath live hai!"
            )

        except Exception as e:
            await client.send_message(
                message.chat.id,
                f"❌ **Restart Failed!**\n`{str(e)}`"
            )
    else:
        response += "\n\n⚠️ **Clone running nahi hai.**\nRedeploy pe auto-start hoga."
        await message.reply_text(response, quote=True)


# ====================== REMOVE CONFIG KEY ======================
@Bot.on_message(filters.command("remove_config") 
