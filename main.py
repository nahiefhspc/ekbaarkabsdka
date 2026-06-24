import asyncio
import pyrogram.utils
from bot import Bot
from database.database import get_all_clones
from config import TG_BOT_TOKEN, OWNER_ID, API_ID, API_HASH   # Yeh line ab sahi hogi

pyrogram.utils.MIN_CHANNEL_ID = -1009147483647

async def start_all_bots():
    running_bots = []
    
    # Main Bot
    try:
        main_bot = Bot(
            bot_token=TG_BOT_TOKEN,
            is_clone=False,
            force_subs=[]
        )
        await main_bot.start()
        running_bots.append(main_bot)
        print("✅ Main Bot Started Successfully!")
    except Exception as e:
        print(f"❌ Main Bot Failed: {e}")
        return

    # Clone Bots
    clones = await get_all_clones()
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
            print(f"✅ Clone Started: {token[-8:]}...")
        except Exception as e:
            print(f"❌ Clone Failed {token[-8:]}: {e}")

    print(f"\n🚀 Total Bots Running: {len(running_bots)}")
    await asyncio.Event().wait()

if __name__ == "__main__":
    print("Starting File Store Bot with Clone System...")
    asyncio.run(start_all_bots())
