from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot import Bot
from config import OWNER_ID
from database.database import add_clone, remove_clone, get_all_clones, update_clone_force_subs, get_clone_by_partial_token

# ====================== CLONE BOT MANAGEMENT ======================

@Bot.on_message(filters.command("add_bot") & filters.user(OWNER_ID) & filters.private)
async def add_clone_bot(client, message):
    if len(message.command) < 2:
        return await message.reply_text(
            "❌ **Usage:**\n"
            "`/add_bot <bot_token>`\n\n"
            "Example: `/add_bot 7123456789:AAFxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`"
        )
    
    token = message.command[1].strip()
    if len(token) < 30:
        return await message.reply_text("❌ Invalid Bot Token!")

    try:
        await add_clone(token, OWNER_ID)
        await message.reply_text(
            "✅ **Clone Bot Added Successfully!**\n\n"
            "🔄 Ab **Main Bot Restart** kar do taaki clone start ho sake."
        )
    except Exception as e:
        await message.reply_text(f"❌ Error: {str(e)}")


@Bot.on_message(filters.command("list_bots") & filters.user(OWNER_ID) & filters.private)
async def list_clones(client, message):
    clones = await get_all_clones()
    if not clones:
        return await message.reply_text("❌ Koi bhi clone bot add nahi kiya gaya hai.")

    text = "🤖 **Active Clone Bots:**\n\n"
    for c in clones:
        token_end = c['token'][-8:]
        fs_count = len(c.get('force_subs', []))
        text += f"• `{token_end}` | Force Subs: **{fs_count}**\n"
    
    await message.reply_text(text)


@Bot.on_message(filters.command("remove_bot") & filters.user(OWNER_ID) & filters.private)
async def remove_clone_bot(client, message):
    if len(message.command) < 2:
        return await message.reply_text("❌ **Usage:**\n`/remove_bot <last_8_digits_of_token>`")

    partial = message.command[1].strip()
    clones = await get_all_clones()
    
    for c in clones:
        if c['token'].endswith(partial):
            await remove_clone(c['token'])
            return await message.reply_text(
                f"✅ **Clone Removed Successfully!**\n\n"
                f"Token ending with `{partial}` removed.\n"
                "🔄 Main bot restart kar do."
            )
    
    await message.reply_text("❌ No clone found with this token ending.")


# ====================== FORCE SUB MANAGEMENT FOR CLONES ======================

@Bot.on_message(filters.command("set_force") & filters.user(OWNER_ID) & filters.private)
async def set_force_sub(client, message):
    if len(message.command) < 3:
        return await message.reply_text(
            "❌ **Usage:**\n"
            "`/set_force <last_8_digits> <-100xxxxxxxx>`\n\n"
            "Multiple channels add karne ke liye baar-baar command chalao."
        )

    partial = message.command[1].strip()
    try:
        channel_id = int(message.command[2])
    except:
        return await message.reply_text("❌ Invalid Channel ID! (Must be like -1001234567890)")

    clone = await get_clone_by_partial_token(partial)
    if not clone:
        return await message.reply_text("❌ Clone not found with this token.")

    current_fs = clone.get('force_subs', [])
    if channel_id in current_fs:
        return await message.reply_text("⚠️ Yeh channel already added hai is clone mein.")

    current_fs.append(channel_id)
    await update_clone_force_subs(clone['token'], current_fs)

    await message.reply_text(
        f"✅ **Force Sub Added Successfully!**\n\n"
        f"Clone: `{partial}`\n"
        f"Channel ID: `{channel_id}`"
    )


@Bot.on_message(filters.command("remove_force") & filters.user(OWNER_ID) & filters.private)
async def remove_force_sub(client, message):
    if len(message.command) < 3:
        return await message.reply_text(
            "❌ **Usage:**\n"
            "`/remove_force <last_8_digits> <-100xxxxxxxx>`"
        )

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
        return await message.reply_text("⚠️ Yeh channel is clone mein tha hi nahi.")

    current_fs.remove(channel_id)
    await update_clone_force_subs(clone['token'], current_fs)

    await message.reply_text(
        f"✅ **Force Sub Removed Successfully!**\n\n"
        f"Clone: `{partial}`\n"
        f"Channel ID: `{channel_id}`"
    )


@Bot.on_message(filters.command("clone_info") & filters.user(OWNER_ID) & filters.private)
async def clone_info(client, message):
    if len(message.command) < 2:
        return await message.reply_text("❌ **Usage:**\n`/clone_info <last_8_digits>`")

    partial = message.command[1].strip()
    clone = await get_clone_by_partial_token(partial)
    if not clone:
        return await message.reply_text("❌ Clone not found.")

    fs = clone.get('force_subs', [])
    text = f"""**Clone Information**

**Token:** `{clone['token'][-8:]}...`
**Owner ID:** `{clone['owner_id']}`
**Force Subs:** `{len(fs)}`
**Channels:** `{fs}`
**Added At:** {clone.get('added_at', 'Unknown')}
"""
    await message.reply_text(text)
