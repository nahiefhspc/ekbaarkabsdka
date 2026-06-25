from aiohttp import web
from plugins import web_server
import pyromod.listen
from pyrogram import Client
from pyrogram.enums import ParseMode
import sys
from datetime import datetime
from config import API_HASH, APP_ID, LOGGER, TG_BOT_WORKERS, PORT, FORCE_SUB_CHANNEL, FORCE_SUB_CHANNEL2, FORCE_SUB_CHANNEL3, FORCE_SUB_CHANNEL4, CHANNEL_ID, OWNER_ID

class Bot(Client):
    def __init__(self, bot_token=None, is_clone=False, force_subs=None):
        self.is_clone = is_clone
        self.force_subs = force_subs or []   # Clone ke liye alag force subs
        self.bot_token = bot_token or TG_BOT_TOKEN
        
        # Bot name different for clones
        bot_name = "MainBot" if not is_clone else f"Clone_{str(self.bot_token)[-6:]}"
        
        super().__init__(
            name=bot_name,
            api_hash=API_HASH,
            api_id=APP_ID,
            plugins={"root": "plugins"},
            workers=TG_BOT_WORKERS,
            bot_token=self.bot_token,
            parse_mode=ParseMode.HTML,
            sleep_threshold=5
        )
        self.LOGGER = LOGGER
        self.uptime = None
        self.db_channel = None

    async def start(self):
        await super().start()
        self.uptime = datetime.now()

        me = await self.get_me()
                self.username = me.username
        # ====================== FORCE SUB INVITE LINKS ======================
        force_list = self.force_subs if self.is_clone else [FORCE_SUB_CHANNEL, FORCE_SUB_CHANNEL2, FORCE_SUB_CHANNEL3, FORCE_SUB_CHANNEL4]
        
        invite_links = {}
        for idx, fsub in enumerate(force_list):
            if fsub and fsub != 0:
                try:
                    chat = await self.get_chat(fsub)
                    link = chat.invite_link
                    if not link:
                        link = await self.export_chat_invite_link(fsub)
                    invite_links[f'invitelink{idx+1 if idx > 0 else ""}'] = link
                    setattr(self, f'invitelink{idx+1 if idx > 0 else ""}', link)
                    self.LOGGER(__name__).info(f"Force Sub {fsub} link generated for {'Clone' if self.is_clone else 'Main'} Bot")
                except Exception as e:
                    self.LOGGER(__name__).warning(f"Failed to generate invite link for {fsub}: {e}")
                    setattr(self, f'invitelink{idx+1 if idx > 0 else ""}', f"https://t.me/+{fsub}")

        # ====================== DB CHANNEL CHECK ======================
        try:
            db_channel = await self.get_chat(CHANNEL_ID)
            self.db_channel = db_channel
            # Test message to check permissions
            test = await self.send_message(chat_id=db_channel.id, text="**Bot Started Successfully ✅**")
            await test.delete()
            self.LOGGER(__name__).info(f"DB Channel Connected: {db_channel.title} ({CHANNEL_ID})")
        except Exception as e:
            self.LOGGER(__name__).error(f"DB Channel Error: {e}")
            self.LOGGER(__name__).error("Make sure bot is admin in DB Channel with full permissions!")
            sys.exit(1)

        # ====================== BOT START MESSAGE ======================
        self.LOGGER(__name__).info(f"✅ {'Clone' if self.is_clone else 'Main'} Bot is Running!")
        self.LOGGER(__name__).info(f"Bot Username: @{me.username}")
        self.LOGGER(__name__).info(f"Bot ID: {me.id}")

        # ====================== WEB SERVER ======================
        try:
            app = web.AppRunner(await web_server())
            await app.setup()
            await web.TCPSite(app, "0.0.0.0", PORT).start()
            self.LOGGER(__name__).info(f"Web Server Started on Port {PORT}")
        except Exception as e:
            self.LOGGER(__name__).warning(f"Web Server Error: {e}")

    async def stop(self):
        await super().stop()
        self.LOGGER(__name__).info(f"{'Clone' if self.is_clone else 'Main'} Bot Stopped")


# For backward compatibility (if any file directly imports Bot)
Bot = Bot
