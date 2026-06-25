import asyncio
import pyrogram.utils
from bot import Bot
from database.database import get_all_clones
from config import TG_BOT_TOKEN, OWNER_ID

# Fix for large channel IDs
pyrogram.utils.MIN_CHANNEL_ID = -1009147483647

# Global dictionary to keep track of running bots
running_bots = {}


async def start_main_bot():
    """Start the Main Bot"""
    if "main" in running_bots:
        return running_bots["main"]
    
    main_bot = Bot(is_clone=False)
    await main_bot.start()
    running_bots["main"] = main_bot
    print("✅ Main Bot Started Successfully!")
    return main_bot


async def start_clone_bot(token: str, force_subs=None, clone_config=None):
    """Start a single clone bot (Hot Start)"""
    if token in running_bots:
        print(f"⚠️ Clone {token[-8:]} already running.")
        return running_bots[token]
    
    try:
        clone_bot = Bot(
            bot_token=token,
            is_clone=True,
            force_subs=force_subs or [],
            clone_config=clone_config or {}
        )
        await clone_bot.start()
        running_bots[token] = clone_bot
        print(f"✅ Clone Bot Started: {token[-8:]}...")
        return clone_bot
    except Exception as e:
        print(f"❌ Failed to start clone {token[-8:]}: {e}")
        return None


async def start_all_clones():
    """Start all saved clones from database"""
    clones = await get_all_clones()
    print(f"Found {len(clones)} clones in database.")
    
    for clone_data in clones:
        token = clone_data.get('token')
        force_subs = clone_data.get('force_subs', [])
        clone_config = clone_data.get('config', {})
        
        if token not in running_bots:
            await start_clone_bot(token, force_subs, clone_config)


async def main():
    print("🚀 Starting Telegram File Store Bot with Clone System...")

    # Start Main Bot
    await start_main_bot()

    # Start all existing clones
    await start_all_clones()

    print(f"✅ Total Running Bots: {len(running_bots)} (1 Main + {len(running_bots)-1} Clones)")
    print("Bot is now ready. You can add new clones using /add_bot command.")

    # Keep the program alive
    try:
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        print("\nShutting down all bots...")
        for bot in running_bots.values():
            try:
                await bot.stop()
            except:
                pass


if __name__ == "__main__":
    asyncio.run(main())
