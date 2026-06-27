import asyncio
import pyrogram.utils
from bot import Bot, CLONE_BOTS
from database.database import get_all_clones
from config import BOT_TOKEN

# Fix for large channel IDs
pyrogram.utils.MIN_CHANNEL_ID = -1009147483647


async def start_main_bot():
    """Main bot start karo"""
    if "main" in CLONE_BOTS:
        print("⚠️ Main bot already running.")
        return CLONE_BOTS["main"]

    main_bot = Bot(is_clone=False)
    await main_bot.start()
    CLONE_BOTS["main"] = main_bot
    print("✅ Main Bot Started!")
    return main_bot


async def start_clone_bot(token: str, force_subs=None, clone_config=None):
    """Single clone bot start karo"""
    if token in CLONE_BOTS:
        print(f"⚠️ Clone already running: {token[-8:]}")
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
    """Database se saare clones auto start karo"""
    try:
        clones = await get_all_clones()
        print(f"📦 Found {len(clones)} clone(s) in database.")

        for clone_data in clones:
            token = clone_data.get('token', '')
            force_subs = clone_data.get('force_subs', [])
            clone_config = clone_data.get('config', {})
            status = clone_data.get('status', 'active')

            if not token:
                continue

            if status != 'active':
                print(f"⏭️ Skipping inactive: {token[-8:]}")
                continue

            if token in CLONE_BOTS:
                print(f"⏭️ Already running: {token[-8:]}")
                continue

            await start_clone_bot(token, force_subs, clone_config)
            # Thoda delay clones ke beech
            await asyncio.sleep(2)

    except Exception as e:
        print(f"❌ Auto-start clones error: {e}")


async def main():
    print("🚀 Starting Bot System...")
    print("=" * 40)

    # Main bot pehle start karo
    await start_main_bot()

    # Phir saare clones
    await start_all_clones()

    total = len(CLONE_BOTS)
    clones_count = total - 1
    print("=" * 40)
    print(f"✅ System Ready!")
    print(f"📊 Running: {total} total (1 Main + {clones_count} Clone(s))")
    print("=" * 40)

    # Keep alive
    try:
        await asyncio.Event().wait()
    except (asyncio.CancelledError, KeyboardInterrupt):
        print("\n🛑 Shutting down all bots...")
        for name, bot in list(CLONE_BOTS.items()):
            try:
                await bot.stop()
                print(f"✅ Stopped: {name}")
            except Exception as e:
                print(f"Stop error {name}: {e}")
        print("👋 All bots stopped.")


if __name__ == "__main__":
    asyncio.run(main())
