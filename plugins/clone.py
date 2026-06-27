from pyrogram import filters
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

# ====================== INTERACTIVE CLONE ADD ======================
@Bot.on_message(filters.command("add_bot") & filters.user(OWNER_ID) & filters.private)
async def add_clone_bot(client, message):
    if len(message.command) < 2:
        return await message.reply_text("Usage: `/add_bot <token>`")

    token = message.command[1].strip()
    
    await add_clone(token, OWNER_ID, force_subs=[], config={})
    
    await message.reply_text(
        "✅ Token Saved.\n\n"
        "Ab config set karne ke liye:\n"
        "`/set_config <last8>`\n"
        "Bot khud variables puchega."
    )


# ====================== INTERACTIVE CONFIG ======================
@Bot.on_message(filters.command("set_config") & filters.user(OWNER_ID) & filters.private)
async def set_clone_config(client, message):
    if len(message.command) < 2:
        return await message.reply_text("Usage: `/set_config <last8>`")

    partial = message.command[1].strip()
    clone = await get_clone_by_partial_token(partial)
    if not clone:
        return await message.reply_text("❌ Clone not found.")

    await message.reply_text(
        "🔧 **Config Mode Started**\n\n"
        "Ab ek-ek karke variables bhejo jaise:\n"
        "`START_MSG=Hello This is My Clone`\n"
        "`PROTECT_CONTENT=False`\n"
        "`CUSTOM_CAPTION=New Caption`\n"
        "`FORCE_MSG=Join these channels`\n\n"
        "Jab sab ho jaye to `done` likh dena."
    )

    config = clone.get('config', {})
    while True:
        try:
            response = await client.listen(message.chat.id, filters.text, timeout=300)
            text = response.text.strip()

            if text.lower() == "/done":
                await update_clone_config(clone['token'], config)
                await message.reply_text("✅ Config Saved Successfully!\n\nBot restart karne ke liye `/start_clone <last8>` chalao.")
                break

            if '=' in text:
                key, value = text.split('=', 1)
                key = key.strip().upper()
                value = value.strip()

                if value.lower() in ['true', 'false']:
                    config[key] = value.lower() == 'true'
                else:
                    config[key] = value

                await response.reply_text(f"✅ `{key}` = `{value}` Saved")
            else:
                await response.reply_text("❌ Format: `KEY=VALUE`")
        except asyncio.TimeoutError:
            await message.reply_text("⏰ Timeout! Config mode closed.")
            break
        except Exception as e:
            await message.reply_text(f"Error: {e}")
            break


# ====================== START CLONE ======================
@Bot.on_message(filters.command("start_clone") & filters.user(OWNER_ID) & filters.private)
async def start_clone_bot(client, message):
    if len(message.command) < 2:
        return await message.reply_text("Usage: `/start_clone <last8>`")

    partial = message.command[1].strip()
    clone = await get_clone_by_partial_token(partial)
    if not clone:
        return await message.reply_text("❌ Clone not found.")

    token = clone['token']
    force_subs = clone.get('force_subs', [])
    config = clone.get('config', {})

    try:
        clone_bot = Bot(
            bot_token=token,
            is_clone=True,
            force_subs=force_subs,
            clone_config=config
        )
        await clone_bot.start()
        await message.reply_text(f"✅ Clone Bot Started Successfully!\nToken: `{token[-8:]}`")
    except Exception as e:
        await message.reply_text(f"❌ Start failed: {str(e)}")


# ====================== OTHER COMMANDS ======================
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
        return await message.reply_text("Usage: `/remove_bot <last8>`")

    partial = message.command[1].strip()
    clones = await get_all_clones()
    
    for c in clones:
        if c['token'].endswith(partial):
            await remove_clone(c['token'])
            return await message.reply_text(f"✅ Clone Removed: `{partial}`")
    
    await message.reply_text("❌ Clone not found.")


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
        return await message.reply_text("❌ Clone not found.")

    current_fs = clone.get('force_subs', [])
    if channel_id in current_fs:
        return await message.reply_text("⚠️ Yeh channel already added hai.")

    current_fs.append(channel_id)
    await update_clone_force_subs(clone['token'], current_fs)

    await message.reply_text(f"✅ Force Sub Added for clone `{partial}`\nChannel: `{channel_id}`")


@Bot.on_message(filters.command("clone_info") & filters.user(OWNER_ID) & filters.private)
async def clone_info(client, message):
    if len(message.command) < 2:
        return await message.reply_text("Usage: `/clone_info <last8>`")

    partial = message.command[1].strip()
    clone = await get_clone_by_partial_token(partial)
    if not clone:
        return await message.reply_text("❌ Clone not found.")

    fs = clone.get('force_subs', [])
    config = clone.get('config', {})

    text = f"""**🔍 Clone Information**

**Token:** `{clone['token'][-8:]}...`
**Force Subs:** {len(fs)} → `{fs}`
**Custom Config:** {len(config)} keys

**Current Config:**
"""
    for k, v in config.items():
        text += f"• `{k}`: `{v}`\n"

    await message.reply_text(text)
