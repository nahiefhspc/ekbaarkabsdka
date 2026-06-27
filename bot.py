from aiohttp import web
from plugins import web_server
import pyromod.listen
from pyrogram import Client
from pyrogram.enums import ParseMode
import sys
import asyncio
from datetime import datetime
from config import (
    API_HASH, APP_ID, LOGGER, TG_BOT_WORKERS, PORT,
    FORCE_SUB_CHANNEL, FORCE_SUB_CHANNEL2, FORCE_SUB_CHANNEL3,
    FORCE_SUB_CHANNEL4, CHANNEL_ID, BOT_TOKEN
)

# Global dict - saare running bots
CLONE_BOTS = {}


class Bot(Client):
    def __init__(self, bot_token=None, is_clone=False, force_subs=None, clone_config=None):
        self.is_clone = is_clone
        self.force_subs = force_subs or []
        self.clone_config = clone_config or {}
        self.bot_token = bot_token or BOT_TOKEN
        self.username = None

        bot_name = "MainBot" if not is_clone else f"Clone_{str(self.bot_token)[-8:]}"

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

    def get_config(self, key, default=None):
        """
        Clone config se value lo.
        Agar nahi mili toh main config se fallback.
        """
        if self.is_clone and key in self.clone_config:
            return self.clone_config[key]
        try:
            import config as main_config
            return getattr(main_config, key, default)
        except Exception:
            return default

    async def start(self):
        await super().start()
        self.uptime = datetime.now()

        me = await self.get_me()
        self.username = me.username

        print(
            f"✅ {'Clone' if self.is_clone else 'Main'} Bot → "
            f"@{self.username} | Config Keys: {len(self.clone_config)}"
        )

        # ─── Force Sub Setup ───
        if self.is_clone and self.force_subs:
            force_list = self.force_subs
        else:
            force_list = [
                FORCE_SUB_CHANNEL, FORCE_SUB_CHANNEL2,
                FORCE_SUB_CHANNEL3, FORCE_SUB_CHANNEL4
            ]

        for idx, fsub in enumerate(force_list):
            if not fsub or fsub == 0:
                continue
            try:
                chat = await self.get_chat(fsub)
                link = chat.invite_link or await self.export_chat_invite_link(fsub)
                attr_name = f'invitelink{idx + 1 if idx > 0 else ""}'
                setattr(self, attr_name, link)
                print(f"✅ Force Sub {idx+1}: {fsub}")
            except Exception as e:
                print(f"Force Sub {fsub} failed: {e}")
                attr_name = f'invitelink{idx + 1 if idx > 0 else ""}'
                setattr(self, attr_name, f"https://t.me/c/{str(fsub)[4:]}")

        # ─── Clone config mein force sub channels hain? ───
        if self.is_clone and self.clone_config:
            config_force = [
                self.clone_config.get('FORCE_SUB_CHANNEL'),
                self.clone_config.get('FORCE_SUB_CHANNEL2'),
                self.clone_config.get('FORCE_SUB_CHANNEL3'),
                self.clone_config.get('FORCE_SUB_CHANNEL4'),
            ]
            config_force = [ch for ch in config_force if ch and ch != 0]

            for idx, fsub in enumerate(config_force):
                try:
                    chat = await self.get_chat(fsub)
                    link = chat.invite_link or await self.export_chat_invite_link(fsub)
                    attr_name = f'invitelink{idx + 1 if idx > 0 else ""}'
                    setattr(self, attr_name, link)
                    print(f"✅ Clone Config Force Sub {idx+1}: {fsub}")
                except Exception as e:
                    print(f"Clone Config Force Sub {fsub} failed: {e}")
                    attr_name = f'invitelink{idx + 1 if idx > 0 else ""}'
                    setattr(self, attr_name, f"https://t.me/c/{str(fsub)[4:]}")

        # ─── DB Channel - sirf main bot ───
        if not self.is_clone:
            try:
                db_channel = await self.get_chat(CHANNEL_ID)
                self.db_channel = db_channel
                print(f"✅ DB Channel: {db_channel.title}")
            except Exception as e:
                print(f"❌ DB Channel Error: {e}")
                sys.exit(1)

        # ─── Web Server - sirf main bot ───
        if not self.is_clone:
            try:
                runner = web.AppRunner(await web_server())
                await runner.setup()
                await web.TCPSite(runner, "0.0.0.0", PORT).start()
                print(f"🌐 Web Server started on port {PORT}")
            except Exception as e:
                print(f"Web Server Error: {e}")

    async def stop(self):
        await super().stop()
        print(f"🛑 {'Clone' if self.is_clone else 'Main'} Bot Stopped → @{self.username}")

    def update_config(self, new_config: dict):
        """Runtime config update"""
        self.clone_config.update(new_config)
        print(f"⚙️ Config updated for @{self.username}")
