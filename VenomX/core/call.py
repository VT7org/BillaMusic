# VenomX/core/call.py

import asyncio
from typing import Union

from ntgcalls import TelegramServerError
from pyrogram.types import InlineKeyboardMarkup
from pytgcalls import PyTgCalls, filters
from pytgcalls.exceptions import AlreadyJoinedError, GroupCallNotFound
from pytgcalls.types import (
    ChatUpdate,
    GroupCallConfig,
    MediaStream,
    Update,
)
from pytgcalls.types import StreamAudioEnded

import config
from strings import get_string
from VenomX import LOGGER, YouTube, JioSavan, Soundcloud, Telegram, Resso, Spotify, Apple, app, userbot
from VenomX.misc import db
from VenomX.utils.database import (
    add_active_chat,
    add_active_video_chat,
    get_audio_bitrate,
    get_lang,
    get_loop,
    get_video_bitrate,
    group_assistant,
    music_on,
    remove_active_chat,
    remove_active_video_chat,
    set_loop,
)
from VenomX.utils.exceptions import AssistantErr
from VenomX.utils.inline.play import stream_markup, telegram_markup
from VenomX.utils.stream.autoclear import auto_clean
from VenomX.utils.thumbnails import get_thumb
from pyrogram.errors import (
    ChannelsTooMuch,
    ChatAdminRequired,
    FloodWait,
    InviteRequestSent,
    UserAlreadyParticipant,
)

from VenomX.core.userbot import assistants
from VenomX.utils.database import (
    get_assistant,
    get_lang,
    set_assistant,
)

links = {}

async def _clear_(chat_id):
    popped = db.pop(chat_id, None)
    if popped:
        await auto_clean(popped)
    db[chat_id] = []
    await remove_active_video_chat(chat_id)
    await remove_active_chat(chat_id)
    await set_loop(chat_id, 0)

class Call:
    def __init__(self):
        self.calls = []
        for client in userbot.clients:
            pycall = PyTgCalls(
                client,
                cache_duration=100,
            )
            self.calls.append(pycall)
        LOGGER(__name__).info(f"Initialized {len(self.calls)} PyTgCalls instances")

    async def pause_stream(self, chat_id: int):
        assistant = await group_assistant(self, chat_id)
        await assistant.pause_stream(chat_id)
        LOGGER(__name__).info(f"Paused stream in chat {chat_id}")

    async def resume_stream(self, chat_id: int):
        assistant = await group_assistant(self, chat_id)
        await assistant.resume_stream(chat_id)
        LOGGER(__name__).info(f"Resumed stream in chat {chat_id}")

    async def mute_stream(self, chat_id: int):
        assistant = await group_assistant(self, chat_id)
        await assistant.mute_stream(chat_id)
        LOGGER(__name__).info(f"Muted stream in chat {chat_id}")

    async def unmute_stream(self, chat_id: int):
        assistant = await group_assistant(self, chat_id)
        await assistant.unmute_stream(chat_id)
        LOGGER(__name__).info(f"Unmuted stream in chat {chat_id}")

    async def stop_stream(self, chat_id: int):
        assistant = await group_assistant(self, chat_id)
        try:
            await _clear_(chat_id)
            await assistant.leave_call(chat_id)
            LOGGER(__name__).info(f"Stopped stream in chat {chat_id}")
        except Exception as e:
            LOGGER(__name__).error(f"Error stopping stream in chat {chat_id}: {str(e)}", exc_info=True)

    async def force_stop_stream(self, chat_id: int):
        assistant = await group_assistant(self, chat_id)
        try:
            check = db.get(chat_id)
            if check:
                check.pop(0)
        except Exception:
            pass
        await remove_active_video_chat(chat_id)
        await remove_active_chat(chat_id)
        try:
            await assistant.leave_call(chat_id)
            LOGGER(__name__).info(f"Force stopped stream in chat {chat_id}")
        except Exception as e:
            LOGGER(__name__).error(f"Error force stopping stream in chat {chat_id}: {str(e)}", exc_info=True)

    async def skip_stream(
        self,
        chat_id: int,
        link: str,
        video: Union[bool, str] = None,
        image: Union[bool, str] = None,
    ):
        assistant = await group_assistant(self, chat_id)
        audio_stream_quality = await get_audio_bitrate(chat_id)
        video_stream_quality = await get_video_bitrate(chat_id)
        call_config = GroupCallConfig(auto_start=False)
        stream = (
            MediaStream(
                link,
                audio_parameters=audio_stream_quality,
                video_parameters=video_stream_quality,
            )
            if video
            else MediaStream(
                link,
                audio_parameters=audio_stream_quality,
                video_flags=MediaStream.Flags.IGNORE,
            )
        )
        await assistant.play(chat_id, stream, config=call_config)
        LOGGER(__name__).info(f"Skipped to new stream in chat {chat_id}")

    async def seek_stream(self, chat_id, file_path, to_seek, duration, mode):
        assistant = await group_assistant(self, chat_id)
        audio_stream_quality = await get_audio_bitrate(chat_id)
        video_stream_quality = await get_video_bitrate(chat_id)
        call_config = GroupCallConfig(auto_start=False)
        stream = (
            MediaStream(
                file_path,
                audio_parameters=audio_stream_quality,
                video_parameters=video_stream_quality,
                ffmpeg_parameters=f"-ss {to_seek} -to {duration}",
            )
            if mode == "video"
            else MediaStream(
                file_path,
                audio_parameters=audio_stream_quality,
                ffmpeg_parameters=f"-ss {to_seek} -to {duration}",
                video_flags=MediaStream.Flags.IGNORE,
            )
        )
        await assistant.play(chat_id, stream, config=call_config)
        LOGGER(__name__).info(f"Seeking stream in chat {chat_id}")

    async def stream_call(self, link):
        assistant = await group_assistant(self, config.LOGGER_ID)
        call_config = GroupCallConfig(auto_start=False)
        await assistant.play(
            config.LOGGER_ID,
            MediaStream(link),
            config=call_config,
        )
        await asyncio.sleep(0.5)
        await assistant.leave_call(config.LOGGER_ID)
        LOGGER(__name__).info(f"Test stream call executed in logger chat")

    async def join_chat(self, chat_id, attempts=1):
        max_attempts = len(assistants) - 1
        userbot = await get_assistant(chat_id)
        try:
            language = await get_lang(chat_id)
            _ = get_string(language)
        except Exception:
            _ = get_string("en")
        try:
            chat = await app.get_chat(chat_id)
            LOGGER(__name__).info(f"Retrieved chat info for {chat_id}")
        except ChatAdminRequired:
            LOGGER(__name__).error(f"ChatAdminRequired for chat {chat_id}")
            raise AssistantErr(_["call_1"])
        except Exception as e:
            LOGGER(__name__).error(f"Error getting chat {chat_id}: {str(e)}", exc_info=True)
            raise AssistantErr(_["call_3"].format(app.mention, type(e).__name__))

        if chat_id in links:
            invitelink = links[chat_id]
        else:
            if chat.username:
                invitelink = chat.username
                try:
                    await userbot.resolve_peer(invitelink)
                except Exception as e:
                    LOGGER(__name__).warning(f"Error resolving peer {invitelink}: {str(e)}")
            else:
                try:
                    invitelink = await app.export_chat_invite_link(chat_id)
                    LOGGER(__name__).info(f"Exported invite link for chat {chat_id}")
                except ChatAdminRequired:
                    LOGGER(__name__).error(f"ChatAdminRequired for invite link in chat {chat_id}")
                    raise AssistantErr(_["call_1"])
                except Exception as e:
                    LOGGER(__name__).error(f"Error exporting invite link for chat {chat_id}: {str(e)}", exc_info=True)
                    raise AssistantErr(_["call_3"].format(app.mention, type(e).__name__))

            if invitelink.startswith("https://t.me/+"):
                invitelink = invitelink.replace("https://t.me/+", "https://t.me/joinchat/")
            links[chat_id] = invitelink

        try:
            await asyncio.sleep(1)
            await userbot.join_chat(invitelink)
            LOGGER(__name__).info(f"Assistant joined chat {chat_id} via invite link")
        except InviteRequestSent:
            try:
                await app.approve_chat_join_request(chat_id, userbot.id)
                LOGGER(__name__).info(f"Approved join request for assistant in chat {chat_id}")
            except Exception as e:
                LOGGER(__name__).error(f"Error approving join request in chat {chat_id}: {str(e)}", exc_info=True)
                raise AssistantErr(_["call_3"].format(type(e).__name__))
            await asyncio.sleep(1)
            raise AssistantErr(_["call_6"].format(app.mention))
        except UserAlreadyParticipant:
            LOGGER(__name__).info(f"Assistant already a participant in chat {chat_id}")
        except ChannelsTooMuch:
            if attempts <= max_attempts:
                attempts += 1
                userbot = await set_assistant(chat_id)
                LOGGER(__name__).info(f"Retrying join_chat for chat {chat_id} with attempt {attempts}")
                return await self.join_chat(chat_id, attempts)
            else:
                LOGGER(__name__).error(f"Max attempts reached for chat {chat_id}")
                raise AssistantErr(_["call_9"].format(config.SUPPORT_GROUP))
        except FloodWait as e:
            time = e.value
            if time < 20:
                await asyncio.sleep(time)
                attempts += 1
                LOGGER(__name__).info(f"FloodWait {time}s, retrying join_chat for chat {chat_id}")
                return await self.join_chat(chat_id, attempts)
            else:
                if attempts <= max_attempts:
                    attempts += 1
                    userbot = await set_assistant(chat_id)
                    LOGGER(__name__).info(f"FloodWait {time}s, switching assistant for chat {chat_id}")
                    return await self.join_chat(chat_id, attempts)
                LOGGER(__name__).error(f"FloodWait {time}s too long for chat {chat_id}")
                raise AssistantErr(_["call_10"].format(time))
        except Exception as e:
            LOGGER(__name__).error(f"Error joining chat {chat_id}: {str(e)}", exc_info=True)
            raise AssistantErr(_["call_3"].format(type(e).__name__))

    async def join_call(
        self,
        chat_id: int,
        original_chat_id: int,
        link: str,
        video: Union[bool, str] = None,
        image: Union[bool, str] = None,
    ):
        assistant = await group_assistant(self, chat_id)
        audio_stream_quality = await get_audio_bitrate(chat_id)
        video_stream_quality = await get_video_bitrate(chat_id)
        call_config = GroupCallConfig(auto_start=False)
        stream = (
            MediaStream(
                link,
                audio_parameters=audio_stream_quality,
                video_parameters=video_stream_quality,
            )
            if video
            else MediaStream(
                link,
                audio_parameters=audio_stream_quality,
                video_flags=MediaStream.Flags.IGNORE,
            )
        )

        try:
            await self.join_chat(chat_id)  # Ensure assistant is in the chat
            await assistant.join_group_call(chat_id)  # Explicitly join the group call
            await assistant.play(chat_id, stream, config=call_config)
            LOGGER(__name__).info(f"Assistant joined and started playing in chat {chat_id}")
        except AlreadyJoinedError:
            LOGGER(__name__).warning(f"Assistant already in voice chat for chat {chat_id}")
            try:
                await assistant.play(chat_id, stream, config=call_config)
                LOGGER(__name__).info(f"Assistant played stream in chat {chat_id} despite already joined")
            except Exception as e:
                LOGGER(__name__).error(f"Error playing stream in chat {chat_id}: {str(e)}", exc_info=True)
                raise AssistantErr(_["call_7"])
        except GroupCallNotFound:
            LOGGER(__name__).error(f"No active voice chat found in chat {chat_id}")
            raise AssistantErr(
                "**No Active Voice Chat Found**\n\nPlease ensure the group's voice chat is enabled. If already enabled, please end it and start a fresh voice chat. If the problem persists, try /restart."
            )
        except TelegramServerError:
            LOGGER(__name__).error(f"Telegram server error in chat {chat_id}")
            raise AssistantErr(
                "**Telegram Server Error**\n\nPlease restart the voice chat and try again."
            )
        except Exception as e:
            LOGGER(__name__).error(f"Unexpected error in join_call for chat {chat_id}: {str(e)}", exc_info=True)
            try:
                await self.join_chat(chat_id)  # Retry joining the chat
                await assistant.join_group_call(chat_id)
                await assistant.play(chat_id, stream, config=call_config)
                LOGGER(__name__).info(f"Retry successful: Assistant joined and played in chat {chat_id}")
            except Exception as retry_e:
                LOGGER(__name__).error(f"Retry failed for chat {chat_id}: {str(retry_e)}", exc_info=True)
                raise AssistantErr(
                    f"Failed to join voice chat: {str(retry_e)}. Please ensure the voice chat is active and try /restart."
                )

        await add_active_chat(chat_id)
        await music_on(chat_id)
        if video:
            await add_active_video_chat(chat_id)
        LOGGER(__name__).info(f"Active chat and music status updated for chat {chat_id}")

    async def change_stream(self, client, chat_id):
        check = db.get(chat_id)
        popped = None
        loop = await get_loop(chat_id)
        try:
            if loop == 0:
                popped = check.pop(0)
            else:
                loop = loop - 1
                await set_loop(chat_id, loop)
            if popped:
                await auto_clean(popped)
                if popped.get("mystic"):
                    try:
                        await popped.get("mystic").delete()
                    except Exception:
                        pass
            if not check:
                await _clear_(chat_id)
                await client.leave_call(chat_id)
                LOGGER(__name__).info(f"Queue empty, left call in chat {chat_id}")
                return
        except Exception as e:
            LOGGER(__name__).error(f"Error clearing queue in chat {chat_id}: {str(e)}", exc_info=True)
            try:
                await _clear_(chat_id)
                await client.leave_call(chat_id)
            except Exception:
                return
        else:
            queued = check[0]["file"]
            language = await get_lang(chat_id)
            _ = get_string(language)
            title = (check[0]["title"]).title()
            user = check[0]["by"]
            original_chat_id = check[0]["chat_id"]
            streamtype = check[0]["streamtype"]
            audio_stream_quality = await get_audio_bitrate(chat_id)
            video_stream_quality = await get_video_bitrate(chat_id)
            videoid = check[0]["vidid"]
            check[0]["played"] = 0
            video = str(streamtype) == "video"
            call_config = GroupCallConfig(auto_start=False)
            if "live_" in queued:
                n, link = await YouTube.video(videoid, True)
                if n == 0:
                    await app.send_message(original_chat_id, text=_["call_7"])
                    return
                stream = (
                    MediaStream(
                        link,
                        audio_parameters=audio_stream_quality,
                        video_parameters=video_stream_quality,
                    )
                    if video
                    else MediaStream(
                        link,
                        audio_parameters=audio_stream_quality,
                        video_flags=MediaStream.Flags.IGNORE,
                    )
                )
                try:
                    await client.play(chat_id, stream, config=call_config)
                    LOGGER(__name__).info(f"Played live stream in chat {chat_id}")
                except Exception as e:
                    LOGGER(__name__).error(f"Error playing live stream in chat {chat_id}: {str(e)}", exc_info=True)
                    await app.send_message(original_chat_id, text=_["call_7"])
                    return
                img = await get_thumb(videoid)
                button = telegram_markup(_, chat_id)
                run = await app.send_photo(
                    original_chat_id,
                    photo=img,
                    caption=_["stream_1"].format(
                        title[:27],
                        f"https://t.me/{app.username}?start=info_{videoid}",
                        check[0]["dur"],
                        user,
                    ),
                    reply_markup=InlineKeyboardMarkup(button),
                )
                db[chat_id][0]["mystic"] = run
                db[chat_id][0]["markup"] = "tg"
            elif "vid_" in queued:
                mystic = await app.send_message(original_chat_id, _["call_8"])
                try:
                    file_path, direct = await YouTube.download(
                        videoid,
                        mystic,
                        videoid=True,
                        video=video,
                    )
                except Exception as e:
                    LOGGER(__name__).error(f"Error downloading YouTube video in chat {chat_id}: {str(e)}", exc_info=True)
                    await mystic.edit_text(_["call_7"], disable_web_page_preview=True)
                    return
                stream = (
                    MediaStream(
                        file_path,
                        audio_parameters=audio_stream_quality,
                        video_parameters=video_stream_quality,
                    )
                    if video
                    else MediaStream(
                        file_path,
                        audio_parameters=audio_stream_quality,
                        video_flags=MediaStream.Flags.IGNORE,
                    )
                )
                try:
                    await client.play(chat_id, stream, config=call_config)
                    LOGGER(__name__).info(f"Played downloaded video in chat {chat_id}")
                except Exception as e:
                    LOGGER(__name__).error(f"Error playing downloaded video in chat {chat_id}: {str(e)}", exc_info=True)
                    await app.send_message(original_chat_id, text=_["call_7"])
                    return
                img = await get_thumb(videoid)
                button = stream_markup(_, videoid, chat_id)
                await mystic.delete()
                run = await app.send_photo(
                    original_chat_id,
                    photo=img,
                    caption=_["stream_1"].format(
                        title[:27],
                        f"https://t.me/{app.username}?start=info_{videoid}",
                        check[0]["dur"],
                        user,
                    ),
                    reply_markup=InlineKeyboardMarkup(button),
                )
                db[chat_id][0]["mystic"] = run
                db[chat_id][0]["markup"] = "stream"
            elif "index_" in queued:
                stream = (
                    MediaStream(
                        videoid,
                        audio_parameters=audio_stream_quality,
                        video_parameters=video_stream_quality,
                    )
                    if video
                    else MediaStream(
                        videoid,
                        audio_parameters=audio_stream_quality,
                        video_flags=MediaStream.Flags.IGNORE,
                    )
                )
                try:
                    await client.play(chat_id, stream, config=call_config)
                    LOGGER(__name__).info(f"Played index stream in chat {chat_id}")
                except Exception as e:
                    LOGGER(__name__).error(f"Error playing index stream in chat {chat_id}: {str(e)}", exc_info=True)
                    await app.send_message(original_chat_id, text=_["call_7"])
                    return
                button = telegram_markup(_, chat_id)
                run = await app.send_photo(
                    original_chat_id,
                    photo=config.STREAM_IMG_URL,
                    caption=_["stream_2"].format(user),
                    reply_markup=InlineKeyboardMarkup(button),
                )
                db[chat_id][0]["mystic"] = run
                db[chat_id][0]["markup"] = "tg"
            else:
                url = check[0].get("url")
                if videoid == "telegram":
                    image = None
                elif videoid == "Soundcloud":
                    image = None
                elif "Saavn" in videoid:
                    url = check[0].get("url")
                    details = await JioSavan.info(url)
                    image = details["thumb"]
                else:
                    try:
                        image = await YouTube.thumbnail(videoid, True)
                    except Exception:
                        image = None
                stream = (
                    MediaStream(
                        queued,
                        audio_parameters=audio_stream_quality,
                        video_parameters=video_stream_quality,
                    )
                    if video
                    else MediaStream(
                        queued,
                        audio_parameters=audio_stream_quality,
                        video_flags=MediaStream.Flags.IGNORE,
                    )
                )
                try:
                    await client.play(chat_id, stream, config=call_config)
                    LOGGER(__name__).info(f"Played stream in chat {chat_id}")
                except Exception as e:
                    LOGGER(__name__).error(f"Error playing stream in chat {chat_id}: {str(e)}", exc_info=True)
                    await app.send_message(original_chat_id, text=_["call_7"])
                    return
                if videoid == "telegram":
                    button = telegram_markup(_, chat_id)
                    run = await app.send_photo(
                        original_chat_id,
                        photo=(
                            config.TELEGRAM_AUDIO_URL
                            if str(streamtype) == "audio"
                            else config.TELEGRAM_VIDEO_URL
                        ),
                        caption=_["stream_1"].format(
                            title, config.SUPPORT_GROUP, check[0]["dur"], user
                        ),
                        reply_markup=InlineKeyboardMarkup(button),
                    )
                    db[chat_id][0]["mystic"] = run
                    db[chat_id][0]["markup"] = "tg"
                elif videoid == "soundcloud":
                    button = telegram_markup(_, chat_id)
                    run = await app.send_photo(
                        original_chat_id,
                        photo=config.SOUNCLOUD_IMG_URL,
                        caption=_["stream_1"].format(
                            title, config.SUPPORT_GROUP, check[0]["dur"], user
                        ),
                        reply_markup=InlineKeyboardMarkup(button),
                    )
                    db[chat_id][0]["mystic"] = run
                    db[chat_id][0]["markup"] = "tg"
                elif "saavn" in videoid:
                    button = telegram_markup(_, chat_id)
                    run = await app.send_photo(
                        original_chat_id,
                        photo=image,
                        caption=_["stream_1"].format(title, url, check[0]["dur"], user),
                        reply_markup=InlineKeyboardMarkup(button),
                    )
                    db[chat_id][0]["mystic"] = run
                    db[chat_id][0]["markup"] = "tg"
                else:
                    img = await get_thumb(videoid)
                    button = stream_markup(_, videoid, chat_id)
                    run = await app.send_photo(
                        original_chat_id,
                        photo=img,
                        caption=_["stream_1"].format(
                            title[:27],
                            f"https://t.me/{app.username}?start=info_{videoid}",
                            check[0]["dur"],
                            user,
                        ),
                        reply_markup=InlineKeyboardMarkup(button),
                    )
                    db[chat_id][0]["mystic"] = run
                    db[chat_id][0]["markup"] = "stream"

    async def ping(self):
        pings = []
        for call in self.calls:
            pings.append(call.ping)
        if pings:
            return str(round(sum(pings) / len(pings), 3))
        else:
            LOGGER(__name__).error("No active clients for ping calculation.")
            return "No active clients"

    async def start(self):
        """Starts all PyTgCalls instances for the existing userbot clients."""
        LOGGER(__name__).info("Starting PyTgCalls Clients")
        await asyncio.gather(*[c.start() for c in self.calls])

    async def decorators(self):
        for call in self.calls:
            @call.on_update(filters.chat_update(ChatUpdate.Status.LEFT_CALL))
            async def stream_services_handler(client, update):
                LOGGER(__name__).info(f"Assistant left call in chat {update.chat_id}")
                await self.stop_stream(update.chat_id)

            @call.on_update(filters.stream_end)
            async def stream_end_handler(client, update: Update):
                if not isinstance(update, StreamAudioEnded):
                    return
                LOGGER(__name__).info(f"Stream ended in chat {update.chat_id}")
                await self.change_stream(client, update.chat_id)

    def __getattr__(self, name):
        if not self.calls:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
        first_call = self.calls[0]
        if hasattr(first_call, name):
            return getattr(first_call, name)
        raise AttributeError(f"'{type(first_call).__name__}' object has no attribute '{name}'")

Ayush = Call()
