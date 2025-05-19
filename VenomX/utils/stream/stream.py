# VenomX/utils/stream/stream.py

import os
from random import randint
from typing import Union

from pyrogram.types import InlineKeyboardMarkup

import config
from VenomX import Carbon, YouTube, JioSavan, app, LOGGER
from VenomX.core.call import Ayush
from VenomX.misc import db
from VenomX.utils.database import (
    add_active_video_chat,
    is_active_chat,
    is_video_allowed,
)
from VenomX.utils.exceptions import AssistantErr
from VenomX.utils.inline.play import stream_markup, telegram_markup
from VenomX.utils.inline.playlist import close_markup
from VenomX.utils.pastebin import Ayushbin
from VenomX.utils.thumbnails import get_thumb

async def stream(
    _,
    mystic,
    user_id,
    result,
    chat_id,
    user_name,
    original_chat_id,
    video: Union[bool, str] = None,
    streamtype: Union[bool, str] = None,
    spotify: Union[bool, str] = None,
    forceplay: Union[bool, str] = None,
):
    if not result:
        LOGGER(__name__).error(f"No result provided for stream in chat {chat_id}")
        return
    if video:
        if not await is_video_allowed(chat_id):
            LOGGER(__name__).warning(f"Video not allowed in chat {chat_id}")
            raise AssistantErr(_["play_7"])
    if forceplay:
        await Ayush.force_stop_stream(chat_id)
        LOGGER(__name__).info(f"Force stopped stream in chat {chat_id}")

    if streamtype == "playlist":
        msg = f"{_['playlist_16']}\n\n"
        count = 0
        for search in result:
            if count >= config.PLAYLIST_FETCH_LIMIT:
                continue
            try:
                (
                    title,
                    duration_min,
                    duration_sec,
                    thumbnail,
                    vidid,
                ) = await YouTube.details(search, False if spotify else True)
            except Exception as e:
                LOGGER(__name__).error(f"Error fetching YouTube details for {search}: {str(e)}", exc_info=True)
                continue
            if duration_min == "None":
                continue
            if duration_sec > config.DURATION_LIMIT:
                continue
            if await is_active_chat(chat_id):
                await put_queue(
                    chat_id,
                    original_chat_id,
                    f"vid_{vidid}",
                    title,
                    duration_min,
                    user_name,
                    vidid,
                    user_id,
                    "video" if video else "audio",
                )
                position = len(db.get(chat_id)) - 1
                count += 1
                msg += f"{count}- {title[:70]}\n"
                msg += f"{_['playlist_17']} {position}\n\n"
            else:
                if not forceplay:
                    db[chat_id] = []
                status = True if video else None
                try:
                    file_path, direct = await YouTube.download(
                        vidid, mystic, video=status, videoid=True
                    )
                    LOGGER(__name__).info(f"Downloaded YouTube video {vidid} for chat {chat_id}")
                except Exception as e:
                    LOGGER(__name__).error(f"Error downloading YouTube video {vidid}: {str(e)}", exc_info=True)
                    raise AssistantErr(_["play_16"])
                try:
                    await Ayush.join_call(
                        chat_id, original_chat_id, file_path, video=status
                    )
                    LOGGER(__name__).info(f"Assistant joined call in chat {chat_id} for YouTube playlist")
                except AssistantErr as e:
                    LOGGER(__name__).error(f"AssistantErr in join_call for chat {chat_id}: {str(e)}", exc_info=True)
                    await mystic.edit_text(str(e))
                    return
                except Exception as e:
                    LOGGER(__name__).error(f"Unexpected error in join_call for chat {chat_id}: {str(e)}", exc_info=True)
                    await mystic.edit_text(_["play_16"])
                    return
                await put_queue(
                    chat_id,
                    original_chat_id,
                    file_path if direct else f"vid_{vidid}",
                    title,
                    duration_min,
                    user_name,
                    vidid,
                    user_id,
                    "video" if video else "audio",
                    forceplay=forceplay,
                )
                img = await get_thumb(vidid)
                button = stream_markup(_, vidid, chat_id)
                run = await app.send_photo(
                    original_chat_id,
                    photo=img,
                    caption=_["stream_1"].format(
                        title[:27],
                        f"https://t.me/{app.username}?start=info_{vidid}",
                        duration_min,
                        user_name,
                    ),
                    reply_markup=InlineKeyboardMarkup(button),
                )
                db[chat_id][0]["mystic"] = run
                db[chat_id][0]["markup"] = "stream"
        if count == 0:
            LOGGER(__name__).info(f"No valid tracks in playlist for chat {chat_id}")
            return
        else:
            link = await Ayushbin(msg)
            lines = msg.count("\n")
            if lines >= 17:
                car = os.linesep.join(msg.split(os.linesep)[:17])
            else:
                car = msg
            carbon = await Carbon.generate(car, randint(100, 10000000))
            upl = close_markup(_)
            await app.send_photo(
                original_chat_id,
                photo=carbon,
                caption=_["playlist_18"].format(link, position),
                reply_markup=upl,
            )
            LOGGER(__name__).info(f"Sent playlist summary for chat {chat_id}")
            return

    elif streamtype == "youtube":
        link = result["link"]
        vidid = result["vidid"]
        title = (result["title"]).title()
        duration_min = result["duration_min"]
        thumbnail = result["thumb"]
        status = True if video else None
        try:
            file_path, direct = await YouTube.download(
                vidid, mystic, videoid=True, video=status
            )
            LOGGER(__name__).info(f"Downloaded YouTube video {vidid} for chat {chat_id}")
        except Exception as e:
            LOGGER(__name__).error(f"Error downloading YouTube video {vidid}: {str(e)}", exc_info=True)
            raise AssistantErr(_["play_16"])
        if await is_active_chat(chat_id):
            await put_queue(
                chat_id,
                original_chat_id,
                file_path if direct else f"vid_{vidid}",
                title,
                duration_min,
                user_name,
                vidid,
                user_id,
                "video" if video else "audio",
            )
            position = len(db.get(chat_id)) - 1
            qimg = await get_thumb(vidid)
            run = await app.send_photo(
                original_chat_id,
                photo=qimg,
                caption=_["queue_4"].format(
                    position, title[:27], duration_min, user_name
                ),
                reply_markup=close_markup(_),
            )
            LOGGER(__name__).info(f"Queued YouTube video {vidid} at position {position} in chat {chat_id}")
        else:
            if not forceplay:
                db[chat_id] = []
            try:
                await Ayush.join_call(
                    chat_id, original_chat_id, file_path, video=status
                )
                LOGGER(__name__).info(f"Assistant joined call in chat {chat_id} for YouTube video")
            except AssistantErr as e:
                LOGGER(__name__).error(f"AssistantErr in join_call for chat {chat_id}: {str(e)}", exc_info=True)
                await mystic.edit_text(str(e))
                return
            except Exception as e:
                LOGGER(__name__).error(f"Unexpected error in join_call for chat {chat_id}: {str(e)}", exc_info=True)
                await mystic.edit_text(_["play_16"])
                return
            await put_queue(
                chat_id,
                original_chat_id,
                file_path if direct else f"vid_{vidid}",
                title,
                duration_min,
                user_name,
                vidid,
                user_id,
                "video" if video else "audio",
                forceplay=forceplay,
            )
            img = await get_thumb(vidid)
            button = stream_markup(_, vidid, chat_id)
            run = await app.send_photo(
                original_chat_id,
                photo=img,
                caption=_["stream_1"].format(
                    title[:27],
                    f"https://t.me/{app.username}?start=info_{vidid}",
                    duration_min,
                    user_name,
                ),
                reply_markup=InlineKeyboardMarkup(button),
            )
            db[chat_id][0]["mystic"] = run
            db[chat_id][0]["markup"] = "stream"
            LOGGER(__name__).info(f"Started YouTube stream {vidid} in chat {chat_id}")

    elif "Saavn" in streamtype:
        if streamtype == "saavn_track":
            if result["duration_sec"] == 0:
                LOGGER(__name__).warning(f"Invalid duration for Saavn track in chat {chat_id}")
                return
            file_path = result["filepath"]
            title = result["title"]
            duration_min = result["duration_min"]
            link = result["url"]
            thumb = result["thumb"]
            if await is_active_chat(chat_id):
                await put_queue(
                    chat_id,
                    original_chat_id,
                    file_path,
                    title,
                    duration_min,
                    user_name,
                    streamtype,
                    user_id,
                    "audio",
                    url=link,
                )
                position = len(db.get(chat_id)) - 1
                await app.send_photo(
                    original_chat_id,
                    photo=thumb or "https://envs.sh/Ii_.jpg",
                    caption=_["queue_4"].format(
                        position, title[:30], duration_min, user_name
                    ),
                    reply_markup=close_markup(_),
                )
                LOGGER(__name__).info(f"Queued Saavn track at position {position} in chat {chat_id}")
            else:
                if not forceplay:
                    db[chat_id] = []
                try:
                    await Ayush.join_call(chat_id, original_chat_id, file_path, video=None)
                    LOGGER(__name__).info(f"Assistant joined call in chat {chat_id} for Saavn track")
                except AssistantErr as e:
                    LOGGER(__name__).error(f"AssistantErr in join_call for chat {chat_id}: {str(e)}", exc_info=True)
                    await mystic.edit_text(str(e))
                    return
                except Exception as e:
                    LOGGER(__name__).error(f"Unexpected error in join_call for chat {chat_id}: {str(e)}", exc_info=True)
                    await mystic.edit_text(_["play_16"])
                    return
                await put_queue(
                    chat_id,
                    original_chat_id,
                    file_path,
                    title,
                    duration_min,
                    user_name,
                    streamtype,
                    user_id,
                    "audio",
                    forceplay=forceplay,
                    url=link,
                )
                button = telegram_markup(_, chat_id)
                run = await app.send_photo(
                    original_chat_id,
                    photo=thumb,
                    caption=_["stream_1"].format(
                        title, config.SUPPORT_GROUP, duration_min, user_name
                    ),
                    reply_markup=InlineKeyboardMarkup(button),
                )
                db[chat_id][0]["mystic"] = run
                db[chat_id][0]["markup"] = "tg"
                LOGGER(__name__).info(f"Started Saavn track stream in chat {chat_id}")

        elif streamtype == "saavn_playlist":
            msg = f"{_['playlist_16']}\n\n"
            count = 0
            for search in result:
                if search["duration_sec"] == 0:
                    continue
                title = search["title"]
                duration_min = search["duration_min"]
                duration_sec = search["duration_sec"]
                link = search["url"]
                thumb = search["thumb"]
                file_path, n = await JioSavan.download(link)
                if await is_active_chat(chat_id):
                    await put_queue(
                        chat_id,
                        original_chat_id,
                        file_path,
                        title,
                        duration_min,
                        user_name,
                        streamtype,
                        user_id,
                        "audio",
                        url=link,
                    )
                    position = len(db.get(chat_id)) - 1
                    count += 1
                    msg += f"{count}- {title[:70]}\n"
                    msg += f"{_['playlist_17']} {position}\n\n"
                else:
                    if not forceplay:
                        db[chat_id] = []
                    try:
                        await Ayush.join_call(
                            chat_id, original_chat_id, file_path, video=None
                        )
                        LOGGER(__name__).info(f"Assistant joined call in chat {chat_id} for Saavn playlist")
                    except AssistantErr as e:
                        LOGGER(__name__).error(f"AssistantErr in join_call for chat {chat_id}: {str(e)}", exc_info=True)
                        await mystic.edit_text(str(e))
                        return
                    except Exception as e:
                        LOGGER(__name__).error(f"Unexpected error in join_call for chat {chat_id}: {str(e)}", exc_info=True)
                        await mystic.edit_text(_["play_16"])
                        return
                    await put_queue(
                        chat_id,
                        original_chat_id,
                        file_path,
                        title,
                        duration_min,
                        user_name,
                        streamtype,
                        user_id,
                        "audio",
                        forceplay=forceplay,
                        url=link,
                    )
                    button = telegram_markup(_, chat_id)
                    run = await app.send_photo(
                        original_chat_id,
                        photo=thumb,
                        caption=_["stream_1"].format(
                            title, link, duration_min, user_name
                        ),
                        reply_markup=InlineKeyboardMarkup(button),
                    )
                    db[chat_id][0]["mystic"] = run
                    db[chat_id][0]["markup"] = "tg"
            if count == 0:
                LOGGER(__name__).info(f"No valid tracks in Saavn playlist for chat {chat_id}")
                return
            else:
                link = await Ayushbin(msg)
                lines = msg.count("\n")
                if lines >= 17:
                    car = os.linesep.join(msg.split(os.linesep)[:17])
                else:
                    car = msg
                carbon = await Carbon.generate(car, randint(100, 10000000))
                upl = close_markup(_)
                await app.send_photo(
                    original_chat_id,
                    photo=carbon,
                    caption=_["playlist_18"].format(link, position),
                    reply_markup=upl,
                )
                LOGGER(__name__).info(f"Sent Saavn playlist summary for chat {chat_id}")
                return

    elif streamtype == "soundcloud":
        file_path = result["filepath"]
        title = result["title"]
        duration_min = result["duration_min"]
        if await is_active_chat(chat_id):
            await put_queue(
                chat_id,
                original_chat_id,
                file_path,
                title,
                duration_min,
                user_name,
                streamtype,
                user_id,
                "audio",
            )
            position = len(db.get(chat_id)) - 1
            await app.send_message(
                original_chat_id,
                _["queue_4"].format(position, title[:30], duration_min, user_name),
            )
            LOGGER(__name__).info(f"Queued Soundcloud track at position {position} in chat {chat_id}")
        else:
            if not forceplay:
                db[chat_id] = []
            try:
                await Ayush.join_call(chat_id, original_chat_id, file_path, video=None)
                LOGGER(__name__).info(f"Assistant joined call in chat {chat_id} for Soundcloud track")
            except AssistantErr as e:
                LOGGER(__name__).error(f"AssistantErr in join_call for chat {chat_id}: {str(e)}", exc_info=True)
                await mystic.edit_text(str(e))
                return
            except Exception as e:
                LOGGER(__name__).error(f"Unexpected error in join_call for chat {chat_id}: {str(e)}", exc_info=True)
                await mystic.edit_text(_["play_16"])
                return
            await put_queue(
                chat_id,
                original_chat_id,
                file_path,
                title,
                duration_min,
                user_name,
                streamtype,
                user_id,
                "audio",
                forceplay=forceplay,
            )
            button = telegram_markup(_, chat_id)
            run = await app.send_photo(
                original_chat_id,
                photo=config.SOUNCLOUD_IMG_URL,
                caption=_["stream_1"].format(
                    title, config.SUPPORT_GROUP, duration_min, user_name
                ),
                reply_markup=InlineKeyboardMarkup(button),
            )
            db[chat_id][0]["mystic"] = run
            db[chat_id][0]["markup"] = "tg"
            LOGGER(__name__).info(f"Started Soundcloud stream in chat {chat_id}")

    elif streamtype == "telegram":
        file_path = result["path"]
        link = result["link"]
        title = (result["title"]).title()
        duration_min = result["dur"]
        status = True if video else None
        if await is_active_chat(chat_id):
            await put_queue(
                chat_id,
                original_chat_id,
                file_path,
                title,
                duration_min,
                user_name,
                streamtype,
                user_id,
                "video" if video else "audio",
            )
            position = len(db.get(chat_id)) - 1
            await app.send_message(
                original_chat_id,
                _["queue_4"].format(position, title[:30], duration_min, user_name),
            )
            LOGGER(__name__).info(f"Queued Telegram media at position {position} in chat {chat_id}")
        else:
            if not forceplay:
                db[chat_id] = []
            try:
                await Ayush.join_call(chat_id, original_chat_id, file_path, video=status)
                LOGGER(__name__).info(f"Assistant joined call in chat {chat_id} for Telegram media")
            except AssistantErr as e:
                LOGGER(__name__).error(f"AssistantErr in join_call for chat {chat_id}: {str(e)}", exc_info=True)
                await mystic.edit_text(str(e))
                return
            except Exception as e:
                LOGGER(__name__).error(f"Unexpected error in join_call for chat {chat_id}: {str(e)}", exc_info=True)
                await mystic.edit_text(_["play_16"])
                return
            await put_queue(
                chat_id,
                original_chat_id,
                file_path,
                title,
                duration_min,
                user_name,
                streamtype,
                user_id,
                "video" if video else "audio",
                forceplay=forceplay,
            )
            if video:
                await add_active_video_chat(chat_id)
            button = telegram_markup(_, chat_id)
            run = await app.send_photo(
                original_chat_id,
                photo=config.TELEGRAM_VIDEO_URL if video else config.TELEGRAM_AUDIO_URL,
                caption=_["stream_1"].format(title, link, duration_min, user_name),
                reply_markup=InlineKeyboardMarkup(button),
            )
            db[chat_id][0]["mystic"] = run
            db[chat_id][0]["markup"] = "tg"
            LOGGER(__name__).info(f"Started Telegram stream in chat {chat_id}")

    elif streamtype == "live":
        link = result["link"]
        vidid = result["vidid"]
        title = (result["title"]).title()
        thumbnail = result["thumb"]
        duration_min = "00:00"
        status = True if video else None
        if await is_active_chat(chat_id):
            await put_queue(
                chat_id,
                original_chat_id,
                f"live_{vidid}",
                title,
                duration_min,
                user_name,
                vidid,
                user_id,
                "video" if video else "audio",
            )
            position = len(db.get(chat_id)) - 1
            await app.send_message(
                original_chat_id,
                _["queue_4"].format(position, title[:30], duration_min, user_name),
            )
            LOGGER(__name__).info(f"Queued live stream at position {position} in chat {chat_id}")
        else:
            if not forceplay:
                db[chat_id] = []
            n, file_path = await YouTube.video(link)
            if n == 0:
                LOGGER(__name__).error(f"Failed to get live stream URL for {vidid}")
                raise AssistantErr(_["str_3"])
            try:
                await Ayush.join_call(
                    chat_id, original_chat_id, file_path, video=status
                )
                LOGGER(__name__).info(f"Assistant joined call in chat {chat_id} for live stream")
            except AssistantErr as e:
                LOGGER(__name__).error(f"AssistantErr in join_call for chat {chat_id}: {str(e)}", exc_info=True)
                await mystic.edit_text(str(e))
                return
            except Exception as e:
                LOGGER(__name__).error(f"Unexpected error in join_call for chat {chat_id}: {str(e)}", exc_info=True)
                await mystic.edit_text(_["play_16"])
                return
            await put_queue(
                chat_id,
                original_chat_id,
                f"live_{vidid}",
                title,
                duration_min,
                user_name,
                vidid,
                user_id,
                "video" if video else "audio",
                forceplay=forceplay,
            )
            img = await get_thumb(vidid)
            button = telegram_markup(_, chat_id)
            run = await app.send_photo(
                original_chat_id,
                photo=img,
                caption=_["stream_1"].format(
                    title[:27],
                    f"https://t.me/{app.username}?start=info_{vidid}",
                    duration_min,
                    user_name,
                ),
                reply_markup=InlineKeyboardMarkup(button),
            )
            db[chat_id][0]["mystic"] = run
            db[chat_id][0]["markup"] = "tg"
            LOGGER(__name__).info(f"Started live stream {vidid} in chat {chat_id}")

    elif streamtype == "index":
        link = result
        title = "Index or M3u8 Link"
        duration_min = "URL stream"
        if await is_active_chat(chat_id):
            await put_queue_index(
                chat_id,
                original_chat_id,
                "index_url",
                title,
                duration_min,
                user_name,
                link,
                "video" if video else "audio",
            )
            position = len(db.get(chat_id)) - 1
            await mystic.edit_text(
                _["queue_4"].format(position, title[:30], duration_min, user_name)
            )
            LOGGER(__name__).info(f"Queued index stream at position {position} in chat {chat_id}")
        else:
            if not forceplay:
                db[chat_id] = []
            try:
                await Ayush.join_call(
                    chat_id, original_chat_id, link, video=True if video else None
                )
                LOGGER(__name__).info(f"Assistant joined call in chat {chat_id} for index stream")
            except AssistantErr as e:
                LOGGER(__name__).error(f"AssistantErr in join_call for chat {chat_id}: {str(e)}", exc_info=True)
                await mystic.edit_text(str(e))
                return
            except Exception as e:
                LOGGER(__name__).error(f"Unexpected error in join_call for chat {chat_id}: {str(e)}", exc_info=True)
                await mystic.edit_text(_["play_16"])
                return
            await put_queue_index(
                chat_id,
                original_chat_id,
                "index_url",
                title,
                duration_min,
                user_name,
                link,
                "video" if video else "audio",
                forceplay=forceplay,
            )
            button = telegram_markup(_, chat_id)
            run = await app.send_photo(
                original_chat_id,
                photo=config.STREAM_IMG_URL,
                caption=_["stream_2"].format(user_name),
                reply_markup=InlineKeyboardMarkup(button),
            )
            db[chat_id][0]["mystic"] = run
            db[chat_id][0]["markup"] = "tg"
            await mystic.delete()
            LOGGER(__name__).info(f"Started index stream in chat {chat_id}")
