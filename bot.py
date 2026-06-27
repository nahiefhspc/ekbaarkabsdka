from aiohttp import web
from plugins import web_server
import pyromod.listen
from pyrogram import Client
from pyrogram.enums import ParseMode
import sys
from datetime import datetime
from config import API_HASH, APP_ID, LOGGER, TG_BOT_WORKERS, PORT, FORCE_SUB_CHANNEL, FORCE_SUB_CHANNEL2, FORCE_SUB_CHANNEL3, FORCE_SUB_CHANNEL4, CHANNEL_ID, BOT_TOKEN

class Bot(Client):
    def __init__(self, bot_token=None, is_clone=False, force_subs=None, clone_config=None):
        self.is_clone = is_clone
        self.force_subs = force_subs or []
        self.clone_config = clone_config or {}
        self.bot_token = bot_token or BOT_TOKEN
        self.username = None
        
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

        # Force Sub
        if self.is_clone and self.force_subs:
            force_list = self.force_subs
        else:
            force_list = [FORCE_SUB_CHANNEL, FORCE_SUB_CHANNEL2, FORCE_SUB_CHANNEL3, FORCE_SUB_CHANNEL4]

        for idx, fsub in enumerate(force_list):
            if not fsub or fsub == 0:
                continue
            try:
                chat = await self.get_chat(fsub)
                link = chat.invite_link or await self.export_chat_invite_link(fsub)
                setattr(self, f'invitelink{idx+1 if idx > 0 else ""}', link)
            except Exception as e:
                print(f"Force Sub {fsub} failed: {e}")
                setattr(self, f'invitelink{idx+1 if idx > 0 else ""}', f"https://t.me/c/{str(fsub)[4:]}")

        # DB Channel
        if not self.is_clone:
            try:
                db_channel = await self.get_chat(CHANNEL_ID)
                self.db_channel = db_channel
            except Exception as e:
                print(f"DB Channel Error: {e}")
                sys.exit(1)

        print(f"✅ {'Clone' if self.is_clone else 'Main'} Bot Running → @{self.username}")

        # Web Server
        try:
            app = web.AppRunner(await web_server())
            await app.setup()
            await web.TCPSite(app, "0.0.0.0", PORT).start()
        except Exception as e:
            print(f"Web Server Error: {e}")

    async def stop(self):
        await super().stop()
        print(f"{'Clone' if self.is_clone else 'Main'} Bot Stopped")

    def update_config(self, new_config):
        self.clone_config = new_config
        print(f"Config updated for {'Clone' if self.is_clone else 'Main'} Bot")


Bot = Bot
