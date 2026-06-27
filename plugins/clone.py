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
            f"📝 Update: `/set_config {token[-8:]}`\n"
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


# ====================== ADD CLONE (CONFIG SAME MESSAGE) ======================
@Bot.on_message(filters.command("add_bot") & filters.user(OWNER_ID) & filters.private)
async def add_clone_bot(client, message: Message):
    """
    Usage:
    /add_bot <token>
    KEY1=VALUE1
    KEY2=VALUE2
    
    Ya sirf token (main bot config use hoga):
    /add_bot <token>
    """
    full_text = message.text or message.caption or ""
    lines = full_text.strip().split('\n')

    # First line se token lo
    first_line_parts = lines[0].strip().split()

    if len(first_line_parts) < 2:
        return await message.reply_text(
            "❌ **Usage:**\n\n"
            "`/add_bot <token>`\n"
            "`PROTECT_CONTENT=True`\n"
            "`FORCE_SUB_CHANNEL=-100xxx`\n"
            "`START_MSG=Hello Welcome`\n\n"
            "**Ya sirf token (main config use hoga):**\n"
            "`/add_bot <token>`",
            quote=True
        )

    token = first_line_parts[1].strip()

    # Token valid?
    if ":" not in token:
        return await message.reply_text(
            "❌ **Invalid Token!**\n"
            "Format: `123456:ABC-DEF...`",
            quote=True
        )

    # ─── Already running? ───
    if token in CLONE_BOTS:
        return await message.reply_text(
            f"⚠️ **Already running!**\n"
            f"Token: `{token[-8:]}`\n\n"
            f"Info: `/clone_info {token[-8:]}`",
            quote=True
        )

    # ─── DB mein check karo ───
    existing = None
    all_clones = await get_all_clones()
    for c in all_clones:
        if c['token'] == token:
            existing = c
            break

    # ─── Config parse karo (line 1 ke baad) ───
    config_lines = lines[1:] if len(lines) > 1 else []
    parsed_config = {}
    updated_keys = []
    failed_keys = []

    if config_lines:
        parsed_config, updated_keys, failed_keys = parse_config_lines(config_lines)

    # ─── Already exists in DB ───
    if existing:
        old_config = existing.get('config', {})

        if parsed_config:
            # Naya config merge karo
            old_config.update(parsed_config)
            await update_clone_config(token, old_config)

            config_text = "\n".join(updated_keys)
            response = (
                f"✅ **Bot updated & starting!** `{token[-8:]}`\n\n"
                f"**Config ({len(old_config)} keys):**\n{config_text}\n"
            )
            if failed_keys:
                response += f"\n⚠️ **Failed:**\n" + "\n".join(failed_keys) + "\n"

            response += "\n🚀 **Starting...**"
            await message.reply_text(response, quote=True)

            updated_clone = existing.copy()
            updated_clone['config'] = old_config
            await _start_clone_now(client, message, token, updated_clone)

        elif old_config:
            # Purana config hai - use karo
            config_text = "\n".join(
                [f"• `{k}` = `{v}`" for k, v in old_config.items()]
            )
            await message.reply_text(
                f"✅ **DB mein hai! Saved config se start...**\n\n"
                f"**Config ({len(old_config)} keys):**\n{config_text}\n\n"
                f"🚀 **Starting...**",
                quote=True
            )
            await _start_clone_now(client, message, token, existing)

        else:
            # Koi config nahi - main bot config use hoga
            await message.reply_text(
                f"✅ **Starting with main bot config!** `{token[-8:]}`\n\n"
                f"_(Koi custom config nahi diya)_\n\n"
                f"🚀 **Starting...**",
                quote=True
            )
            await _start_clone_now(client, message, token, existing)

    # ─── Naya Bot ───
    else:
        # Save to DB
        await add_clone(token, OWNER_ID, force_subs=[], config=parsed_config)

        if parsed_config:
            config_text = "\n".join(updated_keys)
            response = (
                f"✅ **Token Saved & Starting!** `{token[-8:]}`\n\n"
                f"**Config ({len(parsed_config)} keys):**\n{config_text}\n"
            )
            if failed_keys:
                response += f"\n⚠️ **Failed:**\n" + "\n".join(failed_keys) + "\n"

            response += "\n🚀 **Starting...**"
            await message.reply_text(response, quote=True)

        else:
            await message.reply_text(
                f"✅ **Token Saved!** `{token[-8:]}`\n\n"
                f"_(No config → main bot config use hoga)_\n\n"
                f"🚀 **Starting...**",
                quote=True
            )

        clone_data = {
            'token': token,
            'force_subs': [],
            'config': parsed_config
        }
        await _start_clone_now(client, message, token, clone_data)


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

    # Config parse karo
    new_config, updated_keys, failed_keys = parse_config_lines(lines[1:])

    if not updated_keys:
        fail_text = "\n".join(failed_keys) if failed_keys else "Koi line parse nahi hui."
        return await message.reply_text(
            f"❌ **No valid config!**\n\n{fail_text}",
            quote=True
        )

    # Merge
    current_config.update(new_config)

    # Save
    await update_clone_config(clone['token'], current_config)

    response = (
        f"✅ **Config Updated! `{partial}`**\n\n"
        f"**Updated:**\n" + "\n".join(updated_keys)
    )

    if failed_keys:
        response += "\n\n**⚠️ Failed:**\n" + "\n".join(failed_keys)

    response += f"\n\n**Total:** `{len(current_config)}` keys"

    token = clone['token']

    # Running hai? Restart
    if token in CLONE_BOTS:
        response += "\n\n🔄 **Restarting clone...**"
        await message.reply_text(response, quote=True)

        try:
            old = CLONE_BOTS[token]
            await old.stop()
            del CLONE_BOTS[token]
            print(f"🛑 Stopped: {token[-8:]}")

            await asyncio.sleep(3)

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
                f"✅ **Restarted!** @{new_clone.username} live!\n"
                f"Config: `{len(current_config)}` keys"
            )

        except Exception as e:
            await client.send_message(
                message.chat.id,
                f"❌ **Restart Failed!** `{str(e)}`"
            )
    else:
        response += "\n\n⚠️ **Clone running nahi.** Redeploy pe auto-start."
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
        return await message.reply_text("❌ **Not found.**", quote=True)

    config = clone.get('config', {})
    if key not in config:
        return await message.reply_text(
            f"⚠️ **`{key}` config mein nahi hai!**",
            quote=True
        )

    del config[key]
    await update_clone_config(clone['token'], config)

    await message.reply_text(
        f"✅ **`{key}` removed from `{partial}`**\n"
        f"Main bot ka `{key}` use hoga.",
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

            if token in CLONE_BOTS:
                try:
                    await CLONE_BOTS[token].stop()
                    del CLONE_BOTS[token]
                except Exception:
                    pass

            await remove_clone(token)
            return await message.reply_text(
                f"✅ **Removed!** `{partial}`",
                quote=True
            )

    await message.reply_text("❌ **Not found!**", quote=True)


# ====================== REMOVE FORCE SUB ======================
@Bot.on_message(filters.command("remove_force") & filters.user(OWNER_ID) & filters.private)
async def remove_force_sub(client, message: Message):
    if len(message.command) < 3:
        return await message.reply_text(
            "❌ `/remove_force <last8> <-100xxx>`",
            quote=True
        )

    partial = message.command[1].strip()
    try:
        channel_id = int(message.command[2])
    except ValueError:
        return await message.reply_text("❌ **Invalid ID!**", quote=True)

    clone = await get_clone_by_partial_token(partial)
    if not clone:
        return await message.reply_text("❌ **Not found.**", quote=True)

    fs = clone.get('force_subs', [])
    if channel_id not in fs:
        return await message.reply_text("⚠️ **Tha hi nahi!**", quote=True)

    fs.remove(channel_id)
    await update_clone_force_subs(clone['token'], fs)
    await message.reply_text(f"✅ Removed `{channel_id}`", quote=True)


# ====================== LIST BOTS ======================
@Bot.on_message(filters.command("list_bots") & filters.user(OWNER_ID) & filters.private)
async def list_clones(client, message: Message):
    all_clones = await get_all_clones()
    if not all_clones:
        return await message.reply_text(
            "❌ **Koi clone nahi.**\nAdd: `/add_bot <token>`",
            quote=True
        )

    text = f"🤖 **Clones** ({len(all_clones)})\n\n"
    for i, c in enumerate(all_clones, 1):
        te = c['token'][-8:]
        cc = len(c.get('config', {}))
        fc = len(c.get('force_subs', []))
        r = "🟢" if c['token'] in CLONE_BOTS else "🔴"
        text += f"{i}. `{te}` {r} | Config: **{cc}** | Force: **{fc}**\n"

    await message.reply_text(text, quote=True)


# ====================== CLONE INFO ======================
@Bot.on_message(filters.command("clone_info") & filters.user(OWNER_ID) & filters.private)
async def clone_info(client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("❌ `/clone_info <last8>`", quote=True)

    partial = message.command[1].strip()
    clone = await get_clone_by_partial_token(partial)
    if not clone:
        return await message.reply_text("❌ **Not found.**", quote=True)

    config = clone.get('config', {})
    fs = clone.get('force_subs', [])
    token = clone['token']

    status = "🟢 Running" if token in CLONE_BOTS else "🔴 Stopped"

    username = ""
    if token in CLONE_BOTS:
        username = f"\n**Username:** @{CLONE_BOTS[token].username}"

    text = (
        f"🔍 **Clone Info**\n\n"
        f"**Token:** `{token[-8:]}`{username}\n"
        f"**Status:** {status}\n"
        f"**Config:** `{len(config)}` keys\n"
        f"**Force Subs:** `{len(fs)}`\n"
    )

    if fs:
        text += "\n**📢 Force Subs:**\n"
        for ch in fs:
            text += f"  • `{ch}`\n"

    if config:
        text += "\n**⚙️ Config:**\n"
        for k, v in config.items():
            text += f"  • `{k}` = `{v}`\n"
        text += "\n_Missing → main bot config_"
    else:
        text += "\n_Sab main bot config use ho raha_"

    await message.reply_text(text, quote=True)
