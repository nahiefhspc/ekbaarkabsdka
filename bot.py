from aiohttp import web
from plugins import web_server
import pyromod.listen
from pyrogram import Client
from pyrogram.enums import ParseMode
import sys
from datetime import datetime
from config import API_HASH, APP_ID, LOGGER, TG_BOT_WORKERS, PORT, FORCE_SUB_CHANNEL, FORCE_SUB_CHANNEL2, FORCE_SUB_CHANNEL3, FORCE_SUB_CHANNEL4, CHANNEL_ID

class Bot(Client):
    def __init__(self, bot_token=None, is_clone=False, force_subs=None, clone_config=None):
        self.is_clone = is_clone
        self.force_subs = force_subs or []
        self.clone_config = clone_config or {}   # Per clone custom config
        self.bot_token = bot_token or TG_BOT_TOKEN
        self.username = None
        
        # Bot Name
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

        # Get Bot Info
        me = await self.get_me()
        self.username = me.username

        # ====================== FORCE SUB INVITE LINKS ======================
        force_list = self.force_subs if (self.is_clone and self.force_subs) else \
                     [FORCE_SUB_CHANNEL, FORCE_SUB_CHANNEL2, FORCE_SUB_CHANNEL3, FORCE_SUB_CHANNEL4]
        
        for idx, fsub in enumerate(force_list):
            if not fsub or fsub == 0:
                continue
            try:
                chat = await self.get_chat(fsub)
                link = chat.invite_link
                if not link:
                    link = await self.export_chat_invite_link(fsub)
                
                link_attr = f'invitelink{idx+1 if idx > 0 else ""}'
                setattr(self, link_attr, link)
                self.LOGGER(__name__).info(f"✅ Force Sub Link Set: {fsub}")
            except Exception as e:
                self.LOGGER(__name__).warning(f"Invite link failed for {fsub}: {e}")
                setattr(self, f'invitelink{idx+1 if idx > 0 else ""}', f"https://t.me/c/{str(fsub)[4:]}")

        # ====================== DB CHANNEL ======================
        try:
            db_channel = await self.get_chat(CHANNEL_ID)
            self.db_channel = db_channel
            test = await self.send_message(chat_id=db_channel.id, text="**Bot Started Successfully ✅**")
            await test.delete()
            self.LOGGER(__name__).info(f"DB Channel Connected: {db_channel.title}")
        except Exception as e:
            self.LOGGER(__name__).error(f"DB Channel Error: {e}")
            self.LOGGER(__name__).error("Bot must be admin in DB Channel!")
            sys.exit(1)

        # ====================== BOT START LOG ======================
        bot_type = "Clone" if self.is_clone else "Main"
        self.LOGGER(__name__).info(f"✅ {bot_type} Bot Running → @{self.username} | ID: {me.id}")

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


# For compatibility
Bot = Bot
