from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot import Bot
from config import OWNER_ID
from database.database import (
    add_clone, 
    remove_clone, 
    get_all_clones, 
    update_clone_force_subs, 
    update_clone_config, 
    get_clone_by_partial_token
)

# ====================== CLONE MANAGEMENT ======================

@Bot.on_message(filters.command("add_bot") & filters.user(OWNER_ID) & filters.private)
async def add_clone_bot(client, message):
    if len(message.command) < 2:
        return await message.reply_text(
            "❌ **Usage:**\n"
            "`/add_bot <bot_token>`\n\n"
            "Example:\n`/add_bot 7123456789:AAFxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`"
        )
    
    token = message.command[1].strip()
    if len(token) < 30:
        return await message.reply_text("❌ Invalid Bot Token!")

    try:
        await add_clone(token, OWNER_ID)
        
        # Hot Start (Restart ke bina)
        clone_bot = Bot(
            bot_token=token,
            is_clone=True,
            force_subs=[],
            clone_config={}
        )
        await clone_bot.start()
        
        await message.reply_text(
            "✅ **Clone Bot Added & Started Successfully!**\n"
            "🔥 Hot Reload - Bina restart ke chal gaya!"
        )
    except Exception as e:
        await message.reply_text(f"❌ Error: {str(e)}")


@Bot.on_message(filters.command("list_bots") & filters.user(OWNER_ID) & filters.private)
async def list_clones(client, message):
    clones = await get_all_clones()
    if not clones:
        return await message.reply_text("❌ Koi clone add nahi kiya gaya hai.")

    text = "🤖 **Active Clone Bots:**\n\n"
    for c in clones:
        token_end = c['token'][-8:]
        fs_count = len(c.get('force_subs', []))
        config_count = len(c.get('config', {}))
        text += f"• `{token_end}` | Force Subs: **{fs_count}** | Config: **{config_count}**\n"
    
    await message.reply_text(text)


@Bot.on_message(filters.command("remove_bot") & filters.user(OWNER_ID) & filters.private)
async def remove_clone_bot(client, message):
    if len(message.command) < 2:
        return await message.reply_text("❌ Usage: `/remove_bot <last_8_digits>`")

    partial = message.command[1].strip()
    clones = await get_all_clones()
    
    for c in clones:
        if c['token'].endswith(partial):
            await remove_clone(c['token'])
            return await message.reply_text(
                f"✅ **Clone Removed:** `{partial}`\n"
                "Note: Agar running tha to manually stop karna pad sakta hai."
            )
    
    await message.reply_text("❌ Clone not found with this token.")


# ====================== FORCE SUB MANAGEMENT ======================

@Bot.on_message(filters.command("set_force") & filters.user(OWNER_ID) & filters.private)
async def set_force_sub(client, message):
    if len(message.command) < 3:
        return await message.reply_text("Usage: `/set_force <last8> <-100xxxxxxxx>`")

    partial = message.command[1].strip()
    try:
        channel_id = int(message.command[2])
    except:
        return await message.reply_text("❌ Invalid Channel ID!")

    clone = await get_clone_by_partial_token(partial)
    if not clone:
        return await message.reply_text("❌ Clone not found. /list_bots chalao.")

    current_fs = clone.get('force_subs', [])
    if channel_id in current_fs:
        return await message.reply_text("⚠️ Yeh channel already added hai.")

    current_fs.append(channel_id)
    await update_clone_force_subs(clone['token'], current_fs)

    await message.reply_text(f"✅ Force Sub Added for clone `{partial}`\nChannel: `{channel_id}`")


@Bot.on_message(filters.command("remove_force") & filters.user(OWNER_ID) & filters.private)
async def remove_force_sub(client, message):
    if len(message.command) < 3:
        return await message.reply_text("Usage: `/remove_force <last8> <-100xxxxxxxx>`")

    partial = message.command[1].strip()
    try:
        channel_id = int(message.command[2])
    except:
        return await message.reply_text("❌ Invalid Channel ID!")

    clone = await get_clone_by_partial_token(partial)
    if not clone:
        return await message.reply_text("❌ Clone not found.")

    current_fs = clone.get('force_subs', [])
    if channel_id not in current_fs:
        return await message.reply_text("⚠️ Yeh channel isme tha hi nahi.")

    current_fs.remove(channel_id)
    await update_clone_force_subs(clone['token'], current_fs)

    await message.reply_text(f"✅ Force Sub Removed for clone `{partial}`")


# ====================== PER CLONE CONFIG ======================

@Bot.on_message(filters.command("set_config") & filters.user(OWNER_ID) & filters.private)
async def set_clone_config(client, message):
    if len(message.command) < 4:
        return await message.reply_text(
            "❌ **Usage:**\n"
            "`/set_config <last8> <KEY> <VALUE>`\n\n"
            "Examples:\n"
            "`/set_config abcdefgh START_MSG Hello from My Clone Bot`\n"
            "`/set_config abcdefgh PROTECT_CONTENT True`\n"
            "`/set_config abcdefgh CUSTOM_CAPTION New Caption`"
        )

    partial = message.command[1].strip()
    key = message.command[2].upper()
    value = " |".join(message.command[3:])

    clone = await get_clone_by_partial_token(partial)
    if not clone:
        return await message.reply_text("❌ Clone not found.")

    current_config = clone.get('config', {})
    current_config[key] = value if key not in ["PROTECT_CONTENT", "DISABLE_CHANNEL_BUTTON"] else (value.lower() == "true")
    
    await update_clone_config(clone['token'], current_config)
    await message.reply_text(f"✅ **Config Updated!**\n`{key}` = `{value}`")


@Bot.on_message(filters.command("clone_info") & filters.user(OWNER_ID) & filters.private)
async def clone_info(client, message):
    if len(message.command) < 2:
        return await message.reply_text("Usage: `/clone_info <last8>`")

    partial = message.command[1].strip()
    clone = await get_clone_by_partial_token(partial)
    if not clone:
        return await message.reply_text("❌ Clone not found.")

    config = clone.get('config', {})
    fs = clone.get('force_subs', [])

    text = f"""**🔍 Clone Information**

**Token:** `{clone['token'][-8:]}...`
**Force Subs:** {len(fs)} → `{fs}`
**Custom Config:** {len(config)} keys
**Added:** {clone.get('added_at', 'Unknown')}

**Current Config:**
"""
    for k, v in config.items():
        text += f"• `{k}`: `{v}`\n"

    await message.reply_text(text)
