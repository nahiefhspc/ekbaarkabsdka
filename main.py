import asyncio
import pyrogram.utils
from bot import Bot
from database.database import get_all_clones
from config import TG_BOT_TOKEN, OWNER_ID, API_ID, API_HASH

# Fix for large channel IDs
pyrogram.utils.MIN_CHANNEL_ID = -1009147483647

async def start_all_bots():
    running_bots = []
    
    # ====================== MAIN BOT ======================
    try:
        main_bot = Bot(
            bot_token=TG_BOT_TOKEN,
            is_clone=False,
            force_subs=[]  # Main bot ke liye config.py se lega
        )
        await main_bot.start()
        running_bots.append(main_bot)
        print("✅ Main Bot Started Successfully!")
    except Exception as e:
        print(f"❌ Main Bot Failed to Start: {e}")
        return

    # ====================== CLONE BOTS ======================
    clones = await get_all_clones()
    print(f"Found {len(clones)} clone bots in database.")

    for clone_data in clones:
        token = clone_data.get('token')
        force_subs = clone_data.get('force_subs', [])
        
        try:
            clone_bot = Bot(
                bot_token=token,
                is_clone=True,
                force_subs=force_subs
            )
            await clone_bot.start()
            running_bots.append(clone_bot)
            print(f"✅ Clone Bot Started → {token[-8:]}... | Force Subs: {len(force_subs)}")
        except Exception as e:
            print(f"❌ Failed to start clone {token[-8:]}...: {e}")

    total_bots = len(running_bots)
    print(f"\n🚀 Total Bots Running: {total_bots} (1 Main + {total_bots-1} Clones)")

    # Keep the program running
    try:
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        print("\nShutting down all bots...")
        for bot in running_bots:
            try:
                await bot.stop()
            except:
                pass


if __name__ == "__main__":
    print("Starting Telegram File Store Bot with Clone System...")
    asyncio.run(start_all_bots())
