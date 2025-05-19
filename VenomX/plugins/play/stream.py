# VenomX/plugins/play/stream.py


import logging
from pyrogram import filters
from pyrogram.types import Message
from pytgcalls.exceptions import NoActiveGroupCall

import config
from config import BANNED_USERS
from strings import command
from VenomX import app
from VenomX.core.call import Ayush
from VenomX.utils.decorators.play import PlayWrapper
from VenomX.utils.logger import play_logs
from VenomX.utils.stream.stream import stream

# Set up logging
logger = logging.getLogger(__name__)

@app.on_message(command("STREAM_COMMAND") & filters.group & ~BANNED_USERS)
@PlayWrapper
async def stream_command(
    client,
    message: Message,
    _,
    chat_id,
    video,
    channel,
    playmode,
    url,
    fplay,
):
    if url:
        try:
            mystic = await message.reply_text(
                _["play_2"].format(channel) if channel else _["play_1"]
            )
        except Exception as e:
            logger.error(f"Failed to send initial reply: {str(e)}", exc_info=True)
            return
        try:
            await Ayush.stream_call(url)
        except NoActiveGroupCall:
            logger.error("No active group call for streaming.")
            await mystic.edit_text(
                "There's an issue with the bot. please report it to my Owner and ask them to check logger group"
            )
            text = "Please Turn on voice chat.. Bot is unable to stream urls.."
            await app.send_message(config.LOGGER_ID, text)
            return
        except Exception as e:
            logger.error(f"Stream call error: {str(e)}", exc_info=True)
            await mystic.edit_text(_["general_3"].format(type(e).__name__))
            return
        await mystic.edit_text(_["str_2"])
        try:
            await stream(
                _,
                mystic,
                message.from_user.id,
                url,
                chat_id,
                message.from_user.first_name,
                message.chat.id,
                video=True,
                streamtype="index",
            )
        except Exception as e:
            ex_type = type(e).__name__
            err = e if ex_type == "AssistantErr" else _["general_3"].format(ex_type)
            logger.error(f"Stream error: {str(e)}", exc_info=True)
            await mystic.edit_text(err)
            return
        await play_logs(message, streamtype="M3u8 or Index Link")
        return
    else:
        await message.reply_text(_["str_1"])
