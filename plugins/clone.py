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

# ─── Pending bots jo config wait kar rahe hain ───
# Structure: { token: { 'config': {}, 'step': 'waiting_config' } }
PENDING_BOTS = {}


# ====================== CUSTOM PENDING FILTER ======================
async def pending_config_filter(_, client, message):
    """
    Sirf tab trigger ho jab:
    1. PENDING_BOTS mein koi waiting ho
    2. Message command na ho
    3. Owner ka message ho
    """
    if not PENDING_BOTS:
        return False
    if not message.from_user:
        return False
    if message.from_user.id != OWNER_ID:
        return False
    if message.text and message.text.startswith('/'):
        return False

    # Koi pending bot waiting hai?
    for token, data in PENDING_BOTS.items():
        if data.get('step') == 'waiting_config':
            return True
    return False


pending_filter = filters.create(pending_config_filter)


# ====================== PARSE CONFIG LINES ======================
def parse_config_lines(lines: list):
    """
    Lines ko parse karke config dict banao.
    Returns: (parsed_config, updated_keys_text, failed_keys_text)
    """
    parsed = {}
    updated = []
    failed = []

    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        if '=' not in line:
            failed.append(f"`{line}` (= missing)")
            continue

        key, value = line.split('=', 1)
        key = key.strip().upper()
        value = value.strip()

        if not key:
            failed.append(f"Empty key: `{line}`")
            continue

        # Type conversion
        if value.lower() == 'true':
            parsed[key] = True
        elif value.lower() == 'false':
            parsed[key] = False
        elif value.lower() in ['none', 'null', '']:
            parsed[key] = None
        else:
            try:
                parsed[key] = int(value)
            except ValueError:
                try:
                    parsed[key] = float(value)
                except ValueError:
                    parsed[key] = value

        updated.append(f"✅ `{key}` = `{parsed[key]}`")

    return parsed, updated, failed


# ====================== INTERNAL: START CLONE ======================
async def _start_clone_now(client, message, token: str, clone_data: dict):
    """Clone bot actually start karo"""
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
            f"📝 Config update: `/set_config {token[-8:]}`\n"
            f"ℹ️ Info: `/clone_info {token[-8:]}`"
        )
        print(f"✅ Clone started: @{clone_bot.username} ({token[-8:]})")

    except Exception as e:
        await client.send_message(
            message.chat.id,
            f"❌ **Clone Start Failed!**\n\n"
            f"Token: `{token[-8:]}`\n"
            f"Error: `{str(e)}`"
        )
        print(f"❌ Clone failed: {token[-8:]} → {e}")


# ====================== ADD CLONE ======================
@Bot.on_message(filters.command("add_bot") & filters.user(OWNER_ID) & filters.private)
async def add_clone_bot(client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            "❌ **Usage:** `/add_bot <token>`\n\n"
            "Example: `/add_bot 123456:ABC-DEF...`",
            quote=True
        )

    token = message.command[1].strip()

    # Token valid check
    if ":" not in token:
        return await message.reply_text(
            "❌ **Invalid Token!**\n"
            "Format: `123456:ABC-DEF...`",
            quote=True
        )

    # DB mein already hai?
    existing = None
    all_clones = await get_all_clones()
    for c in all_clones:
        if c['token'] == token:
            existing = c
            break

    if existing:
        existing_config = existing.get('config', {})

        if existing_config:
            # Config hai - check running
            if token in CLONE_BOTS:
                return await message.reply_text(
                    f"⚠️ **Yeh bot already running hai!**\n"
                    f"Token: `{token[-8:]}`\n\n"
                    f"Info: `/clone_info {token[-8:]}`",
                    quote=True
                )

            # Config hai, start karo
            config_text = "\n".join(
                [f"• `{k}` = `{v}`" for k, v in existing_config.items()]
            )
            await message.reply_text(
                f"✅ **Bot DB mein already hai!**\n"
                f"Saved config ke saath start ho raha hai...\n\n"
                f"**Config ({len(existing_config)} keys):**\n{config_text}",
                quote=True
            )
            await _start_clone_now(client, message, token, existing)

        else:
            # DB mein hai par config nahi - config maango
            PENDING_BOTS[token] = {'config': {}, 'step': 'waiting_config'}
            await message.reply_text(
                f"⚠️ **Bot DB mein hai lekin config nahi!**\n\n"
                f"**Config bhejo is format mein:**\n"
                f"`PROTECT_CONTENT=True`\n"
                f"`FORCE_SUB_CHANNEL=-100xxx`\n"
                f"`START_MSG=Hello Welcome`\n\n"
                f"Ya skip karo: `skip`\n"
                f"_(Skip → main bot ka config use hoga)_",
                quote=True
            )
    else:
        # Naya bot - save karo, config maango
        await add_clone(token, OWNER_ID, force_subs=[], config={})
        PENDING_BOTS[token] = {'config': {}, 'step': 'waiting_config'}

        await message.reply_text(
            f"✅ **Token Saved!** `{token[-8:]}`\n\n"
            f"**Ab config bhejo** (ek message mein):\n\n"
            f"`PROTECT_CONTENT=True`\n"
            f"`FORCE_SUB_CHANNEL=-100356565653`\n"
            f"`START_MSG=Hello Welcome!`\n\n"
            f"Ya skip karo: `skip`\n"
            f"_(Skip → main bot ka config use hoga)_",
            quote=True
        )


# ====================== CONFIG RECEIVE ======================
@Bot.on_message(pending_filter & filters.private)
async def handle_pending_config(client, message: Message):
    """Pending bot ka config receive karo"""
    text = message.text.strip()

    # Find karo kaunsa bot wait kar raha hai
    pending_token = None
    for token, data in PENDING_BOTS.items():
        if data.get('step') == 'waiting_config':
            pending_token = token
            break

    if not pending_token:
        return

    # Clone data lao DB se
    clone = None
    all_clones = await get_all_clones()
    for c in all_clones:
        if c['token'] == pending_token:
            clone = c
            break

    if not clone:
        del PENDING_BOTS[pending_token]
        return

    # Skip?
    if text.lower() == 'skip':
        del PENDING_BOTS[pending_token]
        await message.reply_text(
            f"⏭️ **Config Skip!**\n"
            f"Token: `{pending_token[-8:]}`\n\n"
            f"Main bot ka config use hoga.\n"
            f"🚀 Starting...",
            quote=True
        )
        await _start_clone_now(client, message, pending_token, clone)
        return

    # Config parse karo
    lines = text.strip().split('\n')
    parsed_config, updated_keys, failed_keys = parse_config_lines(lines)

    if not parsed_config:
        return await message.reply_text(
            "❌ **Koi valid config nahi mili!**\n\n"
            "`KEY=VALUE` format mein bhejo\n"
            "Ya `skip` likho.",
            quote=True
        )

    # Save to DB
    await update_clone_config(pending_token, parsed_config)

    # Pending se hatao
    del PENDING_BOTS[pending_token]

    config_text = "\n".join(updated_keys)
    response = f"✅ **Config Saved!**\n\n**Keys ({len(parsed_config)}):**\n{config_text}\n\n"

    if failed_keys:
        response += f"⚠️ **Failed:**\n" + "\n".join(failed_keys) + "\n\n"

    response += "🚀 **Starting clone...**"
    await message.reply_text(response, quote=True)

    # Updated clone data ke saath start karo
    updated_clone = clone.copy()
    updated_clone['config'] = parsed_config
    await _start_clone_now(client, message, pending_token, updated_clone)


# ====================== SET CONFIG + AUTO RESTART ======================
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
        return await message.reply_text(
            "❌ **Token missing!**\n"
            "Format: `/set_config <last8>`",
            quote=True
        )

    partial = first_line_parts[1].strip()

    clone = await get_clone_by_partial_token(partial)
    if not clone:
        return await message.reply_text(
            f"❌ **Clone `{partial}` not found!**\n"
            f"List: `/list_bots`",
            quote=True
        )

    current_config = clone.get('config', {})

    # Config parse karo (line 1 ke baad)
    new_config, updated_keys, failed_keys = parse_config_lines(lines[1:])

    if not updated_keys:
        fail_text = "\n".join(failed_keys) if failed_keys else "Koi line parse nahi hui."
        return await message.reply_text(
            f"❌ **No valid config!**\n\n{fail_text}",
            quote=True
        )

    # Merge with existing
    current_config.update(new_config)

    # Save to DB
    await update_clone_config(clone['token'], current_config)

    response = (
        f"✅ **Config Updated! `{partial}`**\n\n"
        f"**Updated:**\n" + "\n".join(updated_keys)
    )

    if failed_keys:
        response += "\n\n**⚠️ Failed:**\n" + "\n".join(failed_keys)

    response += f"\n\n**Total Config Keys:** `{len(current_config)}`"

    token = clone['token']

    # Clone running hai? Restart karo
    if token in CLONE_BOTS:
        response += "\n\n🔄 **Clone restart ho raha hai...**"
        await message.reply_text(response, quote=True)

        try:
            # Stop old clone
            old_clone = CLONE_BOTS[token]
            await old_clone.stop()
            del CLONE_BOTS[token]
            print(f"🛑 Stopped clone: {token[-8:]}")

            await asyncio.sleep(3)

            # Start new clone
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
                f"@{new_clone.username} naye config ke saath live!\n"
                f"Config Keys: `{len(current_config)}`"
            )
            print(f"✅ Clone restarted: @{new_clone.username}")

        except Exception as e:
            await client.send_message(
                message.chat.id,
                f"❌ **Restart Failed!**\n`{str(e)}`"
            )
            print(f"❌ Restart failed: {e}")
    else:
        response += "\n\n⚠️ **Clone running nahi.**\nRedeploy pe auto-start hoga."
        await message.reply_text(response, quote=True)


# ====================== REMOVE CONFIG KEY ======================
@Bot.on_message(filters.command("remove_config") & filters.user(OWNER_ID) & filters.private)
async def remove_config_key(client, message: Message):
    if len(message.command) < 3:
        return await message.reply_text(
            "❌ **Usage:** `/remove_config <last8> <KEY>`\n"
            "Example: `/remove_config abcdefgh PROTECT_CONTENT`",
            quote=True
        )

    partial = message.command[1].strip()
    key = message.command[2].strip().upper()

    clone = await get_clone_by_partial_token(partial)
    if not clone:
        return await message.reply_text("❌ **Clone not found.**", quote=True)

    config = clone.get('config', {})
    if key not in config:
        return await message.reply_text(
            f"⚠️ **`{key}` config mein hai hi nahi!**",
            quote=True
        )

    del config[key]
    await update_clone_config(clone['token'], config)

    await message.reply_text(
        f"✅ **`{key}` removed from `{partial}`**\n"
        f"Ab main bot ka `{key}` use hoga.",
        quote=True
    )


# ====================== REMOVE BOT ======================
@Bot.on_message(filters.command("remove_bot") & filters.user(OWNER_ID) & filters.private)
async def remove_clone_bot(client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            "❌ **Usage:** `/remove_bot <last8>`",
            quote=True
        )

    partial = message.command[1].strip()
    all_clones = await get_all_clones()

    for c in all_clones:
        if c['token'].endswith(partial):
            token = c['token']

            # Stop if running
            if token in CLONE_BOTS:
                try:
                    await CLONE_BOTS[token].stop()
                    del CLONE_BOTS[token]
                    print(f"🛑 Stopped clone: {token[-8:]}")
                except Exception as e:
                    print(f"Stop error: {e}")

            # Remove from pending
            if token in PENDING_BOTS:
                del PENDING_BOTS[token]

            await remove_clone(token)
            return await message.reply_text(
                f"✅ **Clone Removed!**\nToken: `{partial}`",
                quote=True
            )

    await message.reply_text(
        "❌ **Clone not found!**\n"
        "List: `/list_bots`",
        quote=True
    )


# ====================== REMOVE FORCE SUB ======================
@Bot.on_message(filters.command("remove_force") & filters.user(OWNER_ID) & filters.private)
async def remove_force_sub(client, message: Message):
    if len(message.command) < 3:
        return await message.reply_text(
            "❌ **Usage:** `/remove_force <last8> <-100xxxxxxxx>`",
            quote=True
        )

    partial = message.command[1].strip()
    try:
        channel_id = int(message.command[2])
    except ValueError:
        return await message.reply_text(
            "❌ **Invalid Channel ID!**",
            quote=True
        )

    clone = await get_clone_by_partial_token(partial)
    if not clone:
        return await message.reply_text("❌ **Clone not found.**", quote=True)

    fs = clone.get('force_subs', [])
    if channel_id not in fs:
        return await message.reply_text(
            "⚠️ **Yeh channel tha hi nahi!**",
            quote=True
        )

    fs.remove(channel_id)
    await update_clone_force_subs(clone['token'], fs)

    await message.reply_text(
        f"✅ **Force Sub Removed!**\n"
        f"Channel `{channel_id}` → Clone `{partial}`",
        quote=True
    )


# ====================== LIST BOTS ======================
@Bot.on_message(filters.command("list_bots") & filters.user(OWNER_ID) & filters.private)
async def list_clones(client, message: Message):
    all_clones = await get_all_clones()
    if not all_clones:
        return await message.reply_text(
            "❌ **Koi clone nahi hai.**\n"
            "Add: `/add_bot <token>`",
            quote=True
        )

    text = f"🤖 **Clone Bots** ({len(all_clones)} total)\n\n"
    for i, c in enumerate(all_clones, 1):
        token_end = c['token'][-8:]
        config_count = len(c.get('config', {}))
        fs_count = len(c.get('force_subs', []))
        running = "🟢" if c['token'] in CLONE_BOTS else "🔴"
        pending = " ⏳" if c['token'] in PENDING_BOTS else ""

        text += (
            f"{i}. `{token_end}` {running}{pending}\n"
            f"   Config: **{config_count}** | Force: **{fs_count}**\n\n"
        )

    await message.reply_text(text, quote=True)


# ====================== CLONE INFO ======================
@Bot.on_message(filters.command("clone_info") & filters.user(OWNER_ID) & filters.private)
async def clone_info(client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            "❌ **Usage:** `/clone_info <last8>`",
            quote=True
        )

    partial = message.command[1].strip()
    clone = await get_clone_by_partial_token(partial)
    if not clone:
        return await message.reply_text("❌ **Clone not found.**", quote=True)

    config = clone.get('config', {})
    fs = clone.get('force_subs', [])
    token = clone['token']

    status = (
        "🟢 Running" if token in CLONE_BOTS else
        "⏳ Config Pending" if token in PENDING_BOTS else
        "🔴 Stopped"
    )

    # Running bot ka username
    username = ""
    if token in CLONE_BOTS:
        username = f"\n**Username:** @{CLONE_BOTS[token].username}"

    text = (
        f"🔍 **Clone Info**\n\n"
        f"**Token:** `{token[-8:]}`"
        f"{username}\n"
        f"**Status:** {status}\n"
        f"**Config Keys:** `{len(config)}`\n"
        f"**Force Subs:** `{len(fs)}`\n"
    )

    if fs:
        text += "\n**📢 Force Subs:**\n"
        for ch in fs:
            text += f"  • `{ch}`\n"

    if config:
        text += "\n**⚙️ Clone Config:**\n"
        for k, v in config.items():
            text += f"  • `{k}` = `{v}`\n"
        text += "\n_Missing keys → main bot config se aayengi_"
    else:
        text += "\n**⚙️** _Sab main bot config use ho raha_"

    await message.reply_text(text, quote=True)
