#(©)t.me/CodeFlix_Bots




import os
import logging
from logging.handlers import RotatingFileHandler



#Bot token @Botfather
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_MAIN_BOT_TOKEN")  # Main Bot Token
TG_BOT_TOKEN = BOT_TOKEN
CLONE_MODE = True

#Your API ID from my.telegram.org
APP_ID = int(os.environ.get("APP_ID", "23713783"))

#Your API Hash from my.telegram.org
API_HASH = os.environ.get("API_HASH", "2daa157943cb2d76d149c4de0b036a99")

#Your db channel Id
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", "-1002493255368"))

# NAMA OWNER
OWNER = os.environ.get("OWNER", "real_hackheist")

#OWNER ID
OWNER_ID = int(os.environ.get("OWNER_ID", "5487643307"))

#Port
PORT = os.environ.get("PORT", "8030")

#Database
DB_URI = os.environ.get("DB_URI", "mongodb+srv://namanjain123eudhc:opmaster@cluster0.5iokvxo.mongodb.net/?retryWrites=true&w=majority")
DB_NAME = os.environ.get("DB_NAME", "Cluster0")

#force sub channel id, if you want enable force sub
FORCE_SUB_CHANNEL = int(os.environ.get("FORCE_SUB_CHANNEL", "-1001473043276"))
FORCE_SUB_CHANNEL2 = int(os.environ.get("FORCE_SUB_CHANNEL2", "-1001644866777"))
FORCE_SUB_CHANNEL3 = int(os.environ.get("FORCE_SUB_CHANNEL3", "-1001473043246"))
FORCE_SUB_CHANNEL4 = int(os.environ.get("FORCE_SUB_CHANNEL4", "-1001473043246"))

TG_BOT_WORKERS = int(os.environ.get("TG_BOT_WORKERS", "4"))

FILE_AUTO_DELETE = int(os.getenv("FILE_AUTO_DELETE", "14400")) # auto delete in seconds
INDIVIDUAL_AUTO_DELETE = int(os.getenv("INDIVIDUAL_AUTO_DELETE", "259200"))
#start message
START_MSG = os.environ.get("START_MESSAGE", "<b>ʜᴇʟʟᴏ {first}\n\n<blockquote> ɪ ᴀᴍ ʟᴇᴄᴛᴜʀᴇ ᴘʀᴏᴠɪᴅᴇʀ ʙᴏᴛ, ɪ ᴄᴀɴ ᴘʀᴏᴠɪᴅᴇ ᴀʟʟ ʟᴇᴄᴛᴜʀᴇs 😈 ᴀɴᴅ ᴘᴅғs 😁</blockquote></b>")
FORCE_MSG = os.environ.get("FORCE_SUB_MESSAGE", "ʜᴇʟʟᴏ {first}\n\n<b>💝 𝗜𝗳 𝗬𝗼𝘂 𝗮𝗿𝗲 𝗻𝗲𝘄 𝗼𝗻 𝗼𝘂𝗿 𝗯𝗼𝘁 𝘁𝗵𝗲𝗻 𝘆𝗼𝘂 𝗵𝗮𝘃𝗲 𝘁𝗼 𝗱𝗼 𝘁𝗵𝗶𝘀 𝗼𝗻𝗹𝘆 𝟭𝘀𝘁 𝘁𝗶𝗺𝗲 🥰</b>\n\n<b>1. Join our all channels by below buttons.</b>\n<b>2.Like Join 1st & Join 2nd & Join 3rd.</b>\n<b>3.After Joined all channels click on ♻️Try Again♻️ Button and Enjoy 👻</b>")

CMD_TXT = "<blockquote><b>HACKHEIST</b></blockquote>"
#--------------------------------------------
CUSTOM_CAPTION = os.environ.get("CUSTOM_CAPTION", """<b>{previouscaption}</b>\n<b>━━━━━━━━━━━━━━━━━◇</b>\n<b>⛧ 🄱🅈 :-) </b><b><a href="https://yashyasag.github.io/hiddens">🔥 ℍ𝕀𝔻𝔻𝔼ℕ𝕊 🔥</a></b> <b>♛</b>\n<b>━━━━━━━━━━━━━━━━━◇</b>\n<b>🙏 sʜᴀʀᴇ ᴀɴᴅ sᴜᴘᴘᴏʀᴛ ᴜs 👇</b>\n<b>—————————————————</b>\n<b><a href="https://yashyasag.github.io/hiddens">🚀 𝗠𝗢𝗥𝗘 𝗪𝗘𝗕𝗦𝗜𝗧𝗘𝗦 🌟</a></b>\n<b>—————————————————</b>""")

try:
    ADMINS=[6376328008]
    for x in (os.environ.get("ADMINS", "").split()):
        ADMINS.append(int(x))
except ValueError:
        raise Exception("Your Admins list does not contain valid integers.")

#Force sub message 

#set True if you want to prevent users from forwarding files from bot
PROTECT_CONTENT = True if os.environ.get('PROTECT_CONTENT', "False") == "True" else False

#Set true if you want Disable your Channel Posts Share button
DISABLE_CHANNEL_BUTTON = os.environ.get("DISABLE_CHANNEL_BUTTON", None) == 'True'

BOT_STATS_TEXT = "<b>BOT UPTIME</b>\n{uptime}"
USER_REPLY_TEXT = "ʙᴀᴋᴋᴀ ! ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴍʏ ꜱᴇɴᴘᴀɪ!!"

ADMINS.append(OWNER_ID)
ADMINS.append(6497757690)

LOG_FILE_NAME = "filesharingbot.txt"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s - %(levelname)s] - %(name)s - %(message)s",
    datefmt='%d-%b-%y %H:%M:%S',
    handlers=[
        RotatingFileHandler(
            LOG_FILE_NAME,
            maxBytes=50000000,
            backupCount=10
        ),
        logging.StreamHandler()
    ]
)
logging.getLogger("pyrogram").setLevel(logging.WARNING)


def LOGGER(name: str) -> logging.Logger:
    return logging.getLogger(name)
   
