import asyncio
import pyrogram.utils
from bot import Bot, CLONE_BOTS
from database.database import get_all_clones
from config import BOT_TOKEN

# Fix for large channel IDs
pyrogram.utils.MIN_CHANNEL_ID = -1009147483647


async def start_main_bot():
    """Start the Main Bot"""
    if "main" in CLONE_BOTS:
        return CLONE_BOTS["main"]

    main_bot = Bot(is_clone=False)
    await main_bot.start()
    CLONE_BOTS["main"] = main_bot
    print("✅ Main Bot Started!")
    return main_bot


async def start_clone_bot(token: str, force_subs=None, clone_config=None):
    """Start a single clone bot"""
    if token in CLONE_BOTS:
        print(f"⚠️ Clone {token[-8:]} already running.")
        return CLONE_BOTS[token]

    try:
        clone_bot = Bot(
            bot_token=token,
            is_clone=True,
            force_subs=force_subs or [],
            clone_config=clone_config or {}
        )
        await clone_bot.start()
        CLONE_BOTS[token] = clone_bot
        print(f"✅ Clone Started: {token[-8:]}")
        return clone_bot
    except Exception as e:
        print(f"❌ Clone {token[-8:]} failed: {e}")
        return None


async def start_all_clones():
    """Start all saved clones from database on startup"""
    clones = await get_all_clones()
    print(f"📦 Found {len(clones)} clone(s) in database.")

    for clone_data in clones:
        token = clone_data.get('token')
        force_subs = clone_data.get('force_subs', [])
        clone_config = clone_data.get('config', {})
        status = clone_data.get('status', 'active')

        if not token:
            continue

        if status != 'active':
            print(f"⏭️ Skipping inactive clone: {token[-8:]}")
            continue

        if token in CLONE_BOTS:
            print(f"⏭️ Already running: {token[-8:]}")
            continue

        await start_clone_bot(token, force_subs, clone_config)
        await asyncio.sleep(2)  # Delay between starts


async def main():
    print("🚀 Starting Bot System...")

    # Start Main Bot first
    await start_main_bot()

    # Start all clones from database
    await start_all_clones()

    total = len(CLONE_BOTS)
    clones = total - 1  # minus main bot
    print(f"✅ Total Running: {total} (1 Main + {clones} Clone(s))")
    print("🟢 System Ready!")

    # Keep alive
    try:
        await asyncio.Event().wait()
    except (asyncio.CancelledError, KeyboardInterrupt):
        print("\n🛑 Shutting down...")
        for bot in list(CLONE_BOTS.values()):
            try:
                await bot.stop()
            except Exception:
                pass


if __name__ == "__main__":
    asyncio.run(main())
